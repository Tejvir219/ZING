"""
src/report_generator.py
Aggregates all analysis outputs into a structured JSON report.
Uses local Ollama to generate parent-friendly narratives and tips.
"""

import json
import os

from src.llm_synthesizer import synthesize_report_sections


def generate_report(student_name, session_id,
                    vision_data, audio_data, activity_data,
                    attendance_data, homework_data):
    """
    Combines metrics from all pipeline modules into a structured report dict.
    Saves report.json to outputs/ and returns the dict.
    """
    print("[Report] Generating structured JSON report...")

    focus    = vision_data.get("average_focus_score", 0)
    fluency  = audio_data.get("fluency_score", 0)
    mastery  = activity_data.get("quiz_score_percentage", 0)
    att_rate = attendance_data.get("attendance_rate", 0)
    hw_qual  = homework_data.get("completion_quality", "N/A")

    strong   = activity_data.get("strong_concepts", [])
    weak     = activity_data.get("weak_concepts", [])
    # Required Ollama synthesis
    llm_context = {
        "student_name": student_name,
        "session_id": session_id,
        "metrics": {
            "focus_index": focus,
            "speech_fluency": fluency,
            "concept_mastery": round(mastery, 1),
            "attendance_rate": round(att_rate, 1),
            "homework_quality": hw_qual,
        },
        "strength_areas": strong,
        "improvement_areas": weak,
        "vision": vision_data,
        "audio": audio_data,
        "activity": activity_data,
        "attendance": attendance_data,
        "homework": homework_data,
    }
    llm_sections = synthesize_report_sections(llm_context)

    narrative = llm_sections["parent_narrative"]
    weekly_progress = llm_sections["weekly_progress"]
    tips = llm_sections["actionable_tips"]
    tips = _exactly_three_tips(tips, student_name, strong)

    # â”€â”€ Build final report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    report = {
        "student_name": student_name,
        "session_id":   session_id,
        "quantitative_metrics": {
            "focus_index":      focus,
            "speech_fluency":   fluency,
            "concept_mastery":  round(mastery, 1),
            "attendance_rate":  round(att_rate, 1),
            "homework_quality": hw_qual,
        },
        "parent_narrative": narrative,
        "weekly_progress": weekly_progress,
        "actionable_tips": tips,
        "strength_areas":    strong,
        "improvement_areas": weak,
        "llm_synthesis": {
            "used_llm": llm_sections.get("used_llm", True),
            "provider": llm_sections.get("provider", "ollama"),
            "model": llm_sections.get("model", ""),
            "error": llm_sections.get("error", ""),
        },
        # Detailed module outputs for the HTML template
        "vision":    vision_data,
        "audio":     audio_data,
        "activity":  activity_data,
        "attendance": attendance_data,
        "homework":  homework_data,
    }

    os.makedirs("outputs", exist_ok=True)
    path = os.path.join("outputs", "report.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[Report] JSON saved -> {path}")

    return report


def _exactly_three_tips(tips, student_name, strong):
    defaults = [
        f"Spend 10 minutes reviewing today's strongest topic with {student_name} so the learning stays fresh.",
        "Ask one open-ended question after class, such as what felt easy and what felt confusing.",
        f"Give {student_name} a short practice task in {', '.join(strong or ['the current subject'])} before the next session.",
    ]

    cleaned = []
    for tip in tips + defaults:
        if tip and tip not in cleaned:
            cleaned.append(tip)
        if len(cleaned) == 3:
            break
    return cleaned
