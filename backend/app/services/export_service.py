"""OmniSight Inspection History & Report Export Service.

Provides export capabilities for:
1. Complete inspection history as CSV.
2. Individual inspection run details as CSV.
3. Individual inspection reports as high-fidelity executive PDFs (with findings, screenshots, and repair decisions).
4. Inspection history audit summary as executive PDF.

Guarantees:
- Never exposes secrets, internal credentials, or sensitive query tokens in URLs/messages.
- Handles empty history and failed runs gracefully.
- Integrates screenshots and visual evidence cleanly when available on storage.
"""

from __future__ import annotations

import csv
import io
import os
import re
import xml.sax.saxutils as saxutils
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.schemas.artifacts import ArtifactResponse
from backend.app.schemas.findings import FindingResponse
from backend.app.schemas.proposals import RepairProposalResponse
from backend.app.schemas.runs import RunResponse

# Sensitive parameter names and tokens to mask in URLs
SENSITIVE_PARAM_NAMES = {
    "token",
    "api_key",
    "apikey",
    "key",
    "secret",
    "access_token",
    "auth",
    "authorization",
    "password",
    "pass",
    "passwd",
    "client_secret",
    "session",
    "sig",
    "signature",
    "bearer",
    "private_key",
}

ARTIFACTS_DIR = Path("artifacts").resolve()


def sanitize_url_credentials(raw_url: str | None) -> str:
    """Mask embedded username:password and sensitive query parameters in a URL."""
    if not raw_url:
        return ""
    clean = str(raw_url).strip()
    try:
        parts = urlsplit(clean)
        if not parts.scheme and not parts.netloc:
            return sanitize_secrets(clean)

        netloc = parts.netloc
        # Redact userinfo: e.g. user:password@host -> ***:***@host
        if "@" in netloc:
            _, host = netloc.split("@", 1)
            netloc = f"***:***@{host}"

        # Redact sensitive query parameters
        query_pairs = parse_qsl(parts.query, keep_blank_values=True)
        sanitized_pairs = []
        for k, v in query_pairs:
            k_lower = k.lower()
            if (
                k_lower in SENSITIVE_PARAM_NAMES
                or any(sub in k_lower for sub in ("token", "secret", "password", "api_key", "apikey"))
            ):
                sanitized_pairs.append((k, "***"))
            else:
                sanitized_pairs.append((k, v))

        sanitized_query = "&".join(f"{k}={v}" for k, v in sanitized_pairs)
        reconstructed = urlunsplit((parts.scheme, netloc, parts.path, sanitized_query, parts.fragment))
        return sanitize_secrets(reconstructed)
    except Exception:
        return sanitize_secrets(clean)


def sanitize_secrets(text: str | None) -> str:
    """Mask credentials, tokens, bearer authorizations, or passwords in plain text."""
    if not text:
        return ""
    # Mask embedded user:pass in URLs within text
    masked = re.sub(r"([a-zA-Z]+://)([^:/\s]+):([^@/\s]+)@", r"\1***:***@", str(text))
    # Mask key=value or key: value
    masked = re.sub(
        r'((?:api[_-]?key|token|secret|password|passwd|auth[_-]?token|access[_-]?token)\s*[:=]\s*[\'"]?)([^\'"\s&,]+)([\'"]?)',
        r"\1***\3",
        masked,
        flags=re.IGNORECASE,
    )
    # Mask Bearer tokens
    masked = re.sub(
        r"(bearer\s+)([A-Za-z0-9_\-\.]{8,})",
        r"\1***",
        masked,
        flags=re.IGNORECASE,
    )
    return masked


def calculate_run_duration_seconds(created_at: str | None, completed_at: str | None) -> float | None:
    """Calculate elapsed duration in seconds between created_at and completed_at."""
    if not created_at or not completed_at:
        return None
    try:
        t0 = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        diff = (t1 - t0).total_seconds()
        return round(diff, 1) if diff >= 0 else None
    except Exception:
        return None


