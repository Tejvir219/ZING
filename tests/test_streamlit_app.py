import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import streamlit_app


class StreamlitAppHelperTests(unittest.TestCase):
    def test_safe_filename_cleans_upload_names(self):
        self.assertEqual(streamlit_app.safe_filename("../Activity Log!.json"), "Activity_Log.json")

    def test_save_uploaded_json_writes_formatted_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            upload = SimpleNamespace(
                name="activity.json",
                getvalue=lambda: b'{"quiz":[]}',
            )
            path = Path(tmp) / "activity" / "activity_log.json"

            parsed = streamlit_app.save_uploaded_json(upload, path)

            self.assertEqual(parsed, {"quiz": []})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"quiz": []})

    def test_save_uploaded_binary_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            upload = SimpleNamespace(
                name="speech audio.wav",
                getbuffer=lambda: memoryview(b"audio"),
            )

            path = streamlit_app.save_uploaded_binary(upload, Path(tmp))

            self.assertEqual(path.name, "speech_audio.wav")
            self.assertEqual(path.read_bytes(), b"audio")

    def test_clear_outputs_removes_previous_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            original_output_dir = streamlit_app.OUTPUT_DIR
            try:
                streamlit_app.OUTPUT_DIR = Path(tmp)
                for name in ("report.json", "report.html", "report.pdf"):
                    (Path(tmp) / name).write_text("old", encoding="utf-8")

                streamlit_app.clear_outputs()

                self.assertFalse((Path(tmp) / "report.json").exists())
                self.assertFalse((Path(tmp) / "report.html").exists())
                self.assertFalse((Path(tmp) / "report.pdf").exists())
            finally:
                streamlit_app.OUTPUT_DIR = original_output_dir

    def test_format_file_size_is_readable(self):
        self.assertEqual(streamlit_app.format_file_size(500), "500 B")
        self.assertEqual(streamlit_app.format_file_size(1536), "1.5 KB")

    def test_apply_llm_settings_sets_ollama_environment(self):
        old_values = {name: os.environ.get(name) for name in ("LLM_PROVIDER", "OLLAMA_MODEL", "LLM_MAX_OUTPUT_TOKENS", "OLLAMA_URL")}
        try:
            streamlit_app.apply_llm_settings(model="llama3.2:1b", max_output_tokens=300)

            self.assertEqual(os.environ["LLM_PROVIDER"], "ollama")
            self.assertEqual(os.environ["OLLAMA_MODEL"], "llama3.2:1b")
            self.assertEqual(os.environ["LLM_MAX_OUTPUT_TOKENS"], "300")
            self.assertEqual(os.environ["OLLAMA_URL"], "http://localhost:11434/api/generate")
        finally:
            for name, value in old_values.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

    def test_apply_llm_settings_always_uses_ollama(self):
        old_values = {name: os.environ.get(name) for name in ("LLM_PROVIDER", "OLLAMA_MODEL", "LLM_MAX_OUTPUT_TOKENS")}
        try:
            os.environ["LLM_PROVIDER"] = "none"
            streamlit_app.apply_llm_settings(model="llama3.2:1b", max_output_tokens=300)

            self.assertEqual(os.environ["LLM_PROVIDER"], "ollama")
            self.assertEqual(os.environ["OLLAMA_MODEL"], "llama3.2:1b")
            self.assertEqual(os.environ["LLM_MAX_OUTPUT_TOKENS"], "300")
        finally:
            for name, value in old_values.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

if __name__ == "__main__":
    unittest.main()
