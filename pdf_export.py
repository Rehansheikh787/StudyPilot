import json
import os
import sys
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, 
    Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# Global Color Palette Definitions
RED_BG = colors.HexColor('#FFD3D3')
RED_ACCENT = colors.HexColor('#C83C3C')
YEL_BG = colors.HexColor('#FFF2CC')
YEL_ACCENT = colors.HexColor('#D6A300')
GRN_BG = colors.HexColor('#E2EFDA')
GRN_ACCENT = colors.HexColor('#375623')

HEADER_BG = colors.HexColor('#1F4E78')
HEADER_TEXT = colors.white
ALT_ROW = colors.HexColor('#F2F2F2')
WHITE = colors.white
BORDER = colors.HexColor('#D9D9D9')
TEXT_DARK = colors.HexColor('#262626')
TEXT_MED = colors.HexColor('#595959')
TEXT_LIGHT = colors.HexColor('#A6A6A6')

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm
TABLE_W = PAGE_W - 2 * MARGIN

def make_styles():
    styles = getSampleStyleSheet()
    
    # Custom implementations or replacements of default layout text styles using 'sp_' prefix to avoid conflicts
    styles.add(ParagraphStyle(
        name='sp_title',
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=HEADER_BG,
        alignment=TA_LEFT,
        spaceAfter=12
    ))
    
    styles.add(ParagraphStyle(
        name='sp_subtitle',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=TEXT_MED,
        alignment=TA_LEFT,
        spaceAfter=6
    ))
    
    styles.add(ParagraphStyle(
        name='sp_date_cell',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK,
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name='sp_subject_cell',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=HEADER_BG,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        name='sp_topic_cell',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        name='sp_min_cell',
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=TEXT_MED,
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name='sp_notes_cell',
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=TEXT_MED,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        name='sp_col_header',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=HEADER_TEXT,
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name='sp_legend_label',
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        name='sp_legend_sub',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=TEXT_MED,
        alignment=TA_LEFT
    ))

    return styles

def get_urgency(exam_date_str):
    try:
        exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
        days_left = (exam_date - date.today()).days
    except (ValueError, TypeError):
        days_left = 999  # Fallback for empty or invalid dates
        
    if days_left <= 7:
        return "red", RED_BG, RED_ACCENT
    elif days_left <= 14:
        return "yellow", YEL_BG, YEL_ACCENT
    else:
        return "green", GRN_BG, GRN_ACCENT

def load_timetable(json_path="timetable.json"):
    # Resolve path relative to script directory if relative
    if not os.path.isabs(json_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, json_path)
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    rows = []
    timetable_data = data.get("timetable", [])
    
    for day in timetable_data:
        for slot in day.get("slots", []):
            chapters = slot.get("chapters_to_cover", [])
            topic_str = ", ".join(chapters) if isinstance(chapters, list) else str(chapters)
            
            rows.append({
                "date": day.get("date", ""),
                "subject": slot.get("subject", ""),
                "topic": topic_str,
                "minutes": slot.get("duration_minutes", 0),
                "notes": slot.get("notes", ""),
                "exam_date": slot.get("exam_date", "2026-12-31")
            })
            
    summary = data.get("weekly_summary", "")
    return rows, summary

def build_legend(styles):
    items = [
        (RED_BG, RED_ACCENT, "Exam week", "0 - 7 days left"),
        (YEL_BG, YEL_ACCENT, "Revision", "8 - 14 days left"),
        (GRN_BG, GRN_ACCENT, "New Chapters", "15+ days left")
    ]
    
    cells = []
    for bg, accent, label, sub in items:
        cell_content = [
            Paragraph(f"<b>{label}</b>", styles['sp_legend_label']),
            Paragraph(sub, styles['sp_legend_sub'])
        ]
        
        t = Table([cell_content], colWidths=[TABLE_W / 3.1])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LINEBEFORE', (0,0), (0,-1), 4, accent),
            ('LINEABOVE', (0,0), (-1,-1), 0.5, BORDER),
            ('LINEBELOW', (0,0), (-1,-1), 0.5, BORDER),
            ('LINEAFTER', (0,0), (-1,-1), 0.5, BORDER),
        ]))
        cells.append(t)
        
    legend_table = Table([cells], colWidths=[TABLE_W / 3.0] * 3)
    legend_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    return legend_table

