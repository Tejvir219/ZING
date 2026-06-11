import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.audio_analysis import analyze_audio
from src.export_report import export_to_html, export_to_pdf
from src.homework_parser import parse_homework
from src.ingest import load_data
from src.report_generator import generate_report
from src.vision_analysis import analyze_video


class PipelineTests(unittest.TestCase):
    def test_load_data_uses_user_files_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in ("activity", "attendance", "audio", "video", "homework"):
                (base / name).mkdir()
            (base / "activity" / "activity_log.json").write_text(
                '{"student_name":"Asha"}', encoding="utf-8"
            )
            (base / "attendance" / "attendance.json").write_text(
                '{"attendance":[]}', encoding="utf-8"
            )
            (base / "audio" / "b.wav").write_bytes(b"audio-b")
            (base / "audio" / "a.mp3").write_bytes(b"audio-a")
            (base / "video" / "session.webm").write_bytes(b"video")
            (base / "homework" / "z.pdf").write_bytes(b"pdf-z")
            (base / "homework" / "a.pdf").write_bytes(b"pdf-a")

            data = load_data(str(base))

            self.assertEqual(data["activity"]["student_name"], "Asha")
            self.assertTrue(data["audio_path"].endswith("a.mp3"))
            self.assertTrue(data["video_path"].endswith("session.webm"))
            self.assertTrue(data["homework_paths"][0].endswith("a.pdf"))

    def test_missing_media_returns_empty_metrics_not_sample_values(self):
        self.assertEqual(analyze_video("")["average_focus_score"], 0)
        self.assertEqual(analyze_audio("")["fluency_score"], 0)
        self.assertEqual(parse_homework([])["completion_quality"], "N/A")

    def test_generate_report_for_empty_data_is_neutral(self):
        with tempfile.TemporaryDirectory() as tmp:
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                with patch("src.report_generator.synthesize_report_sections") as synthesize:
                    synthesize.return_value = {
                        "used_llm": True,
                        "provider": "ollama",
                        "model": "llama3.2:1b",
                        "error": "",
                        "parent_narrative": ["Ollama summary paragraph one.", "Ollama summary paragraph two."],
                        "weekly_progress": "Ollama weekly progress.",
                        "actionable_tips": ["Tip one.", "Tip two.", "Tip three."],
                    }
                    report = generate_report(
                        student_name="Student",
                        session_id="session_01",
                        vision_data=analyze_video(""),
                        audio_data=analyze_audio(""),
                        activity_data={},
                        attendance_data={},
                        homework_data=parse_homework([]),
                    )
            finally:
                os.chdir(original_cwd)

            self.assertEqual(report["parent_narrative"][0], "Ollama summary paragraph one.")
            self.assertEqual(report["weekly_progress"], "Ollama weekly progress.")
            self.assertTrue(report["llm_synthesis"]["used_llm"])
            self.assertTrue((Path(tmp) / "outputs" / "report.json").exists())

    def test_export_to_html_writes_report_without_jinja_dependency_requirement(self):
        report = {
            "student_name": "Student",
            "session_id": "session_01",
            "quantitative_metrics": {},
            "parent_narrative": ["Ready for data."],
            "weekly_progress": "No attendance data added yet.",
            "actionable_tips": ["Add data."],
        }

        with tempfile.TemporaryDirectory() as tmp:
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                export_to_html(report)
            finally:
                os.chdir(original_cwd)

            html_path = Path(tmp) / "outputs" / "report.html"
            self.assertTrue(html_path.exists())
            self.assertIn("Student Session Insights", html_path.read_text(encoding="utf-8"))

    def test_export_to_pdf_writes_real_pdf_report(self):
        report = {
            "student_name": "Student",
            "session_id": "session_01",
            "quantitative_metrics": {
                "focus_index": 86,
                "speech_fluency": 57,
                "concept_mastery": 80,
                "attendance_rate": 100,
                "homework_quality": "Good",
            },
            "parent_narrative": ["Strong focus today.", "Keep practicing fractions."],
            "weekly_progress": "Attendance was consistent this week.",
            "actionable_tips": ["Read aloud.", "Practice fractions.", "Review homework."],
            "strength_areas": ["addition"],
            "improvement_areas": ["fractions"],
        }

        with tempfile.TemporaryDirectory() as tmp:
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp)
                pdf_path = export_to_pdf(report)
            finally:
                os.chdir(original_cwd)

            path = Path(tmp) / pdf_path
            self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
