"""
Streamlit app for the Multi-Modal Session Insights Pipeline.

The app accepts activity JSON and attendance JSON as the required structured
inputs. Video, audio, and homework PDFs are optional supporting files.
"""

import json
import os
from pathlib import Path

from main import main as run_pipeline


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

DEFAULT_OLLAMA_MODEL = "llama3.2:1b"
DEFAULT_LLM_TOKENS = 300


def ensure_dirs():
    for name in ("activity", "attendance", "audio", "video", "homework"):
        (DATA_DIR / name).mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)


def clear_inputs():
    for folder_name in ("audio", "video", "homework"):
        folder = DATA_DIR / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        for item in folder.iterdir():
            if item.is_file():
                item.unlink()

    for path in (
        DATA_DIR / "activity" / "activity_log.json",
        DATA_DIR / "attendance" / "attendance.json",
    ):
        if path.exists():
            path.unlink()


def clear_outputs():
    OUTPUT_DIR.mkdir(exist_ok=True)
    for filename in ("report.json", "report.html", "report.pdf"):
        path = OUTPUT_DIR / filename
        if path.exists():
            path.unlink()


def safe_filename(filename):
    filename = filename.replace("\\", "/").split("/")[-1]
    keep = "".join(ch for ch in filename if ch.isalnum() or ch in ("-", "_", ".", " "))
    keep = keep.strip(" .")
    return keep.replace(" ", "_") or "upload"


def write_json_file(data, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_uploaded_binary(uploaded_file, folder):
    if uploaded_file is None:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe_filename(uploaded_file.name)
    path.write_bytes(uploaded_file.getbuffer())
    return path


def save_uploaded_json(uploaded_file, path):
    if uploaded_file is None:
        return None
    parsed = json.loads(uploaded_file.getvalue().decode("utf-8"))
    write_json_file(parsed, path)
    return parsed


def load_report():
    report_path = OUTPUT_DIR / "report.json"
    if not report_path.exists():
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))


def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def apply_llm_settings(model=None, max_output_tokens=None):
    selected_model = model or DEFAULT_OLLAMA_MODEL
    selected_tokens = max_output_tokens or DEFAULT_LLM_TOKENS

    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_MODEL"] = selected_model
    os.environ["LLM_MAX_OUTPUT_TOKENS"] = str(selected_tokens)
    os.environ.setdefault("OLLAMA_URL", "http://localhost:11434/api/generate")

    return {
        "provider": os.environ["LLM_PROVIDER"],
        "model": selected_model,
        "max_output_tokens": selected_tokens,
    }


def render_api_sidebar(st):
    with st.sidebar:
        st.header("Local LLM")
        model = st.text_input("Ollama model", value=DEFAULT_OLLAMA_MODEL)
        llm_settings = apply_llm_settings(model=model.strip() or DEFAULT_OLLAMA_MODEL)
        st.divider()
        st.success(f"Ollama required: {llm_settings['model']}")
        st.caption("Runs locally through http://localhost:11434. No API key is needed.")


def render_saved_files(st):
    rows = []
    for path in sorted(DATA_DIR.glob("*/*")):
        if path.is_file():
            rows.append({"File": str(path.relative_to(BASE_DIR)), "Size": format_file_size(path.stat().st_size)})
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.caption("No uploaded files saved yet.")


def render_report_preview(st, report):
    if not report:
        st.info("No report yet. Fill the session details and click Generate report.")
        return

    metrics = report.get("quantitative_metrics", {})
    st.markdown("## Report preview")
    st.caption(f"{report.get('student_name', 'Student')} · {report.get('session_id', 'N/A')}")

    cols = st.columns(5)
    cols[0].metric("Focus", f"{metrics.get('focus_index', 'N/A')}/100")
    cols[1].metric("Speech", f"{metrics.get('speech_fluency', 'N/A')}/100")
    cols[2].metric("Mastery", f"{metrics.get('concept_mastery', 'N/A')}%")
    cols[3].metric("Attendance", f"{metrics.get('attendance_rate', 'N/A')}%")
    cols[4].metric("Homework", metrics.get("homework_quality", "N/A"))

    left, right = st.columns([1.25, 0.85])
    with left:
        st.markdown("### Parent summary")
        for paragraph in report.get("parent_narrative", []):
            st.write(paragraph)
        st.write(f"**Weekly Progress:** {report.get('weekly_progress', 'N/A')}")

    with right:
        st.markdown("### Concept areas")
        strengths = report.get("strength_areas", [])
        improvements = report.get("improvement_areas", [])
        st.write("**Strengths**")
        st.write(", ".join(strengths) if strengths else "None yet")
        st.write("**Needs Work**")
        st.write(", ".join(improvements) if improvements else "None yet")

    st.markdown("### Recommendations")
    for tip in report.get("actionable_tips", []):
        st.write(f"- {tip}")

    llm = report.get("llm_synthesis", {})
    st.success(f"LLM synthesis used before PDF/HTML export: {llm.get('provider')} / {llm.get('model')}")

    st.divider()
    download_a, download_b, download_c = st.columns(3)
    report_html = OUTPUT_DIR / "report.html"
    report_pdf = OUTPUT_DIR / "report.pdf"
    if report_pdf.exists():
        download_a.download_button(
            "Download PDF Report",
            data=report_pdf.read_bytes(),
            file_name="report.pdf",
            mime="application/pdf",
            width="stretch",
        )
    if report_html.exists():
        download_b.download_button(
            "Download HTML Report",
            data=report_html.read_bytes(),
            file_name="report.html",
            mime="text/html",
            width="stretch",
        )
    download_c.download_button(
        "Download JSON Report",
        data=json.dumps(report, indent=2).encode("utf-8"),
        file_name="report.json",
        mime="application/json",
        width="stretch",
    )