def compute_severity_counts(findings: Sequence[FindingResponse] | None) -> dict[str, int]:
    """Calculate defect counts by severity level."""
    counts = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
    if not findings:
        return counts
    counts["total"] = len(findings)
    for f in findings:
        sev = (f.severity or "low").lower()
        if sev in counts:
            counts[sev] += 1
        else:
            counts["low"] += 1
    return counts


# =============================================================================
# CSV Export Functions
# =============================================================================


def generate_history_csv(
    runs: Sequence[RunResponse],
    findings_map: dict[str, list[FindingResponse]] | None = None,
) -> str:
    """Generate CSV string for inspection run history.

    Columns:
    Run ID, Target URL, Status, Viewports, Created At (UTC), Completed At (UTC),
    Duration (s), Total Findings, Critical, High, Medium, Low, Message / Error.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    writer.writerow([
        "Run ID",
        "Target URL",
        "Status",
        "Viewports",
        "Created At (UTC)",
        "Completed At (UTC)",
        "Duration (s)",
        "Total Findings",
        "Critical Findings",
        "High Findings",
        "Medium Findings",
        "Low Findings",
        "Message / Error",
    ])

    findings_map = findings_map or {}

    for r in runs:
        run_findings = findings_map.get(r.run_id, [])
        sev = compute_severity_counts(run_findings)
        duration = calculate_run_duration_seconds(r.created_at, r.completed_at)
        viewports_str = ", ".join(r.viewports) if r.viewports else "desktop"

        error_or_message = r.error if r.status == "failed" and r.error else (r.message or "")
        sanitized_msg = sanitize_secrets(error_or_message)
        sanitized_url = sanitize_url_credentials(r.url)

        writer.writerow([
            r.run_id,
            sanitized_url,
            (r.status or "").upper(),
            viewports_str,
            r.created_at or "",
            r.completed_at or "",
            f"{duration:.1f}" if duration is not None else "",
            sev["total"],
            sev["critical"],
            sev["high"],
            sev["medium"],
            sev["low"],
            sanitized_msg,
        ])

    return output.getvalue()


def generate_run_csv(
    run: RunResponse,
    findings: Sequence[FindingResponse],
    proposals: Sequence[RepairProposalResponse] | None = None,
) -> str:
    """Generate detailed CSV string for an individual inspection run.

    Outputs run metadata paired with each defect finding and associated repair proposal.
    If run has 0 findings, outputs a single row with run metadata and empty finding fields.
    """
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    writer.writerow([
        "Run ID",
        "Target URL",
        "Status",
        "Viewports",
        "Run Created At (UTC)",
        "Run Completed At (UTC)",
        "Duration (s)",
        "Finding ID",
        "Category",
        "Severity",
        "Confidence",
        "Viewport",
        "Selector",
        "Description",
        "Screenshot Path",
        "DOM Snapshot Path",
        "Repair Proposal ID",
        "Repair Approval Status",
        "Proposed Change",
        "Reviewer Notes",
        "Run Error / Message",
    ])

    duration = calculate_run_duration_seconds(run.created_at, run.completed_at)
    viewports_str = ", ".join(run.viewports) if run.viewports else "desktop"
    sanitized_url = sanitize_url_credentials(run.url)
    err_or_msg = sanitize_secrets(run.error if run.status == "failed" and run.error else (run.message or ""))

    # Map proposals by finding_id for quick pairing
    proposal_by_finding: dict[str, RepairProposalResponse] = {}
    if proposals:
        for p in proposals:
            if p.finding_id:
                proposal_by_finding[p.finding_id] = p

    if not findings:
        # Single row representing run with no defects detected or failed before inspection
        writer.writerow([
            run.run_id,
            sanitized_url,
            (run.status or "").upper(),
            viewports_str,
            run.created_at or "",
            run.completed_at or "",
            f"{duration:.1f}" if duration is not None else "",
            "None",
            "None",
            "None",
            "",
            "None",
            "None",
            "No defects detected" if run.status == "completed" else "None",
            "",
            "",
            "",
            "",
            "",
            "",
            err_or_msg,
        ])
        return output.getvalue()

    for f in findings:
        matched_prop = proposal_by_finding.get(f.finding_id)
        prop_id = matched_prop.proposal_id if matched_prop else ""
        prop_status = (matched_prop.approval_status or "").upper() if matched_prop else ""
        prop_change = matched_prop.proposed_change if matched_prop else ""
        prop_notes = matched_prop.reviewer_notes or "" if matched_prop else ""

        ss_path = f.evidence.screenshot_path if f.evidence else ""
        dom_path = f.evidence.dom_snapshot_path if f.evidence else ""

        writer.writerow([
            run.run_id,
            sanitized_url,
            (run.status or "").upper(),
            viewports_str,
            run.created_at or "",
            run.completed_at or "",
            f"{duration:.1f}" if duration is not None else "",
            f.finding_id,
            f.category,
            (f.severity or "").upper(),
            f"{f.confidence:.2f}" if f.confidence is not None else "",
            getattr(f, "viewport", "desktop") or "desktop",
            f.selector or "",
            sanitize_secrets(f.description),
            ss_path or "",
            dom_path or "",
            prop_id,
            prop_status,
            sanitize_secrets(prop_change),
            sanitize_secrets(prop_notes),
            err_or_msg,
        ])

    return output.getvalue()


# =============================================================================
# ReportLab Canvas & Styling Helpers
# =============================================================================


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas that adds dynamic 'Page X of Y' numbers and running headers/footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 756, "OmniSight • Multimodal UI Self-Healing & RPA Agent • Inspection Audit")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, 750, 576, 750)

        # Running footer (all pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(36, 40, 576, 40)
        self.drawString(
            36,
            26,
            "Confidential • All credentials redacted • OmniSight Autonomous Inspection Engine",
        )
        self.drawRightString(576, 26, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def _get_export_styles() -> dict[str, ParagraphStyle]:
    """Build polished typography styles for ReportLab documents."""
    base_styles = getSampleStyleSheet()

    custom_styles = {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            alignment=0,
            spaceAfter=4,
        ),
        "DocSubtitle": ParagraphStyle(
            "DocSubtitle",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=12,
        ),
        "SectionHeader": ParagraphStyle(
            "SectionHeader",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "SubSectionHeader": ParagraphStyle(
            "SubSectionHeader",
            parent=base_styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        ),
        "BodyBold": ParagraphStyle(
            "BodyBold",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#0f172a"),
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#ffffff"),
            alignment=0,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base_styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        ),
        "CodeText": ParagraphStyle(
            "CodeText",
            parent=base_styles["Normal"],
            fontName="Courier",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#0f172a"),
        ),
        "BadgeText": ParagraphStyle(
            "BadgeText",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#ffffff"),
            alignment=1,
        ),
        "Caption": ParagraphStyle(
            "Caption",
            parent=base_styles["Italic"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b"),
            alignment=1,
            spaceBefore=4,
            spaceAfter=10,
        ),
    }

    return custom_styles


def _get_severity_color(severity: str) -> colors.Color:
    """Return theme color for a defect severity level."""
    s = (severity or "low").lower()
    if s == "critical":
        return colors.HexColor("#dc2626")
    elif s == "high":
        return colors.HexColor("#ea580c")
    elif s == "medium":
        return colors.HexColor("#d97706")
    return colors.HexColor("#2563eb")


def _get_status_color(status: str) -> colors.Color:
    """Return theme color for an execution status."""
    st = (status or "").lower()
    if st == "completed":
        return colors.HexColor("#16a34a")
    elif st in ("failed", "cancelled", "error"):
        return colors.HexColor("#dc2626")
    elif st in ("capturing", "analyzing", "repairing", "verifying"):
        return colors.HexColor("#2563eb")
    return colors.HexColor("#64748b")


# =============================================================================
# PDF Report Generation (Individual Run)
# =============================================================================


def generate_run_pdf(
    run: RunResponse,
    findings: Sequence[FindingResponse],
    proposals: Sequence[RepairProposalResponse] | None = None,
    artifacts: Sequence[ArtifactResponse] | None = None,
) -> bytes:
    """Generate high-fidelity executive PDF inspection report for an individual run."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46,
    )
    styles = _get_export_styles()
    story = []

    # 1. Header Banner & Identity
    sanitized_url = sanitize_url_credentials(run.url)
    gen_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    story.append(Paragraph("<b>OmniSight Inspection Report</b>", styles["DocTitle"]))
    story.append(
        Paragraph(
            f"Autonomous Multimodal UI Inspection &amp; Self-Healing Audit &bull; Generated: {gen_time_str}",
            styles["DocSubtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=12))

    # 2. Executive Overview Table
    duration = calculate_run_duration_seconds(run.created_at, run.completed_at)
    duration_str = f"{duration:.1f}s" if duration is not None else ("In progress" if run.status not in ("completed", "failed", "cancelled") else "—")
    viewports_str = ", ".join(v.capitalize() for v in (run.viewports or ["desktop"]))

    status_color = _get_status_color(run.status)
    status_label = (run.status or "UNKNOWN").upper()

    overview_data = [
        [
            Paragraph("<b>Run Identifier</b>", styles["BodyBold"]),
            Paragraph(f"<code>{saxutils.escape(run.run_id)}</code>", styles["CodeText"]),
            Paragraph("<b>Inspection Status</b>", styles["BodyBold"]),
            Paragraph(
                f"<font color='{status_color.hexval()}'><b>{saxutils.escape(status_label)}</b></font>",
                styles["BodyBold"],
            ),
        ],
        [
            Paragraph("<b>Target URL</b>", styles["BodyBold"]),
            Paragraph(f"<code>{saxutils.escape(sanitized_url)}</code>", styles["CodeText"]),
            Paragraph("<b>Viewports</b>", styles["BodyBold"]),
            Paragraph(saxutils.escape(viewports_str), styles["Body"]),
        ],
        [
            Paragraph("<b>Created At (UTC)</b>", styles["BodyBold"]),
            Paragraph(saxutils.escape(run.created_at or "—"), styles["Body"]),
            Paragraph("<b>Duration</b>", styles["BodyBold"]),
            Paragraph(saxutils.escape(duration_str), styles["Body"]),
        ],
    ]

    overview_table = Table(
        overview_data,
        colWidths=[110, 210, 100, 120],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]),
    )
    story.append(overview_table)
    story.append(Spacer(1, 10))

    # 3. Failed Run Banner (if failed)
    if run.status in ("failed", "cancelled") or run.error:
        err_msg = sanitize_secrets(run.error or run.message or "Inspection run terminated prematurely.")
        fail_table = Table(
            [[
                Paragraph(
                    f"<b>Inspection Anomaly / Failure Alert:</b><br/>"
                    f"{saxutils.escape(err_msg)}",
                    styles["Body"],
                )
            ]],
            colWidths=[540],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#f87171")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#991b1b")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]),
        )
        story.append(fail_table)
        story.append(Spacer(1, 10))

    # 4. Defect Severity Summary
    sev = compute_severity_counts(findings)
    story.append(Paragraph("<b>Defect Severity Summary</b>", styles["SectionHeader"]))

    summary_table_data = [
        [
            Paragraph("<b>Total Findings</b>", styles["TableHeader"]),
            Paragraph("<b>Critical</b>", styles["TableHeader"]),
            Paragraph("<b>High</b>", styles["TableHeader"]),
            Paragraph("<b>Medium</b>", styles["TableHeader"]),
            Paragraph("<b>Low</b>", styles["TableHeader"]),
        ],
        [
            Paragraph(f"<b>{sev['total']}</b>", styles["TableCellBold"]),
            Paragraph(f"<font color='#dc2626'><b>{sev['critical']}</b></font>", styles["TableCellBold"]),
            Paragraph(f"<font color='#ea580c'><b>{sev['high']}</b></font>", styles["TableCellBold"]),
            Paragraph(f"<font color='#d97706'><b>{sev['medium']}</b></font>", styles["TableCellBold"]),
            Paragraph(f"<font color='#2563eb'><b>{sev['low']}</b></font>", styles["TableCellBold"]),
        ],
    ]
    summary_table = Table(
        summary_table_data,
        colWidths=[108, 108, 108, 108, 108],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]),
    )
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # 5. Defect Findings Breakdown
    story.append(Paragraph("<b>Detailed UI Defect Findings</b>", styles["SectionHeader"]))

    if not findings:
        clean_note = (
            "✓ No visual defects or layout anomalies were detected for this inspection run. "
            "The target web page complies with all visual integrity, visibility, and responsiveness criteria."
            if run.status == "completed"
            else "No defect findings recorded."
        )
        clean_table = Table(
            [[Paragraph(clean_note, styles["Body"])]],
            colWidths=[540],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4") if run.status == "completed" else colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#86efac") if run.status == "completed" else colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]),
        )
        story.append(clean_table)
        story.append(Spacer(1, 12))
    else:
        for idx, f in enumerate(findings, start=1):
            sev_color = _get_severity_color(f.severity)
            cat_label = f.category.replace("_", " ").title()
            conf_pct = f"{int(f.confidence * 100)}%" if f.confidence is not None else "100%"
            vp_label = (getattr(f, "viewport", "desktop") or "desktop").capitalize()

            finding_rows = [
                [
                    Paragraph(f"<b>Finding #{idx}: {saxutils.escape(f.finding_id)}</b>", styles["BodyBold"]),
                    Paragraph(
                        f"<font color='{sev_color.hexval()}'><b>{(f.severity or 'LOW').upper()}</b></font> &bull; "
                        f"Category: <b>{saxutils.escape(cat_label)}</b> &bull; "
                        f"Viewport: <b>{saxutils.escape(vp_label)}</b> &bull; "
                        f"Confidence: <b>{conf_pct}</b>",
                        styles["Body"],
                    ),
                ],
                [
                    Paragraph("<b>Affected Selector</b>", styles["BodyBold"]),
                    Paragraph(f"<code>{saxutils.escape(f.selector or 'None identified')}</code>", styles["CodeText"]),
                ],
                [
                    Paragraph("<b>Description</b>", styles["BodyBold"]),
                    Paragraph(saxutils.escape(sanitize_secrets(f.description)), styles["Body"]),
                ],
            ]

            finding_box = Table(
                finding_rows,
                colWidths=[120, 420],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]),
            )
            story.append(KeepTogether([finding_box, Spacer(1, 8)]))

    # 6. Visual Evidence (Screenshots)
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Visual Evidence &amp; Screen Artifacts</b>", styles["SectionHeader"]))

    # Scan for screenshot artifacts on local disk
    candidate_images = []
    run_dir = ARTIFACTS_DIR / run.run_id

    # Viewport-specific or general before/after screenshots
    for stage, label in [("before", "Initial Inspection"), ("after", "Proposed Correction Preview")]:
        # Primary stage image
        primary = run_dir / f"{stage}.png"
        if primary.is_file():
            candidate_images.append((primary, f"{label} (Desktop)"))

        # Viewport variants
        for vp in ["desktop", "tablet", "mobile"]:
            vp_img = run_dir / f"{stage}_{vp}.png"
            if vp_img.is_file() and vp_img != primary:
                candidate_images.append((vp_img, f"{label} ({vp.capitalize()})"))

    # Also check artifacts passed from backend
    if artifacts:
        for art in artifacts:
            if "screenshot" in (art.artifact_type or "").lower():
                art_p = Path(art.storage_path)
                if not art_p.is_absolute():
                    art_p = (ARTIFACTS_DIR / art_p).resolve()
                if art_p.is_file() and not any(p == art_p for p, _ in candidate_images):
                    candidate_images.append((art_p, f"Visual Artifact ({art.artifact_type})"))

    if candidate_images:
        for img_path, caption in candidate_images[:4]:  # Embed up to 4 primary visual captures
            try:
                with PILImage.open(img_path) as pil_im:
                    orig_w, orig_h = pil_im.size
                # Constrain within page width (540 pt) and max height 220 pt preserving aspect ratio
                max_w, max_h = 480.0, 210.0
                ratio = min(max_w / orig_w, max_h / orig_h)
                render_w = orig_w * ratio
                render_h = orig_h * ratio

                rl_image = RLImage(str(img_path), width=render_w, height=render_h)
                caption_p = Paragraph(f"Figure: {saxutils.escape(caption)}", styles["Caption"])
                story.append(KeepTogether([rl_image, caption_p]))
            except Exception:
                # If PIL or image fails to read, fall back to textual path notice
                story.append(
                    Paragraph(
                        f"Visual Artifact: <code>{saxutils.escape(str(img_path.name))}</code>",
                        styles["Body"],
                    )
                )
    else:
        story.append(
            Paragraph(
                "No visual screenshot files present on storage for this run.",
                styles["Caption"],
            )
        )

    # 7. Self-Healing & Repair Approval Decisions
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Self-Healing &amp; Repair Approval Decisions</b>", styles["SectionHeader"]))
    story.append(
        Paragraph(
            "OmniSight strictly operates under human-in-the-loop review. Proposed code, CSS, "
            "and locator fixes are never applied to the target live website automatically.",
            styles["DocSubtitle"],
        )
    )

    if proposals:
        for p in proposals:
            app_status = (p.approval_status or "pending").upper()
            status_c = (
                colors.HexColor("#16a34a")
                if app_status == "APPROVED"
                else (colors.HexColor("#dc2626") if app_status == "REJECTED" else colors.HexColor("#d97706"))
            )

            prop_rows = [
                [
                    Paragraph(f"<b>Proposal {saxutils.escape(p.proposal_id)}</b>", styles["BodyBold"]),
                    Paragraph(
                        f"Review Decision: <font color='{status_c.hexval()}'><b>{saxutils.escape(app_status)}</b></font> &bull; "
                        f"Linked Finding: <code>{saxutils.escape(p.finding_id or 'General')}</code>",
                        styles["Body"],
                    ),
                ],
                [
                    Paragraph("<b>Proposed Patch / Locator</b>", styles["BodyBold"]),
                    Paragraph(f"<code>{saxutils.escape(sanitize_secrets(p.proposed_change))}</code>", styles["CodeText"]),
                ],
            ]

            if p.reviewer_notes:
                prop_rows.append([
                    Paragraph("<b>Reviewer Notes</b>", styles["BodyBold"]),
                    Paragraph(saxutils.escape(sanitize_secrets(p.reviewer_notes)), styles["Body"]),
                ])

            if p.github_pr_url:
                prop_rows.append([
                    Paragraph("<b>GitHub Pull Request</b>", styles["BodyBold"]),
                    Paragraph(f"<code>{saxutils.escape(p.github_pr_url)}</code>", styles["CodeText"]),
                ])

            prop_table = Table(
                prop_rows,
                colWidths=[130, 410],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ]),
            )
            story.append(KeepTogether([prop_table, Spacer(1, 8)]))
    else:
        story.append(
            Paragraph(
                "No repair proposals currently recorded for this inspection run.",
                styles["Body"],
            )
        )

    # Build PDF with custom NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


