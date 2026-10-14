"""Built-in ReportLab PDF Exporter Plugin with clickable citations and bibliography."""

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from app.config import settings
from app.models.reports import FinalReport, ReportArtifact
from app.models.research import RunStatus
from app.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class PDFExporterPlugin:
    """Exports validated research report to PDF with clickable SEC citations."""

    def __init__(self) -> None:
        self.manifest = PluginManifest(
            plugin_id="pdf",
            display_name="ReportLab PDF Report Exporter",
            version="1.0.0",
            api_version="1.0",
            plugin_type="report_exporter",
            capabilities=["report.pdf.export"],
            required_permissions=["filesystem.write.reports"],
            config_schema={"output_dir": {"type": "string"}},
            enabled_by_default=True,
        )

    def export(self, report: FinalReport, output_path: Path | str | None = None) -> ReportArtifact:
        """Renders report model to a publication-quality PDF."""
        out_dir = Path(settings.REPORT_OUTPUT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        if output_path:
            target_file = Path(output_path)
            target_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            filename = f"Apollo_Research_{report.ticker}_{report.run_id[:8]}.pdf"
            target_file = out_dir / filename

        doc = SimpleDocTemplate(
            str(target_file),
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#1A365D"),
            spaceAfter=12,
        )

        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#4A5568"),
            spaceAfter=16,
        )

        h1_style = ParagraphStyle(
            "Heading1Custom",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=8,
        )

        status_color = "#22543D" if report.is_complete else "#742A2A"
        status_bg = "#C6F6D5" if report.is_complete else "#FED7D7"
        status_text = "STATUS: COMPLETE (100% EVIDENCE SUPPORTED)" if report.is_complete else f"STATUS: {report.status.value} (RESEARCH LIMITATIONS APPLY)"

        status_style = ParagraphStyle(
            "StatusBanner",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(status_color),
            spaceAfter=12,
        )

        story = []

        # Header / Title Block
        story.append(Paragraph(f"Apollo Financial Research: {report.company_name} ({report.ticker})", title_style))
        story.append(
            Paragraph(
                f"<b>CIK:</b> {report.cik} &nbsp;|&nbsp; <b>Date:</b> {report.generated_at.strftime('%B %d, %Y')} "
                f"&nbsp;|&nbsp; <b>Run ID:</b> {report.run_id}",
                subtitle_style,
            )
        )

        # Status Banner
        story.append(
            Table(
                [[Paragraph(status_text, status_style)]],
                colWidths=[504],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(status_bg)),
                    ("PADDING", (0, 0), (-1, -1), 8),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(status_color)),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]),
            )
        )
        story.append(Spacer(1, 14))

        # Research Objective
        story.append(Paragraph("Research Objective", h1_style))
        story.append(Paragraph(report.objective, body_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=14))

        # Executive Summary
        story.append(Paragraph("Executive Summary", h1_style))
        story.append(Paragraph(report.executive_summary, body_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=14))

        # Sections
        # Build source URL map for clickable citations
        source_url_map = {b.source_id: b.source_url for b in report.bibliography}

        for section in report.sections:
            story.append(Paragraph(section.title, h1_style))
            # Format narrative paragraphs with clickable citation links
            for p in section.narrative.split("\n\n"):
                if not p.strip() or p.strip().startswith("###"):
                    continue

                formatted_p = p
                import re
                def _make_anchor(m: re.Match) -> str:
                    lbl = m.group(1).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    u = m.group(2).replace("&", "&amp;")
                    return f'<a href="{u}" color="#3182CE"><u>{lbl}</u></a>'

                formatted_p = re.sub(r'\[([^\]]+)\]\(((?:https?://|ftp://)[^\s\)]+)\)', _make_anchor, formatted_p)

                for src_id, url in source_url_map.items():
                    if src_id in formatted_p and f'href="{url}"' not in formatted_p:
                        link_html = f'<a href="{url}" color="#3182CE"><u>{src_id}</u></a>'
                        formatted_p = formatted_p.replace(src_id, link_html)

                formatted_p = re.sub(r'&(?!amp;|lt;|gt;|quot;|apos;)', '&amp;', formatted_p)
                story.append(Paragraph(formatted_p, body_style))

            if section.unresolved_questions:
                unres_text = (
                    f"<b>Unresolved Questions:</b> "
                    f"Information regarding {', '.join(section.unresolved_questions)} could not be verified in available filings."
                )
                story.append(Paragraph(f'<font color="#C53030">{unres_text}</font>', body_style))

            story.append(Spacer(1, 10))

        # Research Limitations (if any)
        if report.unresolved_limitations:
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=14))
            story.append(Paragraph("Disclosed Research Limitations", h1_style))
            for lim in report.unresolved_limitations:
                story.append(Paragraph(f"• {lim}", body_style))

        # Primary Source Bibliography Table
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E2E8F0"), spaceAfter=14))
        story.append(Paragraph("Primary Source Bibliography & SEC Filings", h1_style))
        story.append(
            Paragraph(
                "All material factual claims trace directly to the official SEC EDGAR primary source documents below. "
                "Click on any link to open the verified filing on sec.gov.",
                body_style,
            )
        )
        story.append(Spacer(1, 8))

        table_data = [
            [
                Paragraph("<b>Source ID</b>", body_style),
                Paragraph("<b>Form</b>", body_style),
                Paragraph("<b>Filing Date</b>", body_style),
                Paragraph("<b>Period</b>", body_style),
                Paragraph("<b>Official SEC EDGAR Link</b>", body_style),
            ]
        ]

        for item in report.bibliography:
            link_cell = Paragraph(
                f'<a href="{item.source_url}" color="#3182CE"><u>{item.accession_number}</u></a>',
                body_style,
            )
            table_data.append([
                Paragraph(item.source_id, body_style),
                Paragraph(item.form_type, body_style),
                Paragraph(item.filed_at, body_style),
                Paragraph(item.period_of_report, body_style),
                link_cell,
            ])

        bib_table = Table(table_data, colWidths=[110, 45, 65, 65, 219])
        bib_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(bib_table)

        # Build PDF
        doc.build(story)

        # Compute file stats & sha256
        with open(target_file, "rb") as f:
            pdf_bytes = f.read()

        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        artifact_id = f"ART_PDF_{report.run_id[:8]}"

        logger.info("Generated PDF report artifact at %s (%d bytes, sha256: %s)", target_file, len(pdf_bytes), file_hash[:10])

        return ReportArtifact(
            artifact_id=artifact_id,
            run_id=report.run_id,
            format="PDF",
            file_path=str(target_file.resolve()),
            sha256=file_hash,
            file_size_bytes=len(pdf_bytes),
            is_complete=report.is_complete,
            generated_at=datetime.now(timezone.utc),
        )


def create_plugin() -> PDFExporterPlugin:
    return PDFExporterPlugin()