def main():
    import streamlit as st

    ensure_dirs()
    if "show_report_preview" not in st.session_state:
        st.session_state.show_report_preview = False

    st.set_page_config(page_title="Session Insights", page_icon="SI", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
        h1 { margin-bottom: 0.4rem; }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 14px;
        }
        .small-note {
            color: rgba(250, 250, 250, 0.66);
            font-size: 0.92rem;
            line-height: 1.5;
        }
        .section-card {
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 8px;
            padding: 1.1rem 1.1rem 0.6rem;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Session Insights")
    st.write("Enter one class session, generate the learning report, and review the result here.")

    render_api_sidebar(st)

    with st.form("upload_form"):
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### 1. Session details")
        col_a, col_b, col_c = st.columns(3)
        student_name = col_a.text_input(
            "Student name optional",
            placeholder="Example: Aarav",
            help="Used in the report title and parent narrative. If blank, the app uses Student.",
        )
        session_id = col_b.text_input(
            "Session ID optional",
            placeholder="Example: session_01",
            help="Used to label the generated JSON, HTML, and PDF report.",
        )
        subject = col_c.text_input(
            "Subject optional",
            placeholder="Example: Mathematics",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### 2. Upload JSON files")
        json_a, json_b = st.columns(2)
        activity_upload = json_a.file_uploader(
            "Activity JSON required",
            type=["json"],
            help="Upload activity_log.json.",
        )
        attendance_upload = json_b.file_uploader(
            "Attendance JSON required",
            type=["json"],
            help="Upload attendance.json.",
        )
        with st.expander("Paste JSON instead of uploading files"):
            activity_text = st.text_area("Activity JSON text", height=160)
            attendance_text = st.text_area("Attendance JSON text", height=160)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### 3. Add supporting files")
        file_a, file_b, file_c = st.columns(3)
        video_upload = file_a.file_uploader("Class video optional", type=["mp4", "mov", "avi", "mkv", "webm"])
        audio_upload = file_b.file_uploader("Class audio optional", type=["wav", "mp3", "m4a", "flac", "ogg"])
        homework_uploads = file_c.file_uploader(
            "Homework PDFs optional",
            type=["pdf"],
            accept_multiple_files=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("### 4. Generate")
        replace_files = st.checkbox("Replace previous uploads before saving", value=True)
        st.markdown(
            '<p class="small-note">Leave this checked for normal use. Turn it off only when adding more homework PDFs to the same session.</p>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        submitted = st.form_submit_button("Generate report", type="primary", width="stretch")

    if submitted:
        try:
            if replace_files:
                clear_inputs()
                clear_outputs()

            activity = save_uploaded_json(activity_upload, DATA_DIR / "activity" / "activity_log.json")
            if activity is None and activity_text.strip():
                activity = json.loads(activity_text)
            if activity is None:
                raise ValueError("Activity JSON is required.")
            if student_name.strip():
                activity["student_name"] = student_name.strip()
            if session_id.strip():
                activity["session_id"] = session_id.strip()
            if subject.strip():
                activity["subject"] = subject.strip()
            write_json_file(activity, DATA_DIR / "activity" / "activity_log.json")

            attendance = save_uploaded_json(attendance_upload, DATA_DIR / "attendance" / "attendance.json")
            if attendance is None and attendance_text.strip():
                attendance = json.loads(attendance_text)
            if attendance is None:
                raise ValueError("Attendance JSON is required.")
            write_json_file(attendance, DATA_DIR / "attendance" / "attendance.json")

            save_uploaded_binary(video_upload, DATA_DIR / "video")
            save_uploaded_binary(audio_upload, DATA_DIR / "audio")
            for upload in homework_uploads or []:
                save_uploaded_binary(upload, DATA_DIR / "homework")

            with st.spinner("Generating report..."):
                run_pipeline()
            st.session_state.show_report_preview = True
            st.success("Report generated. Review it below.")
        except Exception as exc:
            st.session_state.show_report_preview = False
            st.error(f"Could not save data: {exc}")

    tab_output, tab_files, tab_json = st.tabs(["Report", "Uploaded files", "Raw report JSON"])
    report = load_report() if st.session_state.show_report_preview else None
    with tab_output:
        render_report_preview(st, report)
    with tab_files:
        render_saved_files(st)
    with tab_json:
        if report:
            st.json(report)
        else:
            st.caption("No report JSON generated yet.")


if __name__ == "__main__":
    main()