# =============================================================================
# PDF Report Generation (Inspection History Summary)
# =============================================================================


def generate_history_pdf(
    runs: Sequence[RunResponse],
    findings_map: dict[str, list[FindingResponse]] | None = None,
) -> bytes:
    """Generate executive audit summary PDF for all available historical inspection runs."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46,
    )
    styles = _get_export_styles()
    story = []

    findings_map = findings_map or {}
    gen_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Header Banner
    story.append(Paragraph("<b>OmniSight Inspection History &amp; Audit Log</b>", styles["DocTitle"]))
    story.append(
        Paragraph(
            f"Executive Audit Summary of Persisted Inspection Runs &bull; Generated: {gen_time_str}",
            styles["DocSubtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f172a"), spaceAfter=12))

    # 2. High-Level Metrics
    total_runs = len(runs)
    completed_runs = sum(1 for r in runs if (r.status or "").lower() == "completed")
    in_flight_runs = sum(
        1 for r in runs if (r.status or "").lower() in ("queued", "capturing", "analyzing", "repairing", "verifying")
    )
    failed_runs = sum(1 for r in runs if (r.status or "").lower() in ("failed", "cancelled", "error"))

    total_defects = sum(len(findings_map.get(r.run_id, [])) for r in runs)

    metrics_data = [
        [
            Paragraph("<b>Total Audited Runs</b>", styles["TableHeader"]),
            Paragraph("<b>Completed Runs</b>", styles["TableHeader"]),
            Paragraph("<b>In-Flight Runs</b>", styles["TableHeader"]),
            Paragraph("<b>Failed / Anomalies</b>", styles["TableHeader"]),
            Paragraph("<b>Total Detected Defects</b>", styles["TableHeader"]),
        ],
        [
            Paragraph(f"<b>{total_runs}</b>", styles["TableCellBold"]),
            Paragraph(f"<font color='#16a34a'><b>{completed_runs}</b></font>", styles["TableCellBold"]),
            Paragraph(f"<font color='#2563eb'><b>{in_flight_runs}</b></font>", styles["TableCellBold"]),
            Paragraph(f"<font color='{('#dc2626' if failed_runs > 0 else '#64748b')}'><b>{failed_runs}</b></font>", styles["TableCellBold"]),
            Paragraph(f"<b>{total_defects}</b>", styles["TableCellBold"]),
        ],
    ]
    metrics_table = Table(
        metrics_data,
        colWidths=[108, 108, 108, 108, 108],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ffffff")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]),
    )
    story.append(metrics_table)
    story.append(Spacer(1, 14))

    # 3. Runs Table
    story.append(Paragraph("<b>Recorded Inspection Runs</b>", styles["SectionHeader"]))

    if not runs:
        empty_table = Table(
            [[Paragraph("No historical inspection runs recorded in the database.", styles["Body"])]],
            colWidths=[540],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]),
        )
        story.append(empty_table)
    else:
        table_rows = [
            [
                Paragraph("<b>Run ID</b>", styles["TableHeader"]),
                Paragraph("<b>Target URL</b>", styles["TableHeader"]),
                Paragraph("<b>Status</b>", styles["TableHeader"]),
                Paragraph("<b>Viewports</b>", styles["TableHeader"]),
                Paragraph("<b>Created At</b>", styles["TableHeader"]),
                Paragraph("<b>Duration</b>", styles["TableHeader"]),
                Paragraph("<b>Defects (C/H/M/L)</b>", styles["TableHeader"]),
            ]
        ]

        for idx, r in enumerate(runs):
            run_findings = findings_map.get(r.run_id, [])
            sev = compute_severity_counts(run_findings)
            duration = calculate_run_duration_seconds(r.created_at, r.completed_at)
            dur_str = f"{duration:.1f}s" if duration is not None else ("Running..." if r.status not in ("completed", "failed", "cancelled") else "—")
            viewports_str = ", ".join(r.viewports) if r.viewports else "desktop"

            st_color = _get_status_color(r.status)
            defects_summary = f"{sev['total']} ({sev['critical']}/{sev['high']}/{sev['medium']}/{sev['low']})"

            # Truncate target URL if excessively long
            sanitized_url = sanitize_url_credentials(r.url)
            display_url = sanitized_url if len(sanitized_url) <= 32 else f"{sanitized_url[:30]}..."

            created_display = r.created_at[:16].replace("T", " ") if r.created_at else "—"

            table_rows.append([
                Paragraph(f"<code>{saxutils.escape(r.run_id)}</code>", styles["CodeText"]),
                Paragraph(f"<code>{saxutils.escape(display_url)}</code>", styles["CodeText"]),
                Paragraph(f"<font color='{st_color.hexval()}'><b>{(r.status or '').upper()}</b></font>", styles["TableCellBold"]),
                Paragraph(saxutils.escape(viewports_str), styles["TableCell"]),
                Paragraph(saxutils.escape(created_display), styles["TableCell"]),
                Paragraph(saxutils.escape(dur_str), styles["TableCell"]),
                Paragraph(saxutils.escape(defects_summary), styles["TableCellBold"]),
            ])

        history_table = Table(
            table_rows,
            colWidths=[75, 130, 65, 75, 80, 50, 65],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]),
        )
        story.append(history_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
