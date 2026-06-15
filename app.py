import streamlit as st
import json
import os
import tempfile
import re
from datetime import datetime, date
from dotenv import load_dotenv

# Load environment variables on startup
load_dotenv()

import importlib
import sys

# Force reload of local modules to prevent Streamlit reload/caching issues
import extract
import planner
import pdf_export
import reminder

importlib.reload(extract)
importlib.reload(planner)
importlib.reload(pdf_export)
importlib.reload(reminder)

from extract import extract_text_from_pdf, extract_structured_syllabus, clean_and_parse_json
from planner import allocate_hours, generate_weekly_plan, clean_json_response, add_metadata_to_timetable
from pdf_export import generate_pdf, load_timetable, get_urgency
from reminder import send_daily_nudge

# Helper for email validation
def is_valid_email(email_str):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email_str))

# Helper to clean and render HTML safely in Streamlit
def render_html(html_str):
    cleaned = "".join([line.strip() for line in html_str.splitlines()])
    st.markdown(cleaned, unsafe_allow_html=True)

# Helper to translate urgency to UI-friendly hex codes
def get_ui_urgency(exam_date):
    name, _, _ = get_urgency(exam_date)
    if name == "red":
        return "#ef4444", "#fee2e2", "Exam Looming"
    elif name == "yellow":
        return "#d97706", "#fef3c7", "Revision Zone"
    return "#10b981", "#d1fae5", "Standard"

