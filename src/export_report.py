import os
import html

def export_to_html(report_data):
    """
    Uses Jinja2 to create a styled HTML report.
    """
    print("Exporting report to HTML...")

    try:
        from jinja2 import Environment, FileSystemLoader

        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("report_template.html")
        html_out = template.render(report=report_data)
    except Exception as e:
        print(f"Jinja2 template unavailable ({e}) -- using basic HTML export.")
        html_out = _basic_report_html(report_data)
    
    os.makedirs("outputs", exist_ok=True)
    html_path = os.path.join("outputs", "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_out)
        
    print(f"HTML report saved to {html_path}")


def export_to_pdf(report_data):
    """
    Creates a parent-friendly PDF report using ReportLab.
    """
    print("Exporting report to PDF...")

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except Exception as e:
        print(f"ReportLab unavailable ({e}) -- PDF export skipped.")
        return ""

    os.makedirs("outputs", exist_ok=True)
    pdf_path = os.path.join("outputs", "report.pdf")

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=30,
        textColor=colors.HexColor("#17202a"),
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#334155"),
        spaceAfter=8,
    )
    small_style = ParagraphStyle(
        "SmallMuted",
        parent=body_style,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#64748b"),
    )

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"{report_data.get('student_name', 'Student')} Session Insights",
    )

    story = []
    story.append(Paragraph(f"{_esc(report_data.get('student_name', 'Student'))} Session Insights", title_style))
    story.append(Paragraph(f"Session: {_esc(report_data.get('session_id', 'N/A'))}", small_style))
    story.append(Spacer(1, 12))

    metrics = report_data.get("quantitative_metrics", {})
    metric_rows = [
        ["Focus Index", _value(metrics.get("focus_index", "N/A"))],
        ["Speech Fluency", _value(metrics.get("speech_fluency", "N/A"))],
        ["Concept Mastery", _value(metrics.get("concept_mastery", "N/A"))],
        ["Attendance Rate", _value(metrics.get("attendance_rate", "N/A"))],
        ["Homework Quality", _value(metrics.get("homework_quality", "N/A"))],
    ]
    table = Table(metric_rows, colWidths=[2.15 * inch, 4.1 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#17202a")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dbe4ee")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)

    story.append(Paragraph("Parent Narrative", section_style))
    for paragraph in report_data.get("parent_narrative", []):
        story.append(Paragraph(_esc(paragraph), body_style))

    story.append(Paragraph("Weekly Progress", section_style))
    story.append(Paragraph(_esc(report_data.get("weekly_progress", "N/A")), body_style))

    story.append(Paragraph("Actionable Tips", section_style))
    for index, tip in enumerate(report_data.get("actionable_tips", []), start=1):
        story.append(Paragraph(f"{index}. {_esc(tip)}", body_style))

    story.append(Paragraph("Concept Areas", section_style))
    strengths = ", ".join(str(item) for item in report_data.get("strength_areas", [])) or "None yet"
    improvements = ", ".join(str(item) for item in report_data.get("improvement_areas", [])) or "None yet"
    story.append(Paragraph(f"<b>Strengths:</b> {_esc(strengths)}", body_style))
    story.append(Paragraph(f"<b>Needs Work:</b> {_esc(improvements)}", body_style))

    story.append(Paragraph("Detailed Signals", section_style))
    detail_rows = _detail_rows(report_data)
    detail_table = Table(detail_rows, colWidths=[2.15 * inch, 4.1 * inch])
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(detail_table)

    llm = report_data.get("llm_synthesis", {})
    story.append(Spacer(1, 12))
    llm_note = (
        f"LLM synthesis: {'Used' if llm.get('used_llm') else 'Fallback rules'}"
        f" | Provider: {llm.get('provider', 'none')}"
        f" | Model: {llm.get('model', '') or 'N/A'}"
    )
    story.append(Paragraph(_esc(llm_note), small_style))

    doc.build(story)
    print(f"PDF report saved to {pdf_path}")
    return pdf_path


def _detail_rows(report):
    vision = report.get("vision", {})
    audio = report.get("audio", {})
    activity = report.get("activity", {})
    attendance = report.get("attendance", {})
    homework = report.get("homework", {})
    return [
        ["Video", _value(vision.get("focus_summary", "No video data provided yet."))],
        ["Audio", _value(audio.get("speech_summary", "No audio data provided yet."))],
        ["Quiz Score", f"{_value(activity.get('quiz_score_percentage', 'N/A'))}%"],
        ["Canvas Completion", f"{_value(activity.get('canvas_completion_percentage', 'N/A'))}%"],
        ["Attendance", _value(attendance.get("weekly_consistency_summary", "No attendance data added yet."))],
        ["Homework Topics", _value(", ".join(homework.get("extracted_topics", [])) or "None yet")],
        ["Homework Status", _value(homework.get("completion_status", "N/A"))],
    ]


def _esc(value):
    return html.escape(str(value))


def _value(value):
    if isinstance(value, float):
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(value)


def _basic_report_html(report):
    esc = html.escape
    metrics = report.get("quantitative_metrics", {})
    narrative = report.get("parent_narrative", [])
    tips = report.get("actionable_tips", [])
    strengths = report.get("strength_areas", [])
    improvements = report.get("improvement_areas", [])

    metric_items = "".join(
        f"""<article class="metric">
          <span>{esc(label)}</span>
          <strong>{esc(str(value))}</strong>
        </article>"""
        for label, value in {
            "Focus Index": metrics.get("focus_index", "N/A"),
            "Speech Fluency": metrics.get("speech_fluency", "N/A"),
            "Concept Mastery": metrics.get("concept_mastery", "N/A"),
            "Attendance Rate": metrics.get("attendance_rate", "N/A"),
            "Homework Quality": metrics.get("homework_quality", "N/A"),
        }.items()
    )
    narrative_items = "".join(f"<p>{esc(str(item))}</p>" for item in narrative)
    tip_items = "".join(f"<li>{esc(str(item))}</li>" for item in tips)
    strength_items = "".join(f"<span class=\"pill good\">{esc(str(item))}</span>" for item in strengths)
    improvement_items = "".join(f"<span class=\"pill warm\">{esc(str(item))}</span>" for item in improvements)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(str(report.get("student_name", "Student")))} Learning Report</title>
  <style>
    :root {{
      --bg: #f3f5f2;
      --panel: #ffffff;
      --text: #20242a;
      --muted: #64706d;
      --line: #d9ded7;
      --green: #1f7a68;
      --blue: #2f5f9f;
      --amber: #b7791f;
      --rose: #b5475d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(180deg, #eef4ef 0, var(--bg) 310px);
      color: var(--text);
    }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 34px 22px 64px; }}
    .hero {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
      box-shadow: 0 18px 45px rgba(38, 45, 43, 0.11);
    }}
    .eyebrow {{
      color: var(--green);
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    h1 {{ margin: 0; font-size: clamp(30px, 5vw, 48px); line-height: 1.04; }}
    h2 {{ margin: 0 0 14px; font-size: 16px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .hero p {{ margin: 10px 0 0; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 14px;
      margin-top: 20px;
    }}
    .metric {{
      background: #fbfaf6;
      border: 1px solid #e2ded0;
      border-radius: 8px;
      padding: 16px;
    }}
    .metric span {{ color: var(--muted); font-size: 12px; font-weight: 700; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 28px; }}
    .grid {{ display: grid; grid-template-columns: 1.4fr 0.8fr; gap: 18px; margin-top: 18px; }}
    section {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      box-shadow: 0 8px 22px rgba(38, 45, 43, 0.06);
    }}
    ul {{ margin: 0; padding-left: 20px; color: var(--muted); line-height: 1.6; }}
    .pills {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .pill {{
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 800;
      border: 1px solid transparent;
    }}
    .good {{ background: #eaf7f3; color: var(--green); border-color: #bce1d7; }}
    .warm {{ background: #fff5df; color: var(--amber); border-color: #efd59d; }}
    .accent {{
      height: 4px;
      width: 100%;
      background: linear-gradient(90deg, var(--green), var(--blue), var(--amber), var(--rose));
      border-radius: 999px;
      margin-top: 18px;
    }}
    @media (max-width: 760px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <div class="hero">
      <div class="eyebrow">Learning Report</div>
      <h1>{esc(str(report.get("student_name", "Student")))} Session Insights</h1>
      <p>Session: {esc(str(report.get("session_id", "N/A")))}</p>
      <div class="metrics">{metric_items}</div>
      <div class="accent"></div>
    </div>
    <div class="grid">
      <section>
        <h2>Parent Summary</h2>
        {narrative_items}
        <p><strong>Weekly Progress:</strong> {esc(str(report.get("weekly_progress", "N/A")))}</p>
      </section>
      <section>
        <h2>Concept Areas</h2>
        <p>Strengths</p>
        <div class="pills">{strength_items or '<span class="pill good">None yet</span>'}</div>
        <p>Needs Work</p>
        <div class="pills">{improvement_items or '<span class="pill warm">None yet</span>'}</div>
      </section>
    </div>
    <section style="margin-top:18px"><h2>Recommendations</h2><ul>{tip_items}</ul></section>
  </main>
</body>
</html>"""

if __name__ == "__main__":
    export_to_html({"student_name": "Test", "quantitative_metrics": {}})
