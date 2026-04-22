from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.config import get_settings
from backend.models import Evaluation, Grade, Submission


settings = get_settings()


def _dedupe_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items or []:
        normalized = " ".join(str(item).split()).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(str(item).strip())
    return deduped


def _truncate_text(value: str, limit: int = 220) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    if not cleaned:
        return "Insufficient data"
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _dedupe_weak_sections(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for item in items or []:
        criterion = str(item.get("criterion", "Unknown")).strip()
        reason = _truncate_text(item.get("reason", "Insufficient data"), limit=180)
        key = (criterion.lower(), reason.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "criterion": criterion,
                "reason": reason,
                "excerpt": _truncate_text(item.get("excerpt", "Insufficient data"), limit=240),
            }
        )
    return deduped


def _bullet_paragraphs(items: list[str], style: ParagraphStyle) -> list[Paragraph]:
    items = _dedupe_items(items)
    if not items:
        return [Paragraph("Insufficient data", style)]
    return [Paragraph(f"&bull; {item}", style) for item in items]


def generate_submission_report(submission: Submission, evaluation: Evaluation, grade: Grade | None = None) -> Path:
    report_path = settings.reports_dir / f"submission_{submission.id}_report.pdf"
    document = SimpleDocTemplate(str(report_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    heading_style = styles["Heading2"]
    body_style = styles["BodyText"]

    story = [
        Paragraph("AI Course Project Evaluation Report", title_style),
        Spacer(1, 12),
        Paragraph(f"Student: {submission.student.name}", body_style),
        Paragraph(f"Email: {submission.student.email}", body_style),
        Paragraph(f"Submission Title: {submission.title}", body_style),
        Paragraph(f"Submission ID: {submission.id}", body_style),
        Paragraph(f"Evaluation Type: {'Draft' if evaluation.draft else 'Final'}", body_style),
        Spacer(1, 16),
    ]

    feedback = evaluation.feedback or {}
    rubric_weights = feedback.get("rubric_weights", []) if isinstance(feedback, dict) else []
    rubric_scores = feedback.get("rubric_scores", {}) if isinstance(feedback, dict) else {}

    score_rows = [["Criterion", "Score"]]
    if rubric_weights:
        for rubric in rubric_weights:
            key = rubric.get("key")
            score_rows.append([str(rubric.get("name", "Rubric")), str(rubric_scores.get(key, "Insufficient data"))])
    else:
        score_rows.extend(
            [
                ["Innovation", str(evaluation.innovation_score)],
                ["Technical Depth", str(evaluation.technical_score)],
                ["Clarity", str(evaluation.clarity_score)],
                ["Impact", str(evaluation.impact_score)],
            ]
        )
    score_rows.append(["Weighted Total", str(evaluation.total_score)])
    if grade:
        score_rows.append(["Final Marks", str(grade.final_score)])
        score_rows.append(["Class Rank", f"#{grade.rank}"])

    table = Table(score_rows, hAlign="LEFT", colWidths=[220, 180])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([table, Spacer(1, 18)])

    feedback_sections = [
        ("Strengths", feedback.get("strengths", [])),
        ("Weaknesses", feedback.get("weaknesses", [])),
        ("Suggestions", feedback.get("suggestions", [])),
        ("Future Scope", feedback.get("future_scope", [])),
    ]
    for heading, items in feedback_sections:
        story.append(Paragraph(heading, heading_style))
        story.extend(_bullet_paragraphs(items, body_style))
        story.append(Spacer(1, 10))

    story.append(Paragraph("Weak Sections", heading_style))
    weak_sections = _dedupe_weak_sections((evaluation.weak_sections or [])[:3])
    if weak_sections:
        for item in weak_sections:
            criterion = item.get("criterion", "Unknown")
            excerpt = item.get("excerpt", "Insufficient data")
            reason = item.get("reason", "Insufficient data")
            story.append(Paragraph(f"<b>{criterion.title()}</b>: {reason}", body_style))
            story.append(Paragraph(excerpt, body_style))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("Insufficient data", body_style))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Plagiarism Similarity Matches", heading_style))
    matches = evaluation.plagiarism_matches or []
    if matches:
        for match in matches:
            story.append(
                Paragraph(
                    f"&bull; {match['student_name']} (Submission {match['submission_id']}): similarity {match['similarity']}",
                    body_style,
                )
            )
    else:
        story.append(Paragraph("No high-similarity matches detected.", body_style))

    document.build(story)
    return report_path
