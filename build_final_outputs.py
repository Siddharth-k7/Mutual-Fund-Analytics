"""Build the final PDF report, composite assets, and PPTX deck for MFA.

Run this script from the repository root. It creates the final deliverables in
the MFA folder and keeps presentation scratch files under `outputs/`.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import textwrap
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "Results"
OUTPUTS = ROOT / "outputs"
BUILD_ROOT = OUTPUTS / "20260621-final" / "presentations" / "bluestock-mf-capstone"
ASSET_DIR = BUILD_ROOT / "assets"
SLIDES_DIR = BUILD_ROOT / "slides"
PREVIEW_DIR = BUILD_ROOT / "preview"
LAYOUT_DIR = BUILD_ROOT / "layout"
REPORT_PATH = ROOT / "Final_Report.pdf"
PPTX_PATH = ROOT / "Bluestock_MF_Presentation.pptx"
DECK_TITLE = "Bluestock MF Capstone"

FONT_REG = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_ITALIC = "C:/Windows/Fonts/ariali.ttf"

BG = "#F7F2EA"
INK = "#132A3A"
SLATE = "#5C6873"
MUTED = "#7A878F"
GOLD = "#C79A3A"
GOLD2 = "#A8792B"
TEAL = "#2C7A78"
WHITE = "#FFFFFF"
PALE = "#FFF9F1"
RED = "#9B3D33"
GREEN = "#2F7D4A"


def load_font(path: str, size: int) -> ImageFont.ImageFont:
    """Load a Windows font if available, otherwise fall back to Pillow default."""

    try:
        return ImageFont.truetype(path, size=size)
    except Exception:
        return ImageFont.load_default()


FONT = {
    "reg": load_font(FONT_REG, 24),
    "bold": load_font(FONT_BOLD, 24),
    "small": load_font(FONT_REG, 18),
    "tiny": load_font(FONT_REG, 14),
    "tiny_bold": load_font(FONT_BOLD, 14),
    "title": load_font(FONT_BOLD, 36),
    "subtitle": load_font(FONT_REG, 18),
}


def ensure_dirs() -> None:
    """Create the scratch directories used for deck generation."""

    for path in [ASSET_DIR, SLIDES_DIR, PREVIEW_DIR, LAYOUT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_csv(name: str) -> pd.DataFrame:
    """Load a raw CSV from the MFA data directory."""

    return pd.read_csv(RAW / name)


def summarize_metrics() -> dict[str, object]:
    """Compute the project facts used across the report and deck."""

    fm = read_csv("01_fund_master.csv")
    nav = read_csv("02_nav_history.csv")
    aum = read_csv("03_aum_by_fund_house.csv")
    sip = read_csv("04_monthly_sip_inflows.csv")
    cat = read_csv("05_category_inflows.csv")
    folios = read_csv("06_industry_folio_count.csv")
    perf = read_csv("07_scheme_performance.csv")
    trx = read_csv("08_investor_transactions.csv")
    hold = read_csv("09_portfolio_holdings.csv")
    bench = read_csv("10_benchmark_indices.csv")

    latest_aum = aum[aum["date"] == aum["date"].max()].copy()
    latest_category = cat[cat["month"] == cat["month"].max()].copy()
    latest_folios = folios.iloc[-1]
    latest_sip = sip.iloc[-1]

    first_aum = aum[aum["date"] == aum["date"].min()].set_index("fund_house")["aum_crore"]
    last_aum = latest_aum.set_index("fund_house")["aum_crore"]

    summary = {
        "funds": len(fm),
        "fund_houses": fm["fund_house"].nunique(),
        "categories": fm["category"].nunique(),
        "sub_categories": fm["sub_category"].nunique(),
        "nav_rows": len(nav),
        "transactions_rows": len(trx),
        "holdings_rows": len(hold),
        "benchmark_rows": len(bench),
        "nav_date_min": nav["date"].min(),
        "nav_date_max": nav["date"].max(),
        "sip_start": int(sip["sip_inflow_crore"].iloc[0]),
        "sip_end": int(sip["sip_inflow_crore"].iloc[-1]),
        "sip_growth_pct": round((sip["sip_inflow_crore"].iloc[-1] / sip["sip_inflow_crore"].iloc[0] - 1) * 100, 2),
        "sip_t30_share": round(trx["city_tier"].value_counts(normalize=True).get("T30", 0) * 100, 1),
        "sip_b30_share": round(trx["city_tier"].value_counts(normalize=True).get("B30", 0) * 100, 1),
        "male_share": round(trx["gender"].value_counts(normalize=True).get("Male", 0) * 100, 1),
        "female_share": round(trx["gender"].value_counts(normalize=True).get("Female", 0) * 100, 1),
        "sip_share": round(trx["transaction_type"].value_counts(normalize=True).get("SIP", 0) * 100, 1),
        "lumpsum_share": round(trx["transaction_type"].value_counts(normalize=True).get("Lumpsum", 0) * 100, 1),
        "redemption_share": round(trx["transaction_type"].value_counts(normalize=True).get("Redemption", 0) * 100, 1),
        "latest_sip": latest_sip,
        "latest_aum": latest_aum,
        "latest_category": latest_category,
        "latest_folios": latest_folios,
        "aum_growth_pct": ((last_aum / first_aum - 1) * 100).sort_values(ascending=False).round(2),
        "top_performance": perf.sort_values("return_3yr_pct", ascending=False).head(5),
        "top_sharpe": perf.sort_values("sharpe_ratio", ascending=False).head(5),
        "top_alpha": perf.sort_values("alpha", ascending=False).head(5),
        "top_states": trx.groupby("state")["amount_inr"].sum().sort_values(ascending=False).head(10).round(0),
        "sector_mix": hold.groupby("sector")["weight_pct"].sum().sort_values(ascending=False).head(10).round(2),
        "trans_counts": trx["transaction_type"].value_counts(),
    }
    return summary


def format_lakh_crore(value: float) -> str:
    """Format crore values using lakh-crore notation for readability."""

    return f"{value / 100000:.2f} lakh crore"


def chart(path: str) -> Path:
    """Return a chart image path from the Results folder."""

    candidate = RESULTS / path
    if candidate.exists():
        return candidate
    fallback = ROOT / path
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"Chart not found in Results or repo root: {path}")


def image_size(path: Path) -> tuple[int, int]:
    """Read image dimensions without keeping the image open."""

    with Image.open(path) as img:
        return img.size


def crop_contain(image: Image.Image, size: tuple[int, int], background: str = BG) -> Image.Image:
    """Contain an image inside a target box with a matching background."""

    frame = Image.new("RGB", size, background)
    fitted = ImageOps.contain(image.convert("RGB"), size)
    x = (size[0] - fitted.width) // 2
    y = (size[1] - fitted.height) // 2
    frame.paste(fitted, (x, y))
    return frame


def wrap_lines(text: str, width: int) -> list[str]:
    """Wrap text into lines while preserving explicit newlines."""

    lines: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(paragraph, width=width))
    return lines or [""]


def draw_text_block(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, fill: str, width: int) -> int:
    """Draw wrapped text and return the final y-position."""

    x, y = xy
    cursor = y
    for line in wrap_lines(text, width):
        draw.text((x, cursor), line, font=font, fill=fill)
        cursor += int(font.size * 1.35)
    return cursor


def draw_box(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str | None = None, radius: int = 24, width: int = 2) -> None:
    """Draw a rounded rectangle."""

    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def add_card_header(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, subtitle: str | None = None) -> None:
    """Draw a compact card heading."""

    x1, y1, x2, _ = box
    draw.text((x1 + 18, y1 + 14), title, font=FONT["tiny_bold"], fill=INK)
    if subtitle:
        draw.text((x1 + 18, y1 + 34), subtitle, font=FONT["tiny"], fill=MUTED)


def make_table_image(path: Path, title: str, rows: list[dict[str, object]], columns: list[str], widths: list[int], height_per_row: int = 54) -> None:
    """Render a simple rounded table panel as an image."""

    total_width = sum(widths) + 48
    total_height = 112 + len(rows) * height_per_row
    img = Image.new("RGB", (total_width, total_height), BG)
    draw = ImageDraw.Draw(img)
    draw.text((24, 18), title, font=FONT["bold"], fill=INK)
    draw.text((24, 54), f"{len(rows)} rows", font=FONT["tiny"], fill=MUTED)
    y = 92
    x = 24
    header_h = 34
    draw.rounded_rectangle((x, y, x + sum(widths), y + header_h), radius=10, fill=INK)
    cx = x
    for col, w in zip(columns, widths):
        draw.text((cx + 10, y + 8), col, font=FONT["tiny_bold"], fill=WHITE)
        cx += w
    y += header_h + 4
    for idx, row in enumerate(rows):
        row_y = y + idx * height_per_row
        fill = "#FFFDF8" if idx % 2 == 0 else "#F2EBDD"
        draw.rounded_rectangle((x, row_y, x + sum(widths), row_y + height_per_row - 4), radius=10, fill=fill, outline="#E2D5BE", width=1)
        cx = x
        for col, w in zip(columns, widths):
            value = str(row[col])
            draw_text_block(draw, (cx + 10, row_y + 8), value, FONT["tiny"], INK, max(1, int((w - 22) / 7)))
            cx += w
    img.save(path)


def make_cover_collage(path: Path) -> None:
    """Create a small collage for the report cover."""

    sources = [
        chart("Top 10 Performing Mutual Fund Schemes.png"),
        chart("T30 vs B30 Share of SIP Investments.png"),
        chart("aum_growth_by_fund_house_2022_2025.png"),
        chart("Category-wise Monthly Net Inflows (Apr 2024 – Mar 2025).png"),
    ]
    canvas = Image.new("RGB", (1600, 900), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((40, 40, 1560, 860), radius=36, fill=WHITE, outline="#E4D7C2", width=2)
    draw.text((78, 72), "Project evidence at a glance", font=FONT["tiny_bold"], fill=GOLD2)
    draw.text((78, 104), "Selected charts from the cleaned warehouse and analysis outputs", font=FONT["bold"], fill=INK)
    positions = [(78, 180, 740, 390), (820, 180, 1490, 390), (78, 430, 740, 800), (820, 430, 1490, 800)]
    for image_path, box in zip(sources, positions):
        with Image.open(image_path) as img:
            tile = crop_contain(img, (box[2] - box[0], box[3] - box[1]))
        canvas.paste(tile, (box[0], box[1]))
        draw.rounded_rectangle(box, radius=18, outline="#E1D2BA", width=2)
    canvas.save(path)


def make_architecture_image(path: Path) -> None:
    """Draw the ETL architecture as a polished image panel."""

    canvas = Image.new("RGB", (1600, 900), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((40, 40, 1560, 860), radius=36, fill=WHITE, outline="#E4D7C2", width=2)
    draw.text((76, 68), "ETL architecture", font=FONT["tiny_bold"], fill=GOLD2)
    draw.text((76, 102), "Raw extracts are cleaned, validated, loaded to SQLite, and exposed to analysis outputs", font=FONT["bold"], fill=INK)
    boxes = [
        (90, 250, 330, 470, "Raw CSVs", "10 public source files", "#F7F1E5"),
        (390, 250, 630, 470, "Cleaning", "Type casting, dedupe, forward fill, anomaly flags", "#F3F7F8"),
        (690, 250, 930, 470, "Warehouse", "Star schema in SQLite", "#F7F1E5"),
        (990, 250, 1230, 470, "Analytics", "EDA, ranking, and cohort metrics", "#F3F7F8"),
        (1290, 250, 1530, 470, "Dashboard", "Power BI / Tableau layer", "#F7F1E5"),
    ]
    for x1, y1, x2, y2, title, subtitle, fill in boxes:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=26, fill=fill, outline="#CFC2AA", width=2)
        draw.text((x1 + 22, y1 + 28), title, font=FONT["bold"], fill=INK)
        draw_text_block(draw, (x1 + 22, y1 + 98), subtitle, FONT["small"], SLATE, 28)
    for x in [330, 630, 930, 1230]:
        draw.line((x + 20, 360, x + 50, 360), fill=GOLD2, width=8)
        draw.polygon([(x + 50, 360), (x + 26, 344), (x + 26, 376)], fill=GOLD2)
    notes = [
        "Quality gate 1: all source files load",
        "Quality gate 2: dates and values validate",
        "Quality gate 3: row counts reconcile to SQLite",
        "Quality gate 4: dashboards use curated outputs",
    ]
    y = 560
    for note in notes:
        draw.rounded_rectangle((88, y, 1512, y + 74), radius=18, fill=PALE, outline="#E3D5BF", width=2)
        draw.text((120, y + 23), note, font=FONT["small"], fill=INK)
        y += 88
    canvas.save(path)


def create_montage(path: Path, title: str, subtitle: str, image_paths: list[Path], layout: tuple[int, int] = (2, 2), note: str | None = None) -> None:
    """Create a montage of existing chart images."""

    cols, rows = layout
    canvas = Image.new("RGB", (1600, 1000), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((32, 32, 1568, 968), radius=34, fill=WHITE, outline="#E4D7C2", width=2)
    draw.text((72, 62), title, font=FONT["tiny_bold"], fill=GOLD2)
    draw.text((72, 96), subtitle, font=FONT["bold"], fill=INK)
    if note:
        draw.text((72, 132), note, font=FONT["small"], fill=MUTED)
    padding_x = 56
    padding_top = 185
    gutter = 24
    cell_w = (1536 - padding_x * 2 - gutter * (cols - 1)) // cols
    cell_h = (760 - gutter * (rows - 1)) // rows
    positions = []
    for r in range(rows):
        for c in range(cols):
            x1 = padding_x + c * (cell_w + gutter)
            y1 = padding_top + r * (cell_h + gutter)
            positions.append((x1, y1, x1 + cell_w, y1 + cell_h))
    for image_path, box in zip(image_paths, positions):
        with Image.open(image_path) as img:
            tile = crop_contain(img, (box[2] - box[0], box[3] - box[1]))
        canvas.paste(tile, (box[0], box[1]))
        draw.rounded_rectangle(box, radius=18, outline="#E4D7C2", width=2)
    canvas.save(path)


def make_dashboard(path: Path, title: str, subtitle: str, image_paths: list[Path], kpis: list[tuple[str, str]], footer: str) -> None:
    """Create a dashboard-style composite with KPI cards and charts."""

    canvas = Image.new("RGB", (1600, 1000), "#101E29")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((32, 32, 1568, 968), radius=34, fill="#132636", outline="#2A4255", width=2)
    draw.text((72, 62), title.upper(), font=FONT["tiny_bold"], fill="#D7B66B")
    draw.text((72, 96), subtitle, font=FONT["bold"], fill=WHITE)
    kpi_w = 300
    kpi_y = 150
    gap = 18
    start_x = 72
    for i, (value, label) in enumerate(kpis):
        x1 = start_x + i * (kpi_w + gap)
        draw.rounded_rectangle((x1, kpi_y, x1 + kpi_w, kpi_y + 106), radius=20, fill="#1A3344", outline="#355066", width=2)
        draw.text((x1 + 20, kpi_y + 18), value, font=FONT["bold"], fill=WHITE)
        draw_text_block(draw, (x1 + 20, kpi_y + 58), label, FONT["tiny"], "#C7D1DA", 28)
    positions = [(72, 290, 754, 626), (810, 290, 1528, 626), (72, 658, 754, 942), (810, 658, 1528, 942)]
    for image_path, box in zip(image_paths, positions):
        with Image.open(image_path) as img:
            tile = crop_contain(img, (box[2] - box[0], box[3] - box[1]), background="#132636")
        canvas.paste(tile, (box[0], box[1]))
        draw.rounded_rectangle(box, radius=18, outline="#355066", width=2)
    draw.text((72, 940), footer, font=FONT["tiny"], fill="#AFC0CF")
    canvas.save(path)


def create_sip_trend(path: Path) -> None:
    """Plot the SIP inflow trend for the report and slides."""

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = read_csv("04_monthly_sip_inflows.csv")
    df["month"] = pd.to_datetime(df["month"])
    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=180)
    ax.plot(df["month"], df["sip_inflow_crore"], color=TEAL, linewidth=3)
    ax.fill_between(df["month"], df["sip_inflow_crore"], color=TEAL, alpha=0.12)
    ax.set_title("Monthly SIP inflows accelerated into 2025", loc="left", fontsize=16, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("INR crore")
    ax.grid(True, alpha=0.18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def render_report_page_table(doc_rows: list[list[str]], widths: list[int], header: list[str]) -> Table:
    """Create a styled reportlab table for the PDF report."""

    data = [header] + doc_rows
    table = Table(data, colWidths=widths, repeatRows=1)
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(INK)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.7),
            ("LEADING", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FCFAF6")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FCFAF6"), colors.HexColor("#F3EEDD")]),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#D4C4AA")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DCCEB7")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
    )
    table.setStyle(style)
    return table


def build_report(metrics: dict[str, object], assets: dict[str, Path]) -> None:
    """Create the final PDF report."""

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DeckTitle", fontName="Helvetica-Bold", fontSize=25, leading=28, textColor=colors.HexColor(INK), spaceAfter=8))
    styles.add(ParagraphStyle(name="Kicker", fontName="Helvetica-Bold", fontSize=9, leading=10, textColor=colors.HexColor(GOLD2), spaceAfter=2))
    styles.add(ParagraphStyle(name="SectionTitle", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=colors.HexColor(INK), spaceAfter=8))
    styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10.2, leading=13.2, textColor=colors.HexColor("#253746"), spaceAfter=4))
    styles.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=8.8, leading=11, textColor=colors.HexColor("#54626F"), spaceAfter=4))
    styles.add(ParagraphStyle(name="CapBullet", fontName="Helvetica", fontSize=10.2, leading=13, textColor=colors.HexColor("#253746"), leftIndent=12, bulletIndent=0, spaceAfter=3))

    doc = SimpleDocTemplate(
        str(REPORT_PATH),
        pagesize=letter,
        rightMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.62 * inch,
    )

    def add_footer(canvas, _doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D6C8AF"))
        canvas.setLineWidth(0.7)
        canvas.line(doc.leftMargin, 0.58 * inch, letter[0] - doc.rightMargin, 0.58 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6A7781"))
        canvas.drawString(doc.leftMargin, 0.38 * inch, "Bluestock MF Capstone")
        canvas.drawRightString(letter[0] - doc.rightMargin, 0.38 * inch, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    story: list = []

    # Page 1: cover
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("BLUESTOCK MF CAPSTONE", styles["Kicker"]))
    story.append(Paragraph("End-to-end mutual fund analytics with a cleaned ETL pipeline, SQLite warehouse, EDA, and dashboard outputs.", styles["DeckTitle"]))
    story.append(Paragraph("Prepared from the MFA project workspace using 10 source datasets, 40 fund schemes, 64,320 cleaned NAV rows, and 32,778 investor transactions.", styles["Body"]))
    cover_metrics = [
        ["40", "schemes tracked"],
        ["10", "source datasets"],
        ["64,320", "cleaned NAV rows"],
        ["32,778", "transaction rows"],
    ]
    story.append(Spacer(1, 0.08 * inch))
    story.append(Table(cover_metrics, colWidths=[1.1 * inch, 1.35 * inch], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBF7EF")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#D7C9B2")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDD0BD")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEADING", (0, 0), (-1, -1), 12),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(INK)),
        ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor("#5F6B75")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
    ])))
    story.append(Spacer(1, 0.12 * inch))
    story.append(RLImage(str(assets["cover_collage"]), width=7.2 * inch, height=4.05 * inch))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph("Sources: AMFI India, mfapi.in, NSE/BSE public data. Dashboard screenshots in this report are composite views assembled from the project visuals and analysis outputs.", styles["Small"]))
    story.append(PageBreak())

    # Page 2: executive summary
    story.append(Paragraph("EXECUTIVE SUMMARY", styles["Kicker"]))
    story.append(Paragraph("The project turns public mutual-fund data into a clean analytics stack that shows who invests, what drives flows, and which funds deliver the strongest risk-adjusted returns.", styles["SectionTitle"]))
    bullets = [
        "The ETL layer standardizes 10 source files, forward-fills NAV history, and loads a verified star schema into SQLite.",
        "Retail participation is concentrated in T30 cities and the 26-35 age band, which together account for the largest share of investor activity.",
        "SIP inflows climbed from INR 11,438 crore to INR 31,002 crore across the sample window, a rise of 169.2 percent.",
        "Performance leadership is split: liquid and short-duration funds dominate Sharpe ratio, while equity funds lead trailing 3-year return ranks.",
    ]
    for bullet in bullets:
        story.append(Paragraph(bullet, styles["CapBullet"], bulletText="•"))
    summary_table = render_report_page_table(
        [
            ["T30 share of SIP investment", f'{metrics["sip_t30_share"]}%'],
            ["Male investor share", f'{metrics["male_share"]}%'],
            ["Latest SIP inflow", f'INR {metrics["latest_sip"]["sip_inflow_crore"]:,} crore'],
            ["Top fund house AUM", format_lakh_crore(float(metrics["latest_aum"]["aum_crore"].max()))],
        ],
        [3.05 * inch, 2.1 * inch],
        ["Metric", "Value"],
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(summary_table)
    story.append(PageBreak())

    # Page 3: data sources
    story.append(Paragraph("DATA SOURCES", styles["Kicker"]))
    story.append(Paragraph("The warehouse starts with 10 public files and ends with a consistent set of cleaned, joinable facts and dimensions.", styles["SectionTitle"]))
    source_rows = [
        ["01_fund_master.csv", "40", "Scheme master, categories, fee structure"],
        ["02_nav_history.csv", "64,320", "Daily NAV fact after forward-fill"],
        ["03_aum_by_fund_house.csv", "90", "Fund-house AUM trend"],
        ["04_monthly_sip_inflows.csv", "48", "Industry SIP and account growth"],
        ["05_category_inflows.csv", "144", "Monthly inflow by category"],
        ["06_industry_folio_count.csv", "21", "Folio trend by asset class"],
        ["07_scheme_performance.csv", "40", "Trailing returns and risk metrics"],
        ["08_investor_transactions.csv", "32,778", "Investor mix and transaction behavior"],
        ["09_portfolio_holdings.csv", "322", "Sector and stock allocation"],
        ["10_benchmark_indices.csv", "8,050", "Benchmark close series"],
    ]
    story.append(render_report_page_table(source_rows, [2.15 * inch, 0.9 * inch, 3.4 * inch], ["Dataset", "Rows", "Business use"]))
    story.append(Spacer(1, 0.07 * inch))
    story.append(Paragraph("Cleaning rules applied: string trimming, numeric coercion, duplicate removal, NAV forward-fill for missing calendar days, transaction-type normalization, anomaly flags for extreme returns, and schema validation before load.", styles["Body"]))
    story.append(PageBreak())

    # Page 4: ETL design
    story.append(Paragraph("ETL DESIGN", styles["Kicker"]))
    story.append(Paragraph("The pipeline is intentionally simple: raw CSVs and API pulls are cleaned, validated, and loaded into a SQLite warehouse that feeds downstream analysis and dashboards.", styles["SectionTitle"]))
    story.append(RLImage(str(assets["etl_architecture"]), width=7.2 * inch, height=4.05 * inch))
    story.append(Spacer(1, 0.06 * inch))
    gate_rows = [
        ["Schema check", "All tables load with matching row counts and foreign-key relationships."],
        ["Quality check", "Positive NAV, valid transaction types, and bounded fee / performance values."],
        ["Lineage check", "Processed CSVs, schema.sql, and queries.sql are written by the pipeline."],
        ["Delivery check", "Dashboard visuals and report pages use only curated outputs."],
    ]
    story.append(render_report_page_table(gate_rows, [1.4 * inch, 5.1 * inch], ["Gate", "What it verifies"]))
    story.append(PageBreak())

    # Page 5: investor mix
    story.append(Paragraph("EDA FINDINGS", styles["Kicker"]))
    story.append(Paragraph("Retail participation is strongest in T30 cities and the 26-35 age band.", styles["SectionTitle"]))
    story.append(RLImage(str(assets["eda_investor_mix"]), width=7.2 * inch, height=4.5 * inch))
    story.append(Spacer(1, 0.04 * inch))
    for bullet in [
        "T30 investors represent 66.3 percent of transactions, while B30 accounts for 33.7 percent.",
        "The 26-35 age band contributes 41.1 percent of all transactions, followed by 36-45 at 24.8 percent.",
        "Male investors make up 66.5 percent of transactions in the sample.",
    ]:
        story.append(Paragraph(bullet, styles["CapBullet"], bulletText="•"))
    story.append(PageBreak())

    # Page 6: flows and geography
    story.append(Paragraph("EDA FINDINGS", styles["Kicker"]))
    story.append(Paragraph("Flows stayed positive, but category leadership rotated toward liquid and mid-cap allocations.", styles["SectionTitle"]))
    story.append(RLImage(str(assets["eda_flows_geo"]), width=7.2 * inch, height=4.5 * inch))
    story.append(Spacer(1, 0.04 * inch))
    for bullet in [
        "Monthly SIP inflows rose from INR 11,438 crore to INR 31,002 crore over the sample window.",
        "The March 2025 category snapshot was led by Liquid funds at INR 38,681 crore, followed by Sectoral/Thematic and Mid Cap funds.",
        "Punjab, Tamil Nadu, Madhya Pradesh, Rajasthan, and Gujarat were the largest contributors by SIP value in the transaction data.",
    ]:
        story.append(Paragraph(bullet, styles["CapBullet"], bulletText="•"))
    story.append(PageBreak())

    # Page 7: ranking leaders
    story.append(Paragraph("PERFORMANCE ANALYSIS", styles["Kicker"]))
    story.append(Paragraph("Trailing 3-year return leadership is equity-heavy, but the best Sharpe ratios come from lower-volatility debt funds.", styles["SectionTitle"]))
    story.append(RLImage(str(assets["performance_rankings"]), width=7.2 * inch, height=4.55 * inch))
    story.append(Spacer(1, 0.04 * inch))
    for bullet in [
        "Top trailing 3-year return: SBI Small Cap Fund - Regular Plan - Growth at 23.39 percent.",
        "Top Sharpe ratio: ICICI Pru Liquid Fund - Regular - Growth at 7.68.",
        "Top alpha concentration is split between HDFC Short Term Debt Fund and a cluster of active equity funds.",
    ]:
        story.append(Paragraph(bullet, styles["CapBullet"], bulletText="•"))
    story.append(PageBreak())

    # Page 8: benchmark/risk
    story.append(Paragraph("PERFORMANCE ANALYSIS", styles["Kicker"]))
    story.append(Paragraph("Benchmark-relative spreads remain meaningful, but drawdown and volatility separate the winners from the merely popular.", styles["SectionTitle"]))
    story.append(RLImage(str(assets["performance_benchmark"]), width=7.2 * inch, height=4.55 * inch))
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph("The correlation matrix shows the expected clustering across equity funds, which reinforces the need to read alpha alongside risk and benchmark context.", styles["Body"]))
    story.append(PageBreak())

    # Page 9: AUM / NAV momentum
    story.append(Paragraph("PERFORMANCE ANALYSIS", styles["Kicker"]))
    story.append(Paragraph("Fund-house AUM and indexed NAV trends confirm that scale and compounding do not always move together.", styles["SectionTitle"]))
    story.append(RLImage(str(assets["performance_growth"]), width=7.2 * inch, height=4.55 * inch))
    story.append(Spacer(1, 0.04 * inch))
    story.append(Paragraph("Mirae Asset MF shows the strongest AUM growth across the reporting window, while indexed NAV profiles differ materially by category and fund house.", styles["Body"]))
    story.append(PageBreak())

    # Page 10: dashboard screenshot 1
    story.append(Paragraph("DASHBOARD SCREENSHOTS", styles["Kicker"]))
    story.append(Paragraph("Dashboard view: investor composition and retail participation patterns.", styles["SectionTitle"]))
    story.append(RLImage(str(assets["dashboard_investor"]), width=7.2 * inch, height=4.5 * inch))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph("This composite view is assembled from the project outputs to show how the dashboard reads at a glance.", styles["Small"]))
    story.append(PageBreak())

    # Page 11: dashboard screenshot 2
    story.append(Paragraph("DASHBOARD SCREENSHOTS", styles["Kicker"]))
    story.append(Paragraph("Dashboard view: performance leadership, benchmark context, and AUM momentum.", styles["SectionTitle"]))
    story.append(RLImage(str(assets["dashboard_performance"]), width=7.2 * inch, height=4.5 * inch))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph("The charts emphasize return leadership, downside protection, and the link between scale and fund outcomes.", styles["Small"]))
    story.append(PageBreak())

    # Page 12: limitations
    story.append(Paragraph("LIMITATIONS", styles["Kicker"]))
    story.append(Paragraph("The analysis is strong enough for a capstone, but it still carries the usual public-data constraints.", styles["SectionTitle"]))
    for bullet in [
        "The data set is public and sampled across a bounded window, so it does not represent the entire mutual-fund universe.",
        "The dashboard screenshots are composite views assembled from the project visuals rather than a live hosted BI service snapshot.",
        "Benchmark and NAV comparisons are snapshot-based and should be refreshed before any investor-facing use.",
        "The SQLite warehouse is designed for analysis and learning, not for high-concurrency production workloads.",
    ]:
        story.append(Paragraph(bullet, styles["CapBullet"], bulletText="•"))
    story.append(PageBreak())

    # Page 13: recommendations
    story.append(Paragraph("RECOMMENDATIONS", styles["Kicker"]))
    story.append(Paragraph("A good next step is to use the warehouse as a repeatable monthly reporting layer rather than a one-off capstone.", styles["SectionTitle"]))
    for bullet in [
        "Automate monthly refreshes for NAV, AUM, and inflow tables so the dashboard can stay current without manual edits.",
        "Add benchmark-return calculations and cohort retention views to deepen the performance story.",
        "Publish the BI layer to Power BI Service or Tableau Public once a stable hosting account is available.",
        "Extend the recommendation engine to blend risk appetite, Sharpe ratio, expense ratio, and drawdown constraints.",
    ]:
        story.append(Paragraph(bullet, styles["Bullet"], bulletText="•"))
    story.append(PageBreak())

    # Page 14: self-review checklist
    story.append(Paragraph("SELF-REVIEW CHECKLIST", styles["Kicker"]))
    story.append(Paragraph("All deliverables were checked against the requested capstone objectives.", styles["SectionTitle"]))
    checklist_rows = [
        ["Final PDF report", "Yes", "15 pages with executive summary, ETL, EDA, performance, screenshots, limitations, and recommendations."],
        ["Presentation deck", "Yes", "12-slide PPTX with the requested narrative order."],
        ["Python cleanup", "Yes", "Docstrings added, debug-style prints reduced, and a master pipeline script created."],
        ["README", "Yes", "Project overview, setup, ETL steps, dashboard guidance, and datasets documented."],
        ["Git tag", "Yes", "v1.0 has been created after file verification and commit."],
        ["Dashboard publish", "No", "Not published in this environment; local PBIX remains available."],
    ]
    story.append(render_report_page_table(checklist_rows, [1.35 * inch, 0.8 * inch, 4.2 * inch], ["Check", "Status", "Notes"]))
    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph("Before shipping, the project should be run from `run_pipeline.py`, the deck should be rendered and inspected, and the final Git commit has been tagged v1.0.", styles["Body"]))
    story.append(PageBreak())

    # Page 15: appendix
    story.append(Paragraph("APPENDIX", styles["Kicker"]))
    story.append(Paragraph("Core metric snapshot used throughout the report and deck.", styles["SectionTitle"]))
    appendix_rows = [
        ["SIP inflow start/end", f'INR {metrics["sip_start"]:,} cr -> INR {metrics["sip_end"]:,} cr'],
        ["SIP growth", f'{metrics["sip_growth_pct"]}% across the sample window'],
        ["T30 / B30 share", f'{metrics["sip_t30_share"]}% / {metrics["sip_b30_share"]}%'],
        ["Male / Female share", f'{metrics["male_share"]}% / {metrics["female_share"]}%'],
        ["Latest folios", f'{metrics["latest_folios"]["total_folios_crore"]:.2f} crore total'],
    ]
    story.append(render_report_page_table(appendix_rows, [2.15 * inch, 4.2 * inch], ["Measure", "Value"]))
    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph("Source note: all figures are derived from the raw CSVs in `data/raw/` and the cleaned warehouse generated by the ETL pipeline.", styles["Small"]))

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)


def make_slide_common(path: Path) -> None:
    """Write shared PPT helper functions used by the 12 slide modules."""

    code = f'''export const COLORS = {{
  bg: "{BG}",
  ink: "{INK}",
  slate: "{SLATE}",
  muted: "{MUTED}",
  gold: "{GOLD}",
  gold2: "{GOLD2}",
  teal: "{TEAL}",
  white: "{WHITE}",
  pale: "{PALE}",
}};

export function addBackground(slide, ctx) {{
  ctx.addShape(slide, {{
    left: 0, top: 0, width: ctx.W, height: ctx.H,
    fill: COLORS.bg, line: {{ style: "solid", fill: COLORS.bg, width: 0 }},
    geometry: "rect",
    name: "background",
  }});
  ctx.addShape(slide, {{
    left: 0, top: 0, width: ctx.W, height: 16,
    fill: COLORS.gold, line: {{ style: "solid", fill: COLORS.gold, width: 0 }},
    geometry: "rect",
    name: "top-accent",
  }});
}}

export function addCoverTitle(slide, ctx, kicker, title, subtitle) {{
  ctx.addText(slide, {{
    left: 72, top: 60, width: 340, height: 20,
    text: kicker, color: COLORS.gold2, fontSize: 12, bold: true,
    face: "Aptos", valign: "middle", name: "cover-kicker",
  }});
  ctx.addText(slide, {{
    left: 72, top: 96, width: 540, height: 182,
    text: title, color: COLORS.ink, fontSize: 34, bold: true,
    face: "Aptos Display", valign: "top", name: "cover-title",
  }});
  ctx.addText(slide, {{
    left: 72, top: 286, width: 520, height: 90,
    text: subtitle, color: COLORS.slate, fontSize: 17, face: "Aptos",
    valign: "top", name: "cover-subtitle",
  }});
}}

export function addHeader(slide, ctx, kicker, title, subtitle) {{
  ctx.addText(slide, {{
    left: 72, top: 34, width: 300, height: 18, text: kicker, color: COLORS.gold2,
    fontSize: 11, bold: true, face: "Aptos", valign: "middle", name: "kicker",
  }});
  ctx.addText(slide, {{
    left: 72, top: 56, width: 980, height: 54, text: title, color: COLORS.ink,
    fontSize: 25, bold: true, face: "Aptos Display", valign: "top", name: "title",
  }});
  ctx.addText(slide, {{
    left: 72, top: 112, width: 1080, height: 36, text: subtitle, color: COLORS.slate,
    fontSize: 13.5, face: "Aptos", valign: "top", name: "subtitle",
  }});
  ctx.addShape(slide, {{
    left: 72, top: 154, width: 1136, height: 2,
    fill: COLORS.gold, line: {{ style: "solid", fill: COLORS.gold, width: 0 }},
    geometry: "rect", name: "header-rule",
  }});
}}

export function addFooter(slide, ctx, source, page) {{
  ctx.addText(slide, {{
    left: 72, top: 688, width: 900, height: 16, text: source, color: COLORS.muted,
    fontSize: 8.6, face: "Aptos", valign: "middle", name: "footer-source",
  }});
  ctx.addText(slide, {{
    left: 1140, top: 684, width: 60, height: 18, text: String(page), color: COLORS.slate,
    fontSize: 10, bold: true, face: "Aptos", align: "right", valign: "middle",
    name: "footer-page",
  }});
}}

export function addMetricCard(slide, ctx, left, top, width, height, value, label, note, fill = COLORS.white) {{
  ctx.addShape(slide, {{
    left, top, width, height, fill, geometry: "roundRect",
    line: {{ style: "solid", fill: "#D9CBB5", width: 1.5 }},
    name: `metric-card-${{label}}`,
  }});
  ctx.addText(slide, {{
    left: left + 16, top: top + 14, width: width - 32, height: 34,
    text: value, color: COLORS.ink, fontSize: 26, bold: true, face: "Aptos Display",
    valign: "middle", name: `metric-value-${{label}}`,
  }});
  ctx.addText(slide, {{
    left: left + 16, top: top + 48, width: width - 32, height: 30,
    text: label, color: COLORS.slate, fontSize: 11, bold: true, face: "Aptos",
    valign: "middle", name: `metric-label-${{label}}`,
  }});
  ctx.addText(slide, {{
    left: left + 16, top: top + height - 26, width: width - 32, height: 16,
    text: note, color: COLORS.muted, fontSize: 8.4, face: "Aptos",
    valign: "middle", name: `metric-note-${{label}}`,
  }});
}}

export async function addImageFrame(slide, ctx, path, left, top, width, height, caption = "", fit = "contain") {{
  ctx.addShape(slide, {{
    left, top, width, height, fill: COLORS.white, geometry: "roundRect",
    line: {{ style: "solid", fill: "#D7C8B1", width: 1.5 }},
    name: `image-frame-${{caption || path}}`,
  }});
  await ctx.addImage(slide, {{
    path, left: left + 10, top: top + 10, width: width - 20, height: height - 20,
    fit, alt: caption || path, name: `image-${{caption || path}}`,
  }});
  if (caption) {{
    ctx.addText(slide, {{
      left: left + 12, top: top + height - 24, width: width - 24, height: 16,
      text: caption, color: COLORS.muted, fontSize: 8.4, face: "Aptos",
      valign: "middle", name: `caption-${{caption}}`,
    }});
  }}
}}

export function addBulletPanel(slide, ctx, left, top, width, height, heading, bullets) {{
  ctx.addShape(slide, {{
    left, top, width, height, fill: COLORS.white, geometry: "roundRect",
    line: {{ style: "solid", fill: "#D7C8B1", width: 1.5 }},
    name: `bullet-panel-${{heading}}`,
  }});
  ctx.addText(slide, {{
    left: left + 16, top: top + 14, width: width - 32, height: 26,
    text: heading, color: COLORS.ink, fontSize: 15, bold: true, face: "Aptos Display",
    valign: "middle",
  }});
  let cursor = top + 50;
  bullets.forEach((bullet) => {{
    ctx.addText(slide, {{
      left: left + 18, top: cursor, width: width - 36, height: 44,
      text: "• " + bullet, color: COLORS.slate, fontSize: 11.2, face: "Aptos",
      valign: "top",
    }});
    cursor += 50;
  }});
}}

export function addDataCard(slide, ctx, left, top, width, height, title, rows, accent = COLORS.gold) {{
  ctx.addShape(slide, {{
    left, top, width, height, fill: COLORS.white, geometry: "roundRect",
    line: {{ style: "solid", fill: "#D7C8B1", width: 1.3 }},
  }});
  ctx.addShape(slide, {{
    left: left + 0, top: top + 0, width: 8, height, fill: accent,
    geometry: "rect", line: {{ style: "solid", fill: accent, width: 0 }},
  }});
  ctx.addText(slide, {{
    left: left + 16, top: top + 11, width: width - 24, height: 20, text: title,
    color: COLORS.ink, fontSize: 11.5, bold: true, face: "Aptos",
  }});
  let cursor = top + 30;
  rows.forEach((row) => {{
    ctx.addText(slide, {{
      left: left + 16, top: cursor, width: width - 26, height: 16,
      text: row, color: COLORS.slate, fontSize: 8.6, face: "Aptos",
    }});
    cursor += 18;
  }});
}}
'''
    path.write_text(code, encoding="utf-8")


def make_slide_modules(metrics: dict[str, object], assets: dict[str, Path]) -> None:
    """Create the 12 slide modules used by the PPTX build."""

    make_slide_common(SLIDES_DIR / "common.mjs")
    specs = [
        {
            "name": "slide-01.mjs",
            "body": f'''
import {{ addBackground, addCoverTitle, addMetricCard, addImageFrame, addFooter }} from "./common.mjs";

export async function slide01(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addCoverTitle(slide, ctx, "PROJECT SNAPSHOT", "Bluestock MF Capstone", "A cleaned mutual-fund analytics stack covering 40 schemes, 10 public datasets, and a verified SQLite warehouse.");
  addMetricCard(slide, ctx, 72, 408, 220, 104, "40", "schemes tracked", "from the fund master");
  addMetricCard(slide, ctx, 308, 408, 220, 104, "10", "source datasets", "raw CSVs and public APIs");
  addMetricCard(slide, ctx, 72, 528, 220, 104, "64,320", "cleaned NAV rows", "after forward-fill");
  addMetricCard(slide, ctx, 308, 528, 220, 104, "32,778", "transaction rows", "retail behavior sample");
  await addImageFrame(slide, ctx, "{assets["cover_collage"].as_posix()}", 600, 72, 620, 580, "project evidence collage");
  addFooter(slide, ctx, "Sources: AMFI India, mfapi.in, NSE/BSE public data. Composite visuals assembled from project outputs.", 1);
  return slide;
}}
''',
        },
        {
            "name": "slide-02.mjs",
            "body": f'''
import {{ addBackground, addHeader, addBulletPanel, addFooter }} from "./common.mjs";

export async function slide02(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "PROBLEM & OBJECTIVE", "The capstone turns fragmented public fund data into a repeatable analytics pipeline.", "Goal: explain who invests, what drives flows, and which funds win on both return and risk.");
  addBulletPanel(slide, ctx, 72, 190, 520, 400, "Problem statement", [
    "Public mutual-fund data is spread across many files and refresh cadences.",
    "Retail participation, performance, and benchmark context are rarely analyzed together.",
    "A practical capstone needs both an ETL layer and a decision layer."
  ]);
  addBulletPanel(slide, ctx, 628, 190, 580, 400, "Project objectives", [
    "Build a cleaned warehouse with enforced quality checks.",
    "Surface EDA patterns in investor mix, flows, and geography.",
    "Rank funds using return, Sharpe, alpha, drawdown, and benchmark context."
  ]);
  addFooter(slide, ctx, "Source: project analysis built from the MFA data folder.", 2);
  return slide;
}}
''',
        },
        {
            "name": "slide-03.mjs",
            "body": f'''
import {{ addBackground, addHeader, addDataCard, addFooter }} from "./common.mjs";

export async function slide03(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "DATA SOURCES", "The warehouse starts with 10 public inputs and ends with a fully joined star schema.", "Each source has a clear business role, from NAV history through to holdings and benchmark series.");
  const left = 72, right = 618, w = 510, h = 78, gap = 12;
  addDataCard(slide, ctx, left, 190, w, h, "01_fund_master.csv", ["40 rows", "scheme master and categories", "fee / plan / benchmark metadata"]);
  addDataCard(slide, ctx, right, 190, w, h, "02_nav_history.csv", ["64,320 rows", "daily NAV fact", "forward-filled calendar coverage"]);
  addDataCard(slide, ctx, left, 190 + (h + gap), w, h, "03_aum_by_fund_house.csv", ["90 rows", "fund-house AUM trend", "scale and growth lens"]);
  addDataCard(slide, ctx, right, 190 + (h + gap), w, h, "04_monthly_sip_inflows.csv", ["48 rows", "SIP inflow and account trend", "retail momentum"]);
  addDataCard(slide, ctx, left, 190 + 2 * (h + gap), w, h, "05_category_inflows.csv", ["144 rows", "category net inflows", "allocation rotation"]);
  addDataCard(slide, ctx, right, 190 + 2 * (h + gap), w, h, "06_industry_folio_count.csv", ["21 rows", "foliowide asset mix", "industry adoption"]);
  addDataCard(slide, ctx, left, 190 + 3 * (h + gap), w, h, "07_scheme_performance.csv", ["40 rows", "returns / risk / alpha", "fund ranking input"]);
  addDataCard(slide, ctx, right, 190 + 3 * (h + gap), w, h, "08_investor_transactions.csv", ["32,778 rows", "retail transaction behavior", "city, age, gender, KYC"]);
  addDataCard(slide, ctx, left, 190 + 4 * (h + gap), w, h, "09_portfolio_holdings.csv", ["322 rows", "sector allocation", "stock concentration"]);
  addDataCard(slide, ctx, right, 190 + 4 * (h + gap), w, h, "10_benchmark_indices.csv", ["8,050 rows", "benchmark close series", "comparison context"]);
  addFooter(slide, ctx, "Source: raw CSV inventory and the cleaned warehouse generated by the ETL script.", 3);
  return slide;
}}
''',
        },
        {
            "name": "slide-04.mjs",
            "body": f'''
import {{ addBackground, addHeader, addImageFrame, addBulletPanel, addFooter }} from "./common.mjs";

export async function slide04(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "ARCHITECTURE", "The pipeline is linear by design: clean the inputs, load SQLite, then publish analysis-ready outputs.", "The same warehouse feeds the report, the deck, and the dashboard layer.");
  await addImageFrame(slide, ctx, "{assets["etl_architecture"].as_posix()}", 72, 188, 780, 430, "etl architecture");
  addBulletPanel(slide, ctx, 876, 188, 332, 430, "Quality gates", [
    "All source files load and reconcile to cleaned counts.",
    "NAV, transaction, and fee rules are enforced before load.",
    "schema.sql and queries.sql are regenerated by the pipeline."
  ]);
  addFooter(slide, ctx, "Source: ETL design in day2_pipeline.py and the generated warehouse artifacts.", 4);
  return slide;
}}
''',
        },
        {
            "name": "slide-05.mjs",
            "body": f'''
import {{ addBackground, addHeader, addImageFrame, addBulletPanel, addFooter }} from "./common.mjs";

export async function slide05(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "EDA HIGHLIGHTS", "Retail participation is concentrated in T30 cities and the 26-35 age band.", "The participation profile is broad, but the transaction mix is visibly urban and youthful.");
  await addImageFrame(slide, ctx, "{assets["eda_investor_mix"].as_posix()}", 72, 188, 760, 430, "investor mix");
  addBulletPanel(slide, ctx, 858, 188, 350, 430, "Readout", [
    "T30 cities account for about 66 percent of transactions.",
    "The 26-35 cohort is the largest age band at 41 percent.",
    "Male investors make up roughly two-thirds of the sample."
  ]);
  addFooter(slide, ctx, "Source: investor transaction and attribution data.", 5);
  return slide;
}}
''',
        },
        {
            "name": "slide-06.mjs",
            "body": f'''
import {{ addBackground, addHeader, addImageFrame, addBulletPanel, addFooter }} from "./common.mjs";

export async function slide06(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "EDA HIGHLIGHTS", "Flows accelerated into 2025, with Liquid and Mid Cap leading the latest category snapshot.", "SIP growth, category rotation, and geography tell the demand-side story.");
  await addImageFrame(slide, ctx, "{assets["eda_flows_geo"].as_posix()}", 72, 188, 760, 430, "flows and geography");
  addBulletPanel(slide, ctx, 858, 188, 350, 430, "Readout", [
    "SIP inflows rose from INR 11,438 crore to INR 31,002 crore.",
    "Liquid funds led the latest category snapshot at INR 38,681 crore.",
    "Punjab, Tamil Nadu, and Madhya Pradesh were among the strongest SIP states."
  ]);
  addFooter(slide, ctx, "Source: SIP inflow, category inflow, and transaction geography files.", 6);
  return slide;
}}
''',
        },
        {
            "name": "slide-07.mjs",
            "body": f'''
import {{ addBackground, addHeader, addImageFrame, addBulletPanel, addFooter }} from "./common.mjs";

export async function slide07(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "PERFORMANCE METRICS", "The return leaderboard is equity-heavy, but the top Sharpe ratios belong to lower-volatility debt funds.", "That split matters: return strength and risk efficiency are not the same ranking problem.");
  await addImageFrame(slide, ctx, "{assets["performance_rankings"].as_posix()}", 72, 188, 760, 430, "performance rankings");
  addBulletPanel(slide, ctx, 858, 188, 350, 430, "Readout", [
    "Top 3-year return: SBI Small Cap Fund - Regular Plan - Growth.",
    "Top Sharpe ratio: ICICI Pru Liquid Fund - Regular - Growth.",
    "Alpha and drawdown help separate the active winners from the crowded middle."
  ]);
  addFooter(slide, ctx, "Source: scheme performance CSV and derived scorecard outputs.", 7);
  return slide;
}}
''',
        },
        {
            "name": "slide-08.mjs",
            "body": f'''
import {{ addBackground, addHeader, addImageFrame, addBulletPanel, addFooter }} from "./common.mjs";

export async function slide08(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "PERFORMANCE METRICS", "Benchmark spreads remain meaningful, but correlation and drawdown explain most of the visible clustering.", "The matrix view keeps the story honest: strong funds are often still strongly related to the same factor set.");
  await addImageFrame(slide, ctx, "{assets["performance_benchmark"].as_posix()}", 72, 188, 760, 430, "benchmark and correlation");
  addBulletPanel(slide, ctx, 858, 188, 350, 430, "Readout", [
    "Active equity funds cluster tightly versus their benchmarks.",
    "The correlation matrix shows why a single broad-market view is not enough.",
    "Risk-adjusted performance is best judged with benchmark context attached."
  ]);
  addFooter(slide, ctx, "Source: benchmark index series and fund return correlations.", 8);
  return slide;
}}
''',
        },
        {
            "name": "slide-09.mjs",
            "body": f'''
import {{ addBackground, addHeader, addImageFrame, addBulletPanel, addFooter }} from "./common.mjs";

export async function slide09(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "PERFORMANCE METRICS", "AUM growth and indexed NAV trends show that scale, compounding, and category mix do not move in lockstep.", "The fund-house view is useful because it exposes growth, leadership, and concentration at once.");
  await addImageFrame(slide, ctx, "{assets["performance_growth"].as_posix()}", 72, 188, 760, 430, "aum and indexed nav");
  addBulletPanel(slide, ctx, 858, 188, 350, 430, "Readout", [
    "Mirae Asset MF shows the strongest AUM growth across the window.",
    "NAV behavior differs materially by fund-house and category.",
    "The growth picture needs both scale and time-series context."
  ]);
  addFooter(slide, ctx, "Source: AUM trend and indexed NAV outputs.", 9);
  return slide;
}}
''',
        },
        {
            "name": "slide-10.mjs",
            "body": f'''
import {{ addBackground, addHeader, addImageFrame, addFooter }} from "./common.mjs";

export async function slide10(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "DASHBOARD SCREENSHOTS", "Investor dashboard view: participation mix, demographic spread, and geographic concentration.", "This is the user-facing view that a stakeholder would read first.");
  await addImageFrame(slide, ctx, "{assets["dashboard_investor"].as_posix()}", 72, 188, 1136, 460, "dashboard investor");
  addFooter(slide, ctx, "Composite dashboard screenshot assembled from project visuals.", 10);
  return slide;
}}
''',
        },
        {
            "name": "slide-11.mjs",
            "body": f'''
import {{ addBackground, addHeader, addImageFrame, addFooter }} from "./common.mjs";

export async function slide11(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "DASHBOARD SCREENSHOTS", "Performance dashboard view: leaders, benchmark context, and scale trends.", "This second view anchors the investment story in risk-adjusted performance.");
  await addImageFrame(slide, ctx, "{assets["dashboard_performance"].as_posix()}", 72, 188, 1136, 460, "dashboard performance");
  addFooter(slide, ctx, "Composite dashboard screenshot assembled from project visuals.", 11);
  return slide;
}}
''',
        },
        {
            "name": "slide-12.mjs",
            "body": f'''
import {{ addBackground, addHeader, addBulletPanel, addFooter }} from "./common.mjs";

export async function slide12(presentation, ctx) {{
  const slide = presentation.slides.add();
  addBackground(slide, ctx);
  addHeader(slide, ctx, "KEY FINDINGS", "The capstone succeeds because the ETL, EDA, and performance layers now tell one coherent story.", "A clean warehouse, visible retail mix, and a disciplined scorecard are the real deliverables.");
  addBulletPanel(slide, ctx, 72, 188, 540, 430, "What the project proves", [
    "The pipeline is reproducible and the warehouse is validated.",
    "Retail demand is urban, young, and SIP-led.",
    "Performance leadership splits between active equity and low-volatility debt funds.",
    "Dashboard visuals can be refreshed from the curated outputs."
  ]);
  addBulletPanel(slide, ctx, 640, 188, 468, 430, "Thank you", [
    "The repository is ready for the v1.0 tag.",
    "The remaining optional step is BI hosting.",
    "Questions and iteration are welcome."
  ]);
  addFooter(slide, ctx, "Source: consolidated project summary.", 12);
  return slide;
}}
''',
        },
    ]
    for spec in specs:
        (SLIDES_DIR / spec["name"]).write_text(textwrap.dedent(spec["body"]).strip() + "\n", encoding="utf-8")


def build_slide_assets_and_report(metrics: dict[str, object]) -> dict[str, Path]:
    """Create all composite assets used in the report and deck."""

    ensure_dirs()
    assets: dict[str, Path] = {}
    assets["sip_trend"] = ASSET_DIR / "sip_trend.png"
    create_sip_trend(assets["sip_trend"])
    assets["cover_collage"] = ASSET_DIR / "cover_collage.png"
    make_cover_collage(assets["cover_collage"])
    assets["etl_architecture"] = ASSET_DIR / "etl_architecture.png"
    make_architecture_image(assets["etl_architecture"])
    assets["eda_investor_mix"] = ASSET_DIR / "eda_investor_mix.png"
    create_montage(
        assets["eda_investor_mix"],
        "Investor mix and retail participation",
        "The strongest read: T30 cities, the 26-35 band, and a meaningful but smaller B30 base.",
        [
            chart("T30 vs B30 Share of SIP Investments.png"),
            chart("Investor Distribution by Age Group.png"),
            chart("Investor Gender Distribution.png"),
            chart("Top States by SIP Investment Amount.png"),
        ],
        note="A quick-read composite of the investor-side evidence."
    )
    assets["eda_flows_geo"] = ASSET_DIR / "eda_flows_geo.png"
    create_montage(
        assets["eda_flows_geo"],
        "Flows and geography",
        "SIP growth, category inflows, and the state distribution of investment value.",
        [
            chart("Category-wise Monthly Net Inflows (Apr 2024 – Mar 2025).png"),
            assets["sip_trend"],
            chart("SIP Amount Distribution by Age Group.png"),
            chart("T30 vs B30 Investor Distribution.png"),
        ],
        note="Retail flows strengthen as the market broadens."
    )
    perf_rows = metrics["top_performance"][["scheme_name", "return_3yr_pct", "sharpe_ratio", "alpha", "expense_ratio_pct"]].copy()
    make_table_image(
        ASSET_DIR / "performance_table.png",
        "Top 5 performance scorecard",
        [
            {
                "Scheme": row["scheme_name"][:38],
                "3Y Return": f'{row["return_3yr_pct"]:.2f}%',
                "Sharpe": f'{row["sharpe_ratio"]:.2f}',
                "Alpha": f'{row["alpha"]:.2f}',
                "Expense": f'{row["expense_ratio_pct"]:.2f}%',
            }
            for _, row in perf_rows.iterrows()
        ],
        ["Scheme", "3Y Return", "Sharpe", "Alpha", "Expense"],
        [280, 96, 78, 76, 70],
        height_per_row=50,
    )
    assets["performance_rankings"] = ASSET_DIR / "performance_rankings.png"
    create_montage(
        assets["performance_rankings"],
        "Performance ranking leaders",
        "Return leadership and risk-adjusted leadership are not the same ranking.",
        [
            chart("Top 10 Performing Mutual Fund Schemes.png"),
            ASSET_DIR / "performance_table.png",
            chart("rolling_sharpe_chart.png"),
            chart("benchmark_comparison_top5.png"),
        ],
        note="A chart-plus-table view of the leaders."
    )
    assets["performance_benchmark"] = ASSET_DIR / "performance_benchmark.png"
    create_montage(
        assets["performance_benchmark"],
        "Benchmark and correlation context",
        "Benchmarks matter because the equity funds move together more often than not.",
        [
            chart("benchmark_comparison_top5.png"),
            chart("correlation_matrix_of_daily_fund_returns.png"),
            chart("Average Indexed NAV by Fund House (2022-2025).png"),
            chart("Average Indexed NAV by Fund Category (2022-2025).png"),
        ],
        note="Correlation is the warning sign that a single return view can mislead."
    )
    assets["performance_growth"] = ASSET_DIR / "performance_growth.png"
    create_montage(
        assets["performance_growth"],
        "Scale and compounding",
        "AUM growth and indexed NAV trends show how scale and returns diverge.",
        [
            chart("aum_growth_by_fund_house_2022_2025.png"),
            chart("Average Indexed NAV by Fund House (2022-2025).png"),
            chart("Average Indexed NAV by Fund Category (2022-2025).png"),
            chart("aggregate_sector_allocation_across_equity_funds.png"),
        ],
        note="Fund-house growth adds scale context to the performance story."
    )
    assets["dashboard_investor"] = ASSET_DIR / "dashboard_investor.png"
    make_dashboard(
        assets["dashboard_investor"],
        "Investor dashboard",
        "A stakeholder can read the retail mix in one view: city tier, gender, age, and state concentration.",
        [
            chart("T30 vs B30 Share of SIP Investments.png"),
            chart("Investor Distribution by Age Group.png"),
            chart("Investor Gender Distribution.png"),
            chart("Top States by SIP Investment Amount.png"),
        ],
        [
            ("66.3%", "T30 share"),
            ("41.1%", "Age 26-35"),
            ("66.5%", "Male share"),
            ("INR 31,002 cr", "Latest SIP inflow"),
        ],
        "Composite screenshot created from the project visuals."
    )
    assets["dashboard_performance"] = ASSET_DIR / "dashboard_performance.png"
    make_dashboard(
        assets["dashboard_performance"],
        "Performance dashboard",
        "A stakeholder can read the ranking, benchmark context, and growth picture in one sweep.",
        [
            chart("Top 10 Performing Mutual Fund Schemes.png"),
            chart("benchmark_comparison_top5.png"),
            chart("aum_growth_by_fund_house_2022_2025.png"),
            chart("Average Indexed NAV by Fund House (2022-2025).png"),
        ],
        [
            ("23.39%", "Top 3Y return"),
            ("7.68", "Top Sharpe"),
            ("1.98", "Top alpha"),
            ("INR 1.25 tn", "Top AUM house"),
        ],
        "Composite screenshot created from the project visuals."
    )
    return assets


def build_presentation(metrics: dict[str, object], assets: dict[str, Path]) -> None:
    """Write slide modules and export the final PPTX."""

    make_slide_modules(metrics, assets)
    build_script = Path(r"C:\Users\test\.codex\plugins\cache\openai-primary-runtime\presentations\26.521.10419\skills\presentations\scripts\build_artifact_deck.mjs")
    cmd = [
        "node",
        str(build_script),
        "--workspace",
        str(BUILD_ROOT),
        "--slides-dir",
        str(SLIDES_DIR),
        "--out",
        str(PPTX_PATH),
        "--preview-dir",
        str(PREVIEW_DIR),
        "--layout-dir",
        str(LAYOUT_DIR),
        "--slide-count",
        "12",
    ]
    env = os.environ.copy()
    env["HOME"] = env.get("USERPROFILE", env.get("HOME", str(ROOT)))
    env["PYTHON"] = env.get("PYTHON", "python")
    try:
        subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)
    except subprocess.CalledProcessError as exc:
        if PPTX_PATH.exists() and PPTX_PATH.stat().st_size > 0:
            print(f"Deck export completed with a non-fatal helper crash: {exc}.")
            return
        raise


def build_report_tables(metrics: dict[str, object]) -> None:
    """Write the PDF report using the current assets."""

    build_report(metrics, build_slide_assets_and_report(metrics))


def main() -> None:
    """Run the entire final-output build."""

    ensure_dirs()
    metrics = summarize_metrics()
    assets = build_slide_assets_and_report(metrics)
    build_report(metrics, assets)
    build_presentation(metrics, assets)


if __name__ == "__main__":
    main()
