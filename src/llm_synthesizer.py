"""
src/llm_synthesizer.py
Required Ollama synthesis layer for the parent-facing report.
"""

import json
import os
import urllib.error
import urllib.request


EXPECTED_KEYS = ("parent_narrative", "weekly_progress", "actionable_tips")


def synthesize_report_sections(report_context):
    """
    Return LLM-generated report sections plus metadata.

    The returned dict always contains:
      - used_llm: bool
      - provider: str
      - model: str
      - error: str

    When successful, it also contains:
      - parent_narrative: list[str]
      - weekly_progress: str
      - actionable_tips: list[str]
    """
    _load_env_file()
    provider = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    if provider != "ollama":
        raise RuntimeError("This pipeline only supports LLM_PROVIDER=ollama.")

    prompt = _build_prompt(report_context)
    model = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
    sections = _call_ollama(prompt, model)
    if not sections.get("used_llm"):
        error = sections.get("error") or "Ollama did not return valid report sections."
        raise RuntimeError(f"Ollama synthesis failed: {error}")
    return sections


def _build_prompt(context):
    compact_context = _compact_context(context)
    return (
        "You are an education report writer for parents. "
        "Use the supplied class-session metrics to produce friendly, specific, non-robotic feedback. "
        "Return one JSON object only. Do not add markdown or explanation. "
        "Required keys: parent_narrative, weekly_progress, actionable_tips. "
        "parent_narrative: exactly 2 short strings. "
        "weekly_progress: one short string. "
        "actionable_tips: exactly 3 short strings.\n\n"
        f"SESSION_CONTEXT_JSON:\n{json.dumps(compact_context, separators=(',', ':'), ensure_ascii=False)}"
    )


def _compact_context(context):
    """Keep the LLM prompt small and avoid sending unnecessary raw fields."""
    vision = context.get("vision", {})
    audio = context.get("audio", {})
    activity = context.get("activity", {})
    attendance = context.get("attendance", {})
    homework = context.get("homework", {})

    return {
        "student_name": context.get("student_name", "Student"),
        "session_id": context.get("session_id", "session_01"),
        "metrics": context.get("metrics", {}),
        "strength_areas": context.get("strength_areas", []),
        "improvement_areas": context.get("improvement_areas", []),
        "summaries": {
            "focus": vision.get("focus_summary", ""),
            "speech": audio.get("speech_summary", ""),
            "attendance": attendance.get("weekly_consistency_summary", ""),
            "homework_status": homework.get("completion_status", ""),
            "homework_quality": homework.get("completion_quality", ""),
        },
        "details": {
            "face_detected_ratio": vision.get("face_detected_ratio", 0),
            "pause_count": audio.get("pause_count", 0),
            "words_per_minute": audio.get("words_per_minute", 0),
            "canvas_completion": activity.get("canvas_completion_percentage", 0),
            "attendance_streak": attendance.get("current_streak", 0),
            "missed_classes": attendance.get("missed_classes", 0),
            "homework_topics": homework.get("extracted_topics", []),
        },
    }


def _load_env_file():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass


def _call_ollama(prompt, model):
    max_tokens = _max_output_tokens()
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    last_error = ""
    prompts = [
        prompt,
        (
            "Fix the previous output format. Return only this JSON shape with no extra text: "
            '{"parent_narrative":["paragraph one","paragraph two"],'
            '"weekly_progress":"one sentence","actionable_tips":["tip one","tip two","tip three"]}\n\n'
            f"{prompt}"
        ),
    ]
    for current_prompt in prompts:
        payload = {
            "model": model,
            "prompt": current_prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": max_tokens},
        }
        try:
            data = _post_json(url, payload, timeout=90)
            raw_text = data.get("response", "")
            parsed = _parse_llm_json(raw_text)
            parsed.update(_metadata(True, "ollama", model, ""))
            return parsed
        except Exception as exc:
            last_error = str(exc)
    return _metadata(False, "ollama", model, last_error)


def _post_json(url, payload, headers=None, timeout=60):
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {details}") from exc


def _parse_llm_json(raw_text):
    parsed = json.loads(_extract_json_object(raw_text))
    parsed = _normalize_llm_output(parsed)
    _validate_llm_output(parsed)
    return {
        "parent_narrative": [str(item).strip() for item in parsed["parent_narrative"][:2]],
        "weekly_progress": str(parsed["weekly_progress"]).strip(),
        "actionable_tips": [str(item).strip() for item in parsed["actionable_tips"][:3]],
    }


def _extract_json_object(raw_text):
    text = str(raw_text).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _validate_llm_output(parsed):
    if not isinstance(parsed, dict):
        raise ValueError("LLM response was not a JSON object.")
    for key in EXPECTED_KEYS:
        if key not in parsed:
            raise ValueError(f"LLM response missing key: {key}")
    if not isinstance(parsed["parent_narrative"], list) or len(parsed["parent_narrative"]) < 2:
        raise ValueError("parent_narrative must contain at least 2 paragraphs.")
    if not isinstance(parsed["actionable_tips"], list) or len(parsed["actionable_tips"]) < 3:
        raise ValueError("actionable_tips must contain at least 3 tips.")
    if not isinstance(parsed["weekly_progress"], str):
        raise ValueError("weekly_progress must be a string.")


def _normalize_llm_output(parsed):
    if not isinstance(parsed, dict):
        return parsed

    if "weekly_progress" not in parsed and "weeklyProgress" in parsed:
        parsed["weekly_progress"] = parsed["weeklyProgress"]

    narrative = _coerce_list(parsed.get("parent_narrative"))
    tips = _coerce_list(parsed.get("actionable_tips"))
    weekly = str(parsed.get("weekly_progress", "")).strip()

    if narrative is None:
        narrative = []
    if tips is None:
        tips = []

    while len(narrative) < 2:
        if weekly:
            narrative.append(weekly)
        else:
            narrative.append("The session showed useful learning signals across focus, activity, attendance, and homework.")

    while len(tips) < 3:
        tips.append("Review one key concept together before the next class.")

    parsed["parent_narrative"] = narrative
    parsed["weekly_progress"] = weekly or "Weekly progress was reviewed using attendance and homework signals."
    parsed["actionable_tips"] = tips
    return parsed


def _coerce_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in value.split("\n") if part.strip()]
    return value


def _metadata(used_llm, provider, model, error):
    return {
        "used_llm": used_llm,
        "provider": provider,
        "model": model,
        "error": error,
    }


def _max_output_tokens():
    try:
        value = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "300"))
    except ValueError:
        value = 300
    return max(180, min(value, 500))