def build_timetable_table(rows, styles):
    col_widths = [
        TABLE_W * 0.15,  # Date
        TABLE_W * 0.18,  # Subject
        TABLE_W * 0.38,  # Topic / Chapters
        TABLE_W * 0.11,  # Time
        TABLE_W * 0.18   # Notes
    ]
    
    header = [
        Paragraph("DATE", styles["sp_col_header"]),
        Paragraph("SUBJECT", styles["sp_col_header"]),
        Paragraph("TOPICS", styles["sp_col_header"]),
        Paragraph("TIME", styles["sp_col_header"]),
        Paragraph("NOTES", styles["sp_col_header"])
    ]
    
    table_data = [header]
    row_styles = []
    
    for i, row in enumerate(rows):
        row_idx = i + 1  # Offset by 1 for header row
        
        _, bg_color, accent_color = get_urgency(row["exam_date"])
        
        try:
            d_obj = datetime.strptime(row["date"], "%Y-%m-%d")
            date_str = d_obj.strftime("%a %b %d")
        except (ValueError, TypeError):
            date_str = str(row["date"])
            
        topic_text = row["topic"].replace("\n", "<br/>")
        notes_text = row["notes"].replace("\n", "<br/>") if row["notes"] else "-"
        
        cells = [
            Paragraph(date_str, styles["sp_date_cell"]),
            Paragraph(row["subject"], styles["sp_subject_cell"]),
            Paragraph(topic_text, styles["sp_topic_cell"]),
            Paragraph(f"{row['minutes']} min", styles["sp_min_cell"]),
            Paragraph(notes_text, styles["sp_notes_cell"])
        ]
        table_data.append(cells)
        
        fill_bg = bg_color if bg_color else (ALT_ROW if i % 2 == 1 else WHITE)
        
        row_styles.extend([
            ('BACKGROUND', (0, row_idx), (-1, row_idx), fill_bg),
            ('LINEBEFORE', (0, row_idx), (0, row_idx), 3.5, accent_color),
            ('TOPPADDING', (0, row_idx), (-1, row_idx), 8),
            ('BOTTOMPADDING', (0, row_idx), (-1, row_idx), 8),
        ])
        
    base_style = [
        ('BACKGROUND', (0,0), (-1,0), HEADER_BG),
        ('TOPPADDING', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ] + row_styles
    
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle(base_style))
    return t

def generate_pdf(rows, summary, output_path="timetable.pdf"):
    # Resolve path relative to script directory if relative
    if not os.path.isabs(output_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, output_path)

    styles = make_styles()
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="Study Timetable"
    )
    
    generated_on = date.today().strftime("%B %d, %Y")
    total_slots = len(rows)
    total_mins = sum(r["minutes"] for r in rows)
    
    story = [
        Paragraph("StudyPilot - Weekly Timetable", styles["sp_title"]),
        Spacer(1, 4),
        Paragraph(
            f"Generated on {generated_on} &bull; <b>{total_slots}</b> sessions scheduled &bull; "
            f"<b>{total_mins // 60}h {total_mins % 60}m</b> total study time.", 
            styles["sp_subtitle"]
        ),
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=1, color=HEADER_BG, spaceAfter=15),
        build_timetable_table(rows, styles),
        Spacer(1, 15),
        Paragraph("<b>Status Legend</b>", styles["sp_subtitle"]),
        Spacer(1, 5),
        build_legend(styles)
    ]
    
    try:
        doc.build(story)
        print(f"Successfully saved PDF to: {output_path}")
    except Exception as e:
        print(f"Error building PDF: {e}", file=sys.stderr)
        raise RuntimeError(f"Error building PDF: {e}")

if __name__ == "__main__":
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_file = os.path.join(script_dir, "timetable.json")
        pdf_file = os.path.join(script_dir, "timetable.pdf")
        
        rows, summary = load_timetable(json_file)
        generate_pdf(rows, summary, output_path=pdf_file)
    except FileNotFoundError:
        print("Error: 'timetable.json' was not found. Please run planner.py first to generate the timetable.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to generate PDF: {e}", file=sys.stderr)
        sys.exit(1)
