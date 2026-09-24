import io
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from typing import Any

def generate_assessment_pdf(
    report_data: dict,
    analysis_data: dict,
    hse_review: dict = None,
    workflow_status: str = "PENDING",
    audit_trail: list = None
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=20
    )
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=15,
        spaceAfter=8,
        textTransform='uppercase'
    )
    normal_style = styles['Normal']
    alert_style = ParagraphStyle(
        'AlertStyle',
        parent=styles['Normal'],
        textColor=colors.HexColor("#ef4444"),
        fontName="Helvetica-Bold",
        spaceAfter=10
    )
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor("#64748b"),
        alignment=1 # Center
    )

    story = []

    # synthetic data warning
    is_synthetic = report_data.get("source", "").lower() == "synthetic"
    if is_synthetic:
        story.append(Paragraph("SYNTHETIC / DEMONSTRATION DATA", alert_style))

    # Header
    story.append(Paragraph("SIF SENTINEL", title_style))
    story.append(Paragraph("Safety Assessment Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=1, spaceAfter=15))

    # Metadata Table
    meta_data = [
        ["Report ID:", report_data.get("id", "N/A"), "Source File:", report_data.get("source_file_name", "N/A")],
        ["Location:", report_data.get("location", "N/A"), "Source Type:", report_data.get("source", "N/A")],
        ["Date:", str(report_data.get("created_at", "N/A"))[:16], "Report Type:", report_data.get("report_type", "N/A")]
    ]
    meta_table = Table(meta_data, colWidths=[1.2*inch, 2.5*inch, 1.2*inch, 2.5*inch])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#334155")),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # OBSERVATION
    story.append(Paragraph("OBSERVATION", section_style))
    story.append(Paragraph(report_data.get("report_text", ""), normal_style))
    
    # SAFETY ASSESSMENT
    story.append(Paragraph("SAFETY ASSESSMENT", section_style))
    assessment_data = [
        ["Activity", analysis_data.get("activity") or "N/A"],
        ["Hazard", analysis_data.get("hazard") or "N/A"],
        ["Critical Barrier", analysis_data.get("barrier") or "N/A"],
        ["Barrier Status", analysis_data.get("barrier_status") or "N/A"],
        ["Priority", analysis_data.get("priority", "N/A")]
    ]
    assessment_table = Table(assessment_data, colWidths=[1.5*inch, 4*inch])
    assessment_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(assessment_table)

    # SAFETY SIGNIFICANCE
    story.append(Paragraph("SAFETY SIGNIFICANCE", section_style))
    sif_prob = analysis_data.get("sif_probability", 0)
    story.append(Paragraph(f"SIF Precursor Signal Probability: {sif_prob*100:.1f}%", normal_style))

    # EVIDENCE (Triggered rules)
    story.append(Paragraph("EVIDENCE", section_style))
    rules = analysis_data.get("triggered_rules", [])
    if rules:
        for r in rules:
            rname = r.get("rule_name", "Rule")
            rsev = r.get("severity_label", "")
            rexp = r.get("explanation", "")
            story.append(Paragraph(f"<b>{rname} ({rsev})</b>", normal_style))
            story.append(Paragraph(f"{rexp}", normal_style))
            story.append(Spacer(1, 5))
    else:
        story.append(Paragraph("No critical safety rules triggered.", normal_style))

    # DECISION RATIONALE
    story.append(Paragraph("DECISION RATIONALE", section_style))
    story.append(Paragraph(analysis_data.get("explanation", "N/A"), normal_style))

    # HSE REVIEW
    if hse_review:
        story.append(Paragraph("HSE REVIEW", section_style))
        review_data = [
            ["Decision", hse_review.get("decision", "N/A")],
            ["Reviewer", hse_review.get("reviewer_id", "N/A")],
            ["Review Date", str(hse_review.get("reviewed_at", ""))[:16]],
            ["Comments", hse_review.get("comments", "None")]
        ]
        review_table = Table(review_data, colWidths=[1.5*inch, 4*inch])
        review_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(review_table)

    # ACTION STATUS
    story.append(Paragraph("ACTION STATUS", section_style))
    story.append(Paragraph(f"Current Workflow State: {workflow_status}", normal_style))

    # AUDIT TRAIL
    if audit_trail and len(audit_trail) > 0:
        story.append(Paragraph("AUDIT TRAIL", section_style))
        for log in audit_trail:
            action = log.get("action", "")
            actor = log.get("actor_id", "")
            date = str(log.get("created_at", ""))[:16]
            story.append(Paragraph(f"<b>{date}</b> - {action} by {actor}", normal_style))
            story.append(Spacer(1, 4))

    # Footer
    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=1, spaceAfter=10))
    footer_text = "AI-assisted safety triage. This assessment identifies potential precursor signals and does not predict accidents. Final safety decisions remain subject to HSE review."
    story.append(Paragraph(footer_text, footer_style))
    
    if is_synthetic:
        story.append(Paragraph("SYNTHETIC / DEMONSTRATION DATA", footer_style))

    doc.build(story)
    return buffer.getvalue()
