"""
main.py
Entry point for the Multi-Modal Session Insights Pipeline.
Processes user-provided session data from the data/ directory.
"""

def main():
    print("\n" + "=" * 60)
    print("  [*]  Multi-Modal Session Insights Pipeline  ")
    print("=" * 60 + "\n")

    # 1. Ingest data paths
    from src.ingest import load_data
    data = load_data("data")

    # 2. Vision analysis
    from src.vision_analysis import analyze_video
    vision = analyze_video(data["video_path"])

    # 3. Audio analysis
    from src.audio_analysis import analyze_audio
    audio = analyze_audio(data["audio_path"])

    # 4. Activity & attendance
    from src.context_engine import analyze_activity, analyze_attendance
    activity   = analyze_activity(data["activity"])
    attendance = analyze_attendance(data["attendance"])

    # 5. Homework parsing
    from src.homework_parser import parse_homework
    homework = parse_homework(data["homework_paths"])

    # 6. Generate JSON report
    from src.report_generator import generate_report
    student_name = data.get("activity", {}).get("student_name", "Student")
    session_id   = data.get("activity", {}).get("session_id", "session_01")

    report = generate_report(
        student_name   = student_name,
        session_id     = session_id,
        vision_data    = vision,
        audio_data     = audio,
        activity_data  = activity,
        attendance_data= attendance,
        homework_data  = homework,
    )

    # 7. Export HTML/PDF reports
    from src.export_report import export_to_html, export_to_pdf
    export_to_html(report)
    export_to_pdf(report)

    print("\n" + "=" * 60)
    print("  [OK] Pipeline complete!")
    print(f"  [>]  JSON  -> outputs/report.json")
    print(f"  [>]  HTML  -> outputs/report.html")
    print(f"  [>]  PDF   -> outputs/report.pdf")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