# ─── 1. Page Configuration ───
st.set_page_config(
    page_title="Study Pilot — AI Study Planner",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── 2. Session State & Persistence ───
if "timetable_data" not in st.session_state:
    st.session_state.timetable_data = None
    st.session_state.rows = None
    st.session_state.summary = None
if "selected_day" not in st.session_state:
    st.session_state.selected_day = 0

# Try to auto-load saved timetable if session state is empty
if st.session_state.timetable_data is None:
    if os.path.exists("timetable.json") and os.path.exists("timetable.pdf"):
        try:
            rows, summary = load_timetable("timetable.json")
            with open("timetable.json", "r", encoding="utf-8") as f:
                t_data = json.load(f)
            st.session_state.timetable_data = t_data
            st.session_state.rows = rows
            st.session_state.summary = summary
        except Exception as e:
            # Malformed files or error loading, ignore and proceed
            pass

# ─── 3. Global Premium CSS (Soft Structuralism — DESIGN.md palette) ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    /* ── Typography Reset & Layout Fixes ── */
    html, body, .stApp, h1, h2, h3, h4, h5, h6, p, li, a, input, button, select, textarea, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }
    html, body, .stApp {
        line-height: 1.5;
    }
    h1, h2, h3, h4, h5, h6 {
        font-weight: 800 !important;
        margin-top: 0;
        margin-bottom: 0.5rem;
    }

    /* ── App Background ── */
    .stApp {
        background: #f8fafc !important;
        background-image:
            radial-gradient(circle 800px at 0px 0px, rgba(99, 102, 241, 0.08), transparent),
            radial-gradient(circle 800px at 100% 100%, rgba(236, 72, 153, 0.06), transparent),
            radial-gradient(circle 600px at 50% 50%, rgba(16, 185, 129, 0.04), transparent) !important;
        background-attachment: fixed !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #eef2ff !important;
    }

    /* ── Input fields ── */
    .stTextInput > div > div > input {
        background: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 10px !important;
        color: #0f172a !important;
        font-weight: 500 !important;
        padding: 0.7rem 1rem !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #4f46e5 !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.08) !important;
    }
    .stTextInput div[data-testid="InputInstructions"] { display: none !important; }

    /* ── File Uploader ── */
    [data-testid="stFileUploader"] {
        background: #ffffff !important;
        border: 2px dashed #dce9ff !important;
        border-radius: 14px !important;
        padding: 1.5rem !important;
        transition: border-color 0.3s ease !important;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #4f46e5 !important;
    }

    /* ── Slider ── */
    div[data-testid="stSlider"] div[role="slider"] {
        background: #4f46e5 !important;
        border: 2px solid #fff !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25) !important;
    }
    div[data-testid="stSlider"] div[aria-valuenow] {
        color: #4f46e5 !important;
        font-weight: 700 !important;
    }

    /* ── Buttons (all default) ── */
    div.stButton > button:first-child {
        background: #4f46e5 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        padding: 0.7rem 2rem !important;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.18) !important;
        transition: all 0.2s cubic-bezier(0.32, 0.72, 0, 1) !important;
    }
    div.stButton > button:first-child:hover {
        background: #4338ca !important;
        box-shadow: 0 8px 20px rgba(79, 70, 229, 0.25) !important;
        transform: translateY(-1px) !important;
    }
    div.stButton > button:first-child:active {
        transform: translateY(1px) scale(0.98) !important;
        box-shadow: 0 2px 8px rgba(79, 70, 229, 0.12) !important;
    }

    /* ── Download Button (emerald) ── */
    .stDownloadButton > button {
        background: #059669 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.4rem !important;
        box-shadow: 0 4px 14px rgba(5, 150, 105, 0.18) !important;
        transition: all 0.2s cubic-bezier(0.32, 0.72, 0, 1) !important;
        width: 100% !important;
    }
    .stDownloadButton > button:hover {
        background: #047857 !important;
        transform: translateY(-1px) !important;
    }

    /* ── Segmented Tabs Overrides ── */
    div[data-testid="stTabBar"] {
        background: #ffffff !important;
        border: 1px solid #eef2ff !important;
        border-radius: 9999px !important;
        padding: 4px 8px !important;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.02) !important;
        margin-bottom: 1.5rem !important;
    }
    button[data-baseweb="tab"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 700 !important;
        color: #64748b !important;
        border-radius: 9999px !important;
        padding: 8px 18px !important;
        border: none !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        font-size: 0.88rem !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #4f46e5 !important;
        background: #f1f5f9 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.2) !important;
    }
    div[data-baseweb="tab-highlight-bar"] {
        display: none !important;
    }

    /* ── Container border cards ── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #eef2ff !important;
        border-radius: 18px !important;
        padding: 2rem !important;
        background: #ffffff !important;
        box-shadow: 0 8px 30px rgba(15, 23, 42, 0.04) !important;
        border-top: 4px solid #4f46e5 !important;
    }

    /* ── Slide-up animation keyframes ── */
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(18px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .animate-in {
        animation: slideUp 0.55s cubic-bezier(0.32, 0.72, 0, 1) both;
    }
</style>
""", unsafe_allow_html=True)

# ─── Declare default form vars ───
uploaded_file = None
email = ""
hours = 4
generate_clicked = False

# ═══════════════════════════════════════════════════════════════════
# 4. WELCOME PAGE (no timetable generated yet)
# ═══════════════════════════════════════════════════════════════════
if st.session_state.timetable_data is None:
    # Hide sidebar on welcome
    st.markdown("""
    <style>
        [data-testid="stSidebar"]       { display: none !important; }
        [data-testid="collapsedControl"]{ display: none !important; }
        .block-container {
            max-width: 1100px !important;
            padding-top: 3rem !important;
            padding-bottom: 4rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # ── Hero split ──
    hero_left, hero_right = st.columns([1.15, 1], gap="large")

    with hero_left:
        render_html("""
        <div class="animate-in" style="animation-delay: 0.05s;">
            <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff;
                        padding: 0.45rem 1.1rem; border-radius: 9999px;
                        font-size: 0.72rem; font-weight: 800; width: fit-content; margin-bottom: 1.75rem;
                        letter-spacing: 0.08em; text-transform: uppercase;
                        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.22);">
                ⚡ AI-Powered Study Engine
            </div>
            <h1 style="font-size: 3.75rem; font-weight: 800; line-height: 1.1; margin-bottom: 1.5rem;
                       background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #ec4899 100%);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                       letter-spacing: -0.03em;">
                Study Pilot
            </h1>
            <p style="font-size: 1.15rem; color: #334155; line-height: 1.7; margin-bottom: 0rem; max-width: 520px; font-weight: 500;">
                Transform raw syllabus documents into a customized, high-yield study schedule.
                Our AI analyzes chapters, exam dates, and subject weights to map out your perfect
                7-day preparation roadmap.
            </p>
        </div>
        """)

    with hero_right:
        # ── Configuration Card ──
        with st.container(border=True):
            st.markdown("<h3 style='margin-top:0; color:#0f172a; font-size:1.4rem; font-weight:800;'>Configure Your Plan</h3>", unsafe_allow_html=True)
            st.markdown("<p style='color:#475569; font-size:0.9rem; margin-bottom:1.5rem; font-weight:500;'>Upload your syllabus and set preferences to generate a personalised study roadmap.</p>", unsafe_allow_html=True)

            uploaded_file = st.file_uploader("Syllabus PDF", type=["pdf"], key="w_upload")
            email = st.text_input("Email (for daily reminders)", placeholder="you@university.edu", key="w_email")
            st.write("")
            hours = st.slider("Daily study hours", min_value=1, max_value=12, value=4, key="w_hours")
            st.write("")
            generate_clicked = st.button("✨ Generate My Study Plan", use_container_width=True, key="w_generate")

    # ── Feature cards row ──
    st.write("")
    st.divider()
    st.write("")

    f1, f2, f3 = st.columns(3, gap="medium")

    with f1:
        render_html("""
        <div class="animate-in" style="animation-delay: 0.15s;
             background: linear-gradient(135deg, #ffffff 0%, #f5f7ff 100%);
             border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.5rem;
             box-shadow: 0 10px 25px rgba(79, 70, 229, 0.04);
             border-left: 5px solid #4f46e5; min-height: 130px;">
            <div style="font-size: 1.1rem; font-weight: 800; color: #4f46e5; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.35rem;">
                📈 Weightage Ranking
            </div>
            <div style="font-size: 0.88rem; color: #475569; line-height: 1.55; font-weight: 500;">
                Automatically analyzes chapter counts and exam dates to prioritize high-yield milestones.
            </div>
        </div>
        """)

    with f2:
        render_html("""
        <div class="animate-in" style="animation-delay: 0.25s;
             background: linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%);
             border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.5rem;
             box-shadow: 0 10px 25px rgba(5, 150, 105, 0.04);
             border-left: 5px solid #059669; min-height: 130px;">
            <div style="font-size: 1.1rem; font-weight: 800; color: #059669; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.35rem;">
                📅 Micro-Schedules
            </div>
            <div style="font-size: 0.88rem; color: #475569; line-height: 1.55; font-weight: 500;">
                Proportionally scales core daily review blocks and built-in recharge slots across 7 days.
            </div>
        </div>
        """)

    with f3:
        render_html("""
        <div class="animate-in" style="animation-delay: 0.35s;
             background: linear-gradient(135deg, #ffffff 0%, #fffbeb 100%);
             border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.5rem;
             box-shadow: 0 10px 25px rgba(217, 119, 6, 0.04);
             border-left: 5px solid #d97706; min-height: 130px;">
            <div style="font-size: 1.1rem; font-weight: 800; color: #d97706; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.35rem;">
                🔔 Email Nudges
            </div>
            <div style="font-size: 0.88rem; color: #475569; line-height: 1.55; font-weight: 500;">
                Pushes tailored summaries, trackable deadlines, and review links straight to your inbox.
            </div>
        </div>
        """)

# ═══════════════════════════════════════════════════════════════════
# 5. DASHBOARD PAGE (timetable is generated)
# ═══════════════════════════════════════════════════════════════════
else:
    # ── Sidebar config ──
    st.sidebar.markdown("## ⚙️ Study Configuration")
    uploaded_file = st.sidebar.file_uploader("Upload Syllabus PDF", type=["pdf"], key="sb_upload")
    email = st.sidebar.text_input("Your Email (for reminders)", key="sb_email")
    hours = st.sidebar.slider("Daily Study Hours Limit", min_value=1, max_value=12, value=4, key="sb_hours")
    generate_clicked = st.sidebar.button("⚡ Re-Generate Plan", use_container_width=True, key="sb_generate")
    
    st.sidebar.write("---")
    if st.sidebar.button("🗑️ Reset App & Clear Plan", use_container_width=True, key="sb_reset"):
        # Delete generated files
        for f_path in ["timetable.json", "timetable.pdf", "syllabus.json"]:
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except:
                    pass
        # Clear session state
        st.session_state.timetable_data = None
        st.session_state.rows = None
        st.session_state.summary = None
        st.toast("🧹 App reset and study plan cleared.")
        st.rerun()

    # ── Dashboard header ──
    render_html("""
    <div class="animate-in" style="background:#fff; border:1.5px solid #eef2ff; border-radius:20px;
         padding:1.75rem 2rem; box-shadow: 0 10px 30px rgba(15,23,42,0.02); margin-bottom:2rem;
         display:flex; align-items:center; gap:1.5rem; border-left: 6px solid #4f46e5;">
        <div style="font-size:2.75rem; background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%); padding: 0.5rem; border-radius: 12px; display: flex; align-items: center; justify-content: center;">📚</div>
        <div>
            <h1 style="font-size:2.25rem; margin:0; background: linear-gradient(135deg, #4f46e5, #ec4899);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent; font-weight:800; letter-spacing: -0.02em;">Study Pilot</h1>
            <p style="font-size:0.92rem; color:#475569; margin:0.25rem 0 0; font-weight:600;">
                Smart AI-powered study scheduler based on subject weightage, chapter count, and exam dates.
            </p>
        </div>
    </div>
    """)

    # ── Compute dashboard data ──
    total_sessions = len(st.session_state.rows)
    total_mins = sum(r["minutes"] for r in st.session_state.rows)
    total_hours_str = f"{total_mins // 60}h {total_mins % 60}m"
    subjects = list(set([r["subject"] for r in st.session_state.rows]))

    subjects_info = {}
    for r in st.session_state.rows:
        subj = r["subject"]
        if subj not in subjects_info:
            subjects_info[subj] = {"minutes": 0, "exam_date": r["exam_date"]}
        subjects_info[subj]["minutes"] += r["minutes"]

    nearest_exam_days = 999
    nearest_exam_subj = ""
    for subj, info in subjects_info.items():
        if info["exam_date"]:
            try:
                d = (datetime.strptime(info["exam_date"], "%Y-%m-%d").date() - date.today()).days
                if 0 <= d < nearest_exam_days:
                    nearest_exam_days = d
                    nearest_exam_subj = subj
            except Exception:
                pass

    days_list = (st.session_state.timetable_data
                 if isinstance(st.session_state.timetable_data, list)
                 else st.session_state.timetable_data.get("timetable", []))

    # ── Metrics row ──
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_html(f"""
        <div class="animate-in" style="animation-delay: 0.05s;
                    background: linear-gradient(135deg, #eef2ff 0%, #c7d2fe 100%);
                    border-left: 5px solid #4f46e5; border-radius: 14px; padding: 1.25rem;
                    box-shadow: 0 4px 15px rgba(79, 70, 229, 0.08); border-top: 1px solid rgba(255,255,255,0.5);">
            <div style="font-size: 0.82rem; font-weight: 800; color: #4338ca; text-transform: uppercase; letter-spacing: 0.05em;">📚 Total Subjects</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: #1e1b4b; margin-top: 0.25rem;">{len(subjects)}</div>
        </div>
        """)
    with col2:
        render_html(f"""
        <div class="animate-in" style="animation-delay: 0.1s;
                    background: linear-gradient(135deg, #ecfdf5 0%, #a7f3d0 100%);
                    border-left: 5px solid #059669; border-radius: 14px; padding: 1.25rem;
                    box-shadow: 0 4px 15px rgba(5, 150, 105, 0.08); border-top: 1px solid rgba(255,255,255,0.5);">
            <div style="font-size: 0.82rem; font-weight: 800; color: #065f46; text-transform: uppercase; letter-spacing: 0.05em;">⏱️ Total Study Time</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: #064e3b; margin-top: 0.25rem;">{total_hours_str}</div>
        </div>
        """)
    with col3:
        render_html(f"""
        <div class="animate-in" style="animation-delay: 0.15s;
                    background: linear-gradient(135deg, #f5f3ff 0%, #ddd6fe 100%);
                    border-left: 5px solid #7c3aed; border-radius: 14px; padding: 1.25rem;
                    box-shadow: 0 4px 15px rgba(124, 58, 237, 0.08); border-top: 1px solid rgba(255,255,255,0.5);">
            <div style="font-size: 0.82rem; font-weight: 800; color: #5b21b6; text-transform: uppercase; letter-spacing: 0.05em;">🎓 Scheduled Sessions</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: #4c1d95; margin-top: 0.25rem;">{total_sessions}</div>
        </div>
        """)
    with col4:
        if nearest_exam_subj:
            label_subj = nearest_exam_subj[:12] + "…" if len(nearest_exam_subj) > 12 else nearest_exam_subj
            metric_val = f"{nearest_exam_days} Days"
            metric_lbl = f"🚨 Next: {label_subj}"
        else:
            metric_val = "None"
            metric_lbl = "🚨 Next Exam"
        render_html(f"""
        <div class="animate-in" style="animation-delay: 0.2s;
                    background: linear-gradient(135deg, #fff1f2 0%, #fecdd3 100%);
                    border-left: 5px solid #e11d48; border-radius: 14px; padding: 1.25rem;
                    box-shadow: 0 4px 15px rgba(225, 29, 72, 0.08); border-top: 1px solid rgba(255,255,255,0.5);">
            <div style="font-size: 0.82rem; font-weight: 800; color: #9f1239; text-transform: uppercase; letter-spacing: 0.05em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{metric_lbl}</div>
            <div style="font-size: 1.85rem; font-weight: 800; color: #881337; margin-top: 0.25rem;">{metric_val}</div>
        </div>
        """)

    st.write("")

    # ── Dashboard tabs ──
    tab1, tab2 = st.tabs(["📊 Workspace Dashboard", "📧 Email Nudges"])

    # ── TAB 1: Bento Grid ──
    with tab1:
        main_col, side_col = st.columns([5, 3], gap="large")

        with main_col:
            st.markdown("<h3 style='color:#0f172a; margin-top:0.5rem; font-weight:800; font-size:1.4rem;'>📅 Weekly Study Schedule</h3>", unsafe_allow_html=True)

            if days_list:
                day_tab_list = st.tabs([f"Day {d.get('day', i+1)}" for i, d in enumerate(days_list)])
                
                for sel, day in enumerate(days_list):
                    with day_tab_list[sel]:
                        day_num = day.get('day', '')
                        day_date = day.get('date', '')
                        total_day_m = day.get('total_study_minutes', 0)

                        # Day header
                        render_html(f"""
                        <div style="display:flex; justify-content:space-between; align-items:center;
                             border-bottom:1.5px solid #f1f5f9; padding-bottom:0.75rem; margin: 0.75rem 0 1.25rem 0;">
                            <span style="font-size:1.15rem; font-weight:800; color:#4f46e5;">
                                📅 Day {day_num} — {day_date}
                            </span>
                            <span style="background:#eef2ff; color:#4f46e5; border-radius:9999px;
                                  padding:0.25rem 0.75rem; font-size:0.8rem; font-weight:700;">
                                ⏱️ {total_day_m} mins scheduled
                            </span>
                        </div>
                        """)

                        for slot in day.get("slots", []):
                            chapters = slot.get("chapters_to_cover", [])
                            ch_str = ", ".join(chapters) if isinstance(chapters, list) else str(chapters)
                            uc, ubg, utxt = get_ui_urgency(slot.get("exam_date", ""))
                            
                            # Map urgency to card background and borders
                            if utxt == "Exam Looming":
                                card_bg = "#fff5f5"
                                card_border = "#fca5a5"
                                left_accent = "#ef4444"
                            elif utxt == "Revision Zone":
                                card_bg = "#fffbeb"
                                card_border = "#fde68a"
                                left_accent = "#d97706"
                            else:
                                card_bg = "#ffffff"
                                card_border = "#eef2ff"
                                left_accent = "#4f46e5"
                                
                            notes_html = (f'<div style="font-size:0.82rem; color:#475569; font-style:italic; '
                                          f'margin-top:0.5rem; border-left:2.5px solid #dbeafe; padding-left:0.7rem; '
                                          f'line-height:1.4; word-break:break-word;">'
                                          f'💡 <strong>Advisor Tip:</strong> {slot.get("notes")}</div>') if slot.get("notes") else ""

                            render_html(f"""
                            <div style="background:{card_bg}; border:1.5px solid {card_border}; border-radius:14px;
                                 padding:1.25rem; margin-bottom:0.85rem; border-left:6px solid {left_accent};
                                 box-shadow: 0 4px 15px rgba(15,23,42,0.01);
                                 transition: transform 0.2s ease, box-shadow 0.2s ease;">
                                <div style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:0.5rem; margin-bottom:0.6rem;">
                                    <span style="font-size:1.05rem; font-weight:800; color:#0f172a; max-width:65%; word-break:break-word; line-height:1.3;">{slot.get('subject')}</span>
                                    <div style="display:flex; gap:0.4rem; flex-wrap:wrap;">
                                        <span style="background:#eef2ff; color:#4f46e5; border:1px solid rgba(79,70,229,0.12);
                                              border-radius:9999px; padding:0.25rem 0.65rem; font-size:0.72rem; font-weight:700; white-space:nowrap;">
                                            ⏱ {slot.get('duration_minutes',0)} min
                                        </span>
                                        <span style="background:{ubg}; color:{uc}; border:1px solid {uc}25;
                                              border-radius:9999px; padding:0.25rem 0.65rem; font-size:0.72rem; font-weight:700; white-space:nowrap;">
                                            {utxt}
                                        </span>
                                    </div>
                                </div>
                                <div style="font-size:0.88rem; color:#475569; line-height:1.45; word-break:break-word;">
                                    <b style="color:#0f172a;">Topics:</b> {ch_str}
                                </div>
                                {notes_html}
                            </div>
                            """)

        with side_col:
            # ── Priority Breakdown ──
            st.markdown("<h3 style='color:#0f172a; margin-top:0.5rem; font-weight:800; font-size:1.4rem;'>📊 Priority Breakdown</h3>", unsafe_allow_html=True)

            for idx, (subj, info) in enumerate(subjects_info.items()):
                total_m = info["minutes"]
                exam_d = info["exam_date"]
                urgency_name, _, _ = get_urgency(exam_d)
                bar_w = "90%" if urgency_name == "red" else ("55%" if urgency_name == "yellow" else "30%")
                
                # Determine colors and gradients based on urgency
                if urgency_name == "red":
                    card_bg = "linear-gradient(135deg, #ffffff 0%, #fff5f5 100%)"
                    card_border = "#fca5a5"
                    bar_gradient = "linear-gradient(90deg, #f43f5e 0%, #ef4444 100%)"
                    bar_c = "#ef4444"
                elif urgency_name == "yellow":
                    card_bg = "linear-gradient(135deg, #ffffff 0%, #fffbeb 100%)"
                    card_border = "#fde68a"
                    bar_gradient = "linear-gradient(90deg, #fbbf24 0%, #d97706 100%)"
                    bar_c = "#d97706"
                else:
                    card_bg = "linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%)"
                    card_border = "#bbf7d0"
                    bar_gradient = "linear-gradient(90deg, #34d399 0%, #10b981 100%)"
                    bar_c = "#10b981"

                render_html(f"""
                <div class="animate-in" style="animation-delay: {idx*0.06}s;
                     background:{card_bg}; border:1.5px solid {card_border}; border-radius:14px;
                     padding:1.1rem; margin-bottom:0.75rem;
                     box-shadow: 0 4px 15px rgba(15,23,42,0.015);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem; gap:0.5rem; flex-wrap:wrap;">
                        <strong style="font-size:0.95rem; color:#0f172a; word-break:break-word; max-width:70%;">{subj}</strong>
                        <span style="font-size:0.72rem; font-weight:800; color:{bar_c};
                              text-transform:uppercase; letter-spacing:0.05em;">{urgency_name}</span>
                    </div>
                    <div style="font-size:0.82rem; color:#475569; margin-bottom:0.6rem; font-weight:600;">
                        ⏱ {total_m // 60}h {total_m % 60}m &nbsp;·&nbsp; 📅 Exam: {exam_d or 'N/A'}
                    </div>
                    <div style="height:6px; background:rgba(15,23,42,0.05); border-radius:4px; overflow:hidden;">
                        <div style="width:{bar_w}; height:100%; background:{bar_gradient}; border-radius:4px;"></div>
                    </div>
                </div>
                """)

            # ── Quick Actions ──
            st.markdown("### ⚡ Quick Actions")

            render_html("""
            <div style="background:#fff; border:1px solid #eef2ff; border-radius:14px;
                 padding:1.1rem; box-shadow: 0 4px 16px rgba(15,23,42,0.02); margin-bottom:0.65rem;">
                <p style="font-size:0.88rem; color:#64748b; margin-bottom:0.75rem;">
                    Export schedule or trigger email reminder:
                </p>
            """)

            if os.path.exists("timetable.pdf"):
                with open("timetable.pdf", "rb") as f:
                    st.download_button("📥 Download Study Plan PDF", data=f,
                                       file_name="my_study_plan.pdf", mime="application/pdf",
                                       use_container_width=True)

            render_html("</div>")

            # ── AI Summary ──
            if st.session_state.summary:
                st.markdown("<h3 style='color:#0f172a; margin-top:1.25rem; font-weight:800; font-size:1.4rem;'>💡 AI Study Advisor</h3>", unsafe_allow_html=True)
                render_html(f"""
                <div class="animate-in" style="animation-delay: 0.3s;
                     background: linear-gradient(135deg, #f5f3ff 0%, #edd8ff 100%);
                     border: 1.5px solid #d8b4fe; border-radius: 14px;
                     padding: 1.25rem; box-shadow: 0 4px 20px rgba(124, 58, 237, 0.08);
                     font-size: 0.92rem; color: #581c87; line-height: 1.6; font-weight: 500; font-style: italic;">
                    <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.6rem; font-weight:800; color:#7c3aed; font-style:normal; font-size:0.8rem; letter-spacing:0.05em; text-transform:uppercase;">
                        ✨ Advisor Recommendation
                    </div>
                    "{st.session_state.summary}"
                </div>
                """)

    # ── TAB 2: Email Nudges ──
    with tab2:
        st.markdown("### 📧 Personalized Daily Email Nudges")
        st.write("Review, preview, and manually dispatch daily study plans directly to your email address.")

        if not email:
            st.info("💡 Enter your email address in the sidebar to enable sending daily email nudges.")
        else:
            dates = sorted(list(set([r["date"] for r in st.session_state.rows])))
            selected_date = st.selectbox("📅 Select Date for Study Plan Nudge", dates)
            day_tasks = [r for r in st.session_state.rows if r.get('date') == selected_date]

            st.markdown(f"#### 🔍 Email Preview for {selected_date}")

            if day_tasks:
                st.table([{
                    "Subject": r.get("subject"),
                    "Topic": r.get("topic"),
                    "Duration": f"{r.get('minutes')} mins",
                    "Notes": r.get("notes") or "N/A"
                } for r in day_tasks])

                if st.button("📨 Send Nudge Email", use_container_width=True):
                    if not is_valid_email(email):
                        st.error("❌ Please enter a valid email address.")
                    else:
                        sender = os.getenv("EMAIL_ID") or os.getenv("GMAIL_ID")
                        passwd = os.getenv("EMAIL_PASSWORD") or os.getenv("GMAIL_PASSWORD")
                        if not sender or not passwd:
                            st.error("🔑 SMTP credentials missing! Set EMAIL_ID and EMAIL_PASSWORD in .env")
                        else:
                            with st.spinner("Sending study reminder…"):
                                try:
                                    send_daily_nudge(st.session_state.rows, recipient_email=email, target_date=selected_date)
                                    st.success(f"🚀 Email sent to **{email}** for **{selected_date}**!")
                                except Exception as e:
                                    st.error(f"❌ Failed to send email: {e}")
            else:
                st.warning("No study sessions scheduled for this date.")


# ─── 6. GENERATION LOGIC (shared between welcome & sidebar) ───
if generate_clicked:
    if not uploaded_file:
        st.error("❌ Please upload a syllabus PDF first!")
    else:
        with st.spinner("⏳ Step 1/3 — Reading and extracting syllabus text…"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name
            try:
                raw_text = extract_text_from_pdf(tmp_path)
                if not raw_text.strip():
                    st.error("❌ No readable text could be extracted from this PDF. Please ensure it is a text-based PDF (not a scanned image without OCR).")
                    st.stop()
                
                raw_syllabus = extract_structured_syllabus(raw_text)
                syllabus = clean_and_parse_json(raw_syllabus)
                
                if not syllabus:
                    st.error("❌ The AI could not identify any structured syllabus entries. Please check the PDF contents.")
                    st.stop()
                else:
                    try:
                        with open("syllabus.json", "w", encoding="utf-8") as f:
                            json.dump(syllabus, f, indent=2)
                    except Exception as e:
                        pass
            except Exception as e:
                st.error(f"❌ Failed to parse syllabus PDF: {e}")
                st.stop()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        with st.spinner("⏳ Step 2/3 — Calculating priorities and generating timetable…"):
            try:
                allocated = allocate_hours(syllabus, daily_hours=hours)
                raw_timetable = generate_weekly_plan(allocated, daily_hours=hours)
                cleaned_timetable = clean_json_response(raw_timetable)
                timetable_data = json.loads(cleaned_timetable)
                timetable_data = add_metadata_to_timetable(timetable_data, allocated)
                with open("timetable.json", "w", encoding="utf-8") as f:
                    json.dump(timetable_data, f, indent=2)
            except Exception as e:
                st.error(f"❌ Failed to generate timetable: {e}")
                st.stop()

        with st.spinner("⏳ Step 3/3 — Exporting timetable PDF…"):
            try:
                rows, summary = load_timetable("timetable.json")
                generate_pdf(rows, summary, output_path="timetable.pdf")
            except Exception as e:
                st.error(f"❌ Failed to build PDF: {e}")
                st.stop()

        st.session_state.timetable_data = timetable_data
        st.session_state.rows = rows
        st.session_state.summary = summary
        st.toast("🎉 Study plan generated successfully!")
        st.rerun()
