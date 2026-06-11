"""
src/homework_parser.py
Real PDF text extraction using PyMuPDF (fitz).
Applies keyword matching and length heuristics for quality scoring.
"""

import os
import re

# Keywords that signal topic coverage
TOPIC_KEYWORDS = {
    "multiplication": ["multiplication", "multiply", "times", "product", "×"],
    "fractions":      ["fraction", "numerator", "denominator", "half", "quarter", "1/2", "3/4"],
    "division":       ["division", "divide", "quotient", "÷"],
    "addition":       ["addition", "add", "sum", "plus"],
    "subtraction":    ["subtraction", "subtract", "minus", "difference"],
    "word problems":  ["word problem", "total", "how many", "how much", "find the"],
    "geometry":       ["triangle", "circle", "square", "rectangle", "perimeter", "area"],
    "states of matter": ["solid", "liquid", "gas", "evaporation", "condensation", "matter"],
    "science":        ["science", "experiment", "hypothesis", "observation"],
}

COMPLETION_KEYWORDS = ["completed", "done", "finished", "all answers", "submitted", "score"]
DELAY_KEYWORDS      = ["late", "overdue", "pending", "incomplete", "missing"]


def parse_homework(homework_paths):
    """
    Extracts text from each homework PDF using PyMuPDF, then scores
    quality, identifies topics, and checks completion status.
    Returns aggregated metrics across all files.
    """
    print(f"[Homework] Parsing {len(homework_paths)} file(s)...")

    if not homework_paths:
        return _empty_result()

    all_texts    = []
    all_topics   = set()
    all_statuses = []

    for path in homework_paths:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            print(f"[Homework] Skipping empty/missing file: {path}")
            continue

        text = _extract_text(path)
        if text:
            all_texts.append(text)
            topics   = _detect_topics(text)
            all_topics.update(topics)
            status   = _detect_completion(text)
            all_statuses.append(status)
            print(f"[Homework] {os.path.basename(path)}: {len(text)} chars | topics: {topics} | {status}")

    if not all_texts:
        print("[Homework] No readable text found.")
        return _empty_result()

    # ── Aggregate metrics ─────────────────────────────────────────────────────
    combined_text  = " ".join(all_texts)
    total_chars    = len(combined_text)
    quality        = _quality_score(combined_text)
    completion     = "Completed" if all(s == "Completed" for s in all_statuses) else "Partially Completed"
    delay_status   = _detect_delay(combined_text)

    return {
        "extracted_topics":   sorted(all_topics),
        "completion_status":  completion,
        "delay_status":       delay_status,
        "completion_quality": quality,
        "total_text_length":  total_chars
    }


def _extract_text(path):
    """Extract all text from a PDF using PyMuPDF."""
    try:
        import fitz   # PyMuPDF
        doc  = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except ImportError:
        print("[Homework] PyMuPDF not installed — trying plain-text read.")
        try:
            with open(path, 'r', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""
    except Exception as e:
        print(f"[Homework] Could not read {path}: {e}")
        return ""


def _detect_topics(text):
    """Return list of matched topics based on keyword presence."""
    text_lower = text.lower()
    matched = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            matched.append(topic)
    return matched


def _detect_completion(text):
    text_lower = text.lower()
    if any(kw in text_lower for kw in COMPLETION_KEYWORDS):
        return "Completed"
    return "Incomplete"


def _detect_delay(text):
    text_lower = text.lower()
    if any(kw in text_lower for kw in DELAY_KEYWORDS):
        return "Delayed"
    return "On Time"


def _quality_score(text):
    """
    Rule-based quality heuristic:
      ≥ 500 chars  + completion keywords → Good
      ≥ 200 chars                        → Average
      < 200 chars                        → Needs Improvement
    """
    length     = len(text)
    text_lower = text.lower()
    has_completion = any(kw in text_lower for kw in COMPLETION_KEYWORDS)

    if length >= 500 and has_completion:
        return "Good"
    elif length >= 200:
        return "Average"
    else:
        return "Needs Improvement"


def _empty_result():
    return {
        "extracted_topics":   [],
        "completion_status":  "No homework found",
        "delay_status":       "N/A",
        "completion_quality": "N/A",
        "total_text_length":  0
    }

if __name__ == "__main__":
    import json
    result = parse_homework([
        "../data/homework/worksheet_1.pdf",
        "../data/homework/worksheet_2.pdf"
    ])
    print(json.dumps(result, indent=2))
