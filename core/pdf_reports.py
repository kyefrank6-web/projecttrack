from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from decimal import Decimal

from .models import EvidenceCategory, School


def _pdf_header_elements(school: School, title: str, subtitle: str) -> list:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    sub_style = ParagraphStyle(
        "ReportSub",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceAfter=14,
    )
    elements = []
    if school.logo:
        try:
            logo = Image(school.logo.path, width=1.1 * inch, height=1.1 * inch)
            logo.hAlign = "CENTER"
            elements.append(logo)
            elements.append(Spacer(1, 8))
        except Exception:
            pass
    elements.append(Paragraph(f"<b>{school.name}</b>", title_style))
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(subtitle, sub_style))
    return elements


def _table_cell_style(name: str, *, font_size: int = 7, align=TA_LEFT) -> ParagraphStyle:
    styles = getSampleStyleSheet()
    return ParagraphStyle(
        name,
        parent=styles["Normal"],
        fontSize=font_size,
        leading=font_size + 2,
        alignment=align,
    )


def _supervisor_label(student) -> str:
    sup = student.supervisor
    return (sup.get_full_name() or sup.first_name or sup.username or "").strip()


def build_class_scores_pdf(
    *,
    school: School,
    class_level: str,
    year: int,
    term: int,
    scheme_name: str,
    competencies: list,
    students: list,
    by_student: dict,
    checklist=None,
) -> bytes:
    from .observation_utils import build_display_score_map
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    subtitle = f"Class {class_level} · Year {year} · Term {term} · Scheme: {scheme_name}"
    elements = _pdf_header_elements(school, "Secondary Project Score Sheet", subtitle)

    text_style = _table_cell_style("ScoreCell")
    headers = ["Student", "Supervisor", "No.", "Stream"] + [c.name for c in competencies]
    data = [headers]
    for s in students:
        a = by_student.get(s.id)
        score_map = build_display_score_map(
            a,
            checklist=checklist,
            student_id=s.id,
            year=year,
            term=term,
        )
        row = [
            Paragraph(s.full_name, text_style),
            Paragraph(_supervisor_label(s), text_style),
            s.student_no or "—",
            s.stream or "—",
        ]
        for c in competencies:
            val = score_map.get(c.id)
            row.append(f"{val}%" if val is not None else "—")
        data.append(row)

    page_w = landscape(A4)[0] - 0.9 * inch
    n_comp = len(competencies)
    comp_w = min(1.35 * inch, max(0.95 * inch, (page_w - 4.4 * inch) / max(n_comp, 1)))
    col_widths = [2.0 * inch, 1.55 * inch, 0.55 * inch, 0.55 * inch] + [comp_w] * n_comp
    scale = page_w / sum(col_widths)
    col_widths = [w * scale for w in col_widths]

    score_col_start = 4
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b5ed7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (1, -1), "LEFT"),
                ("ALIGN", (score_col_start, 1), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fb")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def build_class_project_titles_pdf(
    *,
    school: School,
    class_level: str,
    year: int,
    term: int,
    students: list,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    subtitle = f"Class {class_level} · Year {year} · Term {term}"
    elements = _pdf_header_elements(school, "Project Titles Register", subtitle)

    text_style = _table_cell_style("TitleCell", font_size=8)
    title_style = _table_cell_style("TitleProject", font_size=8)
    headers = ["Student", "Project title", "Supervisor", "No.", "Stream"]
    data = [headers]
    for s in students:
        data.append(
            [
                Paragraph(s.full_name, text_style),
                Paragraph(s.project_title or "—", title_style),
                Paragraph(_supervisor_label(s), text_style),
                s.student_no or "—",
                s.stream or "—",
            ]
        )

    page_w = landscape(A4)[0] - inch
    col_widths = [2.1 * inch, page_w - 2.1 * inch - 1.5 * inch - 0.6 * inch - 0.6 * inch, 1.5 * inch, 0.6 * inch, 0.6 * inch]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#198754")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                ("ALIGN", (2, 1), (4, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4faf6")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def build_class_evidence_pdf(
    *,
    school: School,
    class_level: str,
    students: list,
    evidence_by_student: dict[int, dict[str, object]],
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
    )

    subtitle = f"Class {class_level} · Photo evidence (Material identification, Project process, Final product)"
    elements = _pdf_header_elements(school, "Project Evidence Report", subtitle)
    styles = getSampleStyleSheet()
    student_style = ParagraphStyle(
        "StudentName",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#084298"),
    )
    label_style = ParagraphStyle(
        "CatLabel",
        parent=styles["Normal"],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
    )

    for idx, student in enumerate(students):
        if idx > 0:
            elements.append(PageBreak())
            elements.append(Spacer(1, 4))

        title_line = student.project_title or "—"
        elements.append(
            Paragraph(
                f"<b>Student:</b> {student.full_name}<br/>"
                f"<b>Project title:</b> {title_line}<br/>"
                f"<b>Supervisor:</b> {student.supervisor.username} · "
                f"{student.class_level} {student.stream or ''}",
                student_style,
            )
        )

        by_cat = evidence_by_student.get(student.id, {})
        img_row = []
        label_row = []
        for cat in EvidenceCategory:
            ev = by_cat.get(cat.value)
            label_row.append(Paragraph(f"<b>{cat.label}</b>", label_style))
            if ev and ev.file:
                try:
                    img = Image(ev.file.path, width=2.2 * inch, height=1.65 * inch, kind="proportional")
                except Exception:
                    img = Paragraph("Image unavailable", label_style)
            else:
                img = Paragraph("<i>Not uploaded</i>", label_style)
            img_row.append(img)

        t = Table([img_row, label_row], colWidths=[2.35 * inch] * 3)
        t.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(t)

    if not students:
        elements.append(Paragraph("No students in this class.", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _xml(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_student_scored_observation_pdf(
    *,
    school: School,
    student,
    checklist,
    year: int,
    term: int,
    observation_structure: list,
    observation_ratings: dict[int, int],
    competency_percentages: dict[int, Decimal],
    competency_headings: dict[str, str],
    checklist_document: dict,
    project_theme: str = "",
    assessed_by: str = "",
) -> bytes:
    """PDF of one learner's completed observation checklist (supervisor ticks + calculated %)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.55 * inch,
        rightMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "ObsBody",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        alignment=TA_LEFT,
    )
    section_title = ParagraphStyle(
        "SecTitle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold",
    )
    preamble_style = ParagraphStyle(
        "Preamble",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#444444"),
        fontName="Helvetica-Oblique",
    )
    comp_heading = ParagraphStyle(
        "CompHead",
        parent=styles["Heading2"],
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#0b5ed7"),
        spaceBefore=10,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
    )

    subtitle = (
        f"Scored observation checklist · Year {year} · Term {term} · "
        f"Class {student.class_level} {student.stream or ''}".strip()
    )
    elements = _pdf_header_elements(
        school,
        "Learner Project Observation Record",
        subtitle,
    )

    learner_block = [
        f"<b>Learner:</b> {_xml(student.full_name)}",
        f"<b>Student No:</b> {_xml(student.student_no or '—')}",
        f"<b>Project title:</b> {_xml(student.project_title or '—')}",
        f"<b>Supervisor:</b> {_xml(_supervisor_label(student))}",
    ]
    if assessed_by:
        learner_block.append(f"<b>Assessed by:</b> {_xml(assessed_by)}")
    elements.append(Paragraph("<br/>".join(learner_block), meta_style))
    if project_theme:
        elements.append(Spacer(1, 6))
        elements.append(
            Paragraph(f"<b>Project theme:</b> {_xml(project_theme)}", meta_style)
        )
    elements.append(Spacer(1, 10))

    if checklist_document:
        elements.append(
            Paragraph(f"<b>{_xml(checklist_document.get('board', ''))}</b>", meta_style)
        )
        elements.append(
            Paragraph(
                f"<i>{_xml(checklist_document.get('title', checklist.title))}</i>",
                meta_style,
            )
        )
        elements.append(Spacer(1, 8))

    for entry in observation_structure:
        comp = entry["competency"]
        heading = competency_headings.get(comp.name, comp.name)
        items = [item for sec in entry["sections"] for item in sec["items"] if item.max_rating > 0]
        met = sum(1 for item in items if observation_ratings.get(item.id, 0) > 0)
        total = len(items)
        pct = competency_percentages.get(comp.id)
        if pct is not None and total:
            summary = f"Indicators observed: {met} / {total} · Competency score: {pct}%"
        elif total:
            summary = f"Indicators observed: {met} / {total} · Not scored yet"
        else:
            summary = "Not scored yet"
        elements.append(Paragraph(f"<b>{_xml(heading)}</b>", comp_heading))
        elements.append(Paragraph(_xml(summary), body))
        elements.append(Spacer(1, 4))

        for section in entry["sections"]:
            sec_label = f"{section['code']} {section['title']}".strip()
            elements.append(Paragraph(_xml(sec_label), section_title))
            if section.get("preamble"):
                elements.append(Paragraph(_xml(section["preamble"]), preamble_style))

            rows = [["", "Observation", "Met"]]
            for item in section["items"]:
                if item.max_rating == 0:
                    rows.append(["", Paragraph(f"<b>{_xml(item.description)}</b>", body), ""])
                else:
                    rating = observation_ratings.get(item.id, 0)
                    mark = "Yes" if rating > 0 else "No"
                    rows.append(
                        [
                            "☑" if rating > 0 else "☐",
                            Paragraph(_xml(item.description), body),
                            mark,
                        ]
                    )
            col_widths = [0.35 * inch, 5.5 * inch, 0.55 * inch]
            table = Table(rows, colWidths=col_widths)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 7),
                        ("FONTSIZE", (0, 1), (-1, -1), 7),
                        ("ALIGN", (0, 0), (0, -1), "CENTER"),
                        ("ALIGN", (2, 0), (2, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            elements.append(table)
            elements.append(Spacer(1, 6))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
