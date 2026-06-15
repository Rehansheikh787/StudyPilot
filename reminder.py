import smtplib
import os
import sys
import json
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Ensure Unicode output works correctly on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Load environment variables relative to the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

def load_data(path="timetable.json"):
    """
    Loads timetable.json and flattens it into the format expected by send_daily_nudge:
    [{"date": "YYYY-MM-DD", "subject": "str", "topic": "str", "minutes": int, "notes": "str"}, ...]
    """
    if not os.path.isabs(path):
        path = os.path.join(script_dir, path)

    if not os.path.exists(path):
        print(f"Error: The timetable file '{path}' was not found.")
        print("Please run planner.py first to generate the timetable.")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        rows = []
        timetable = data.get("timetable", [])
        for day_entry in timetable:
            date_str = day_entry.get("date")
            for slot in day_entry.get("slots", []):
                chapters = slot.get("chapters_to_cover", [])
                if isinstance(chapters, list):
                    topic = ", ".join(chapters)
                else:
                    topic = str(chapters)
                
                rows.append({
                    "date": date_str,
                    "subject": slot.get("subject", ""),
                    "topic": topic,
                    "minutes": slot.get("duration_minutes", 0),
                    "notes": slot.get("notes", "")
                })
        return rows
    except Exception as e:
        print(f"Error reading timetable.json: {e}")
        return []

def load_syllabus_exams(path="syllabus.json"):
    """
    Loads syllabus.json and returns a dict mapping subject names to exam dates:
    {"subject_name": "YYYY-MM-DD", ...}
    """
    if not os.path.isabs(path):
        path = os.path.join(script_dir, path)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        exams = {}
        for entry in data:
            subj = entry.get("subject")
            exam_d = entry.get("exam_date")
            if subj and exam_d:
                # Keep the earliest exam date if duplicate subjects exist
                if subj in exams:
                    if exam_d < exams[subj]:
                        exams[subj] = exam_d
                else:
                    exams[subj] = exam_d
        return exams
    except Exception as e:
        print(f"Error loading syllabus exam dates: {e}")
        return {}

def send_daily_nudge(rows, recipient_email, target_date=None):
    if target_date is None:
        target_date = datetime.today().strftime("%Y-%m-%d")
    
    # Filter tasks scheduled for target date
    today_tasks = [r for r in rows if r.get('date') == target_date]
    
    # If there are no tasks for this date, notify and list available dates
    if not today_tasks:
        print(f"No tasks found for date '{target_date}'. Skipping email.")
        available_dates = sorted(list(set([r.get('date') for r in rows if r.get('date')])))
        if available_dates:
            print("\nAvailable dates in your timetable:")
            for d in available_dates:
                print(f"  - {d}")
            print(f"\nTo test a specific date, run:\n  python reminder.py --date {available_dates[0]}")
        return
 
    # Fetch environment configurations (support both GMAIL and EMAIL prefixes)
    sender_email = os.getenv("EMAIL_ID") or os.getenv("GMAIL_ID")
    app_password = os.getenv("EMAIL_PASSWORD") or os.getenv("GMAIL_PASSWORD")
    
    if not sender_email or not app_password:
        raise ValueError("EMAIL_ID or EMAIL_PASSWORD environment variables are not set in .env.")

    # Calculate exam reminders based on syllabus.json
    exams = load_syllabus_exams()
    exam_alerts_html = ""
    exam_alerts_console = []
    
    try:
        target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    except Exception:
        target_dt = datetime.today().date()
        
    for subj, exam_date_str in exams.items():
        try:
            exam_dt = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
            days_left = (exam_dt - target_dt).days
            if 0 <= days_left <= 14:
                if days_left <= 7:
                    color = "#ef4444"
                    bg = "#fee2e2"
                    border = "#fca5a5"
                    urgency_text = f"⚠️ <strong>URGENT ALERT:</strong> Your exam for <strong>{subj}</strong> is in <strong>{days_left} days</strong> ({exam_date_str})!"
                else:
                    color = "#d97706"
                    bg = "#fef3c7"
                    border = "#fde68a"
                    urgency_text = f"📅 <strong>UPCOMING EXAM:</strong> Your exam for <strong>{subj}</strong> is in <strong>{days_left} days</strong> ({exam_date_str})."
                
                exam_alerts_console.append(urgency_text.replace("<strong>", "").replace("</strong>", ""))
                exam_alerts_html += f"""
                <div style="background-color: {bg}; border: 1px solid {border}; color: {color}; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; font-size: 0.95em; font-family: Arial, sans-serif;">
                    {urgency_text}
                </div>
                """
        except Exception:
            pass

    if exam_alerts_console:
        print("\n🔔 UPCOMING EXAM WARNINGS:")
        for alert in exam_alerts_console:
            print(f"  {alert}")
        print("")

    # Construct HTML Table Rows dynamically from today's tasks
    table_rows = "".join([
        f"<tr>"
        f"<td style='padding: 8px; border: 1px solid #ddd;'>{r.get('subject', '')}</td>"
        f"<td style='padding: 8px; border: 1px solid #ddd;'>{r.get('topic', '')}</td>"
        f"<td style='padding: 8px; border: 1px solid #ddd; text-align: center;'>{r.get('minutes', 0)} mins</td>"
        f"<td style='padding: 8px; border: 1px solid #ddd;'>{r.get('notes', '') or 'N/A'}</td>"
        f"</tr>"
        for r in today_tasks
    ])
    
    # Aggregate total minutes
    total_mins = sum([int(r.get('minutes', 0)) for r in today_tasks])
    
    # Build complete HTML Email Content
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: #2b579a; border-bottom: 2px solid #2b579a; padding-bottom: 8px;">StudyPilot — Your Study Plan for {target_date}</h2>
        {exam_alerts_html}
        <p>Hello,</p>
        <p>Here is your scheduled study plan for today:</p>
        <table border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; width: 100%; max-width: 600px; margin-bottom: 20px;">
            <thead>
                <tr style="background-color: #2b579a; color: white;">
                    <th style="padding: 10px; border: 1px solid #2b579a; text-align: left;">Subject</th>
                    <th style="padding: 10px; border: 1px solid #2b579a; text-align: left;">Topic</th>
                    <th style="padding: 10px; border: 1px solid #2b579a; text-align: center;">Time</th>
                    <th style="padding: 10px; border: 1px solid #2b579a; text-align: left;">Notes</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        <p><strong>Total Study Time Today: {total_mins} minutes</strong></p>
        <p style="margin-top: 25px; padding-top: 15px; border-top: 1px solid #eee; font-size: 0.9em; color: #666;">
            Stay consistent, keep up the great work! See you tomorrow.<br>
            <em>Generated automatically by StudyPilot.</em>
        </p>
    </body>
    </html>
    """
    
    # Prepare Email Package
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"StudyPilot — Your plan for {target_date}"
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    # Attach HTML Content
    msg.attach(MIMEText(html, 'html'))
    
    # Establish Secure SMTP Connection and Send
    try:
        print(f"Connecting to Gmail SMTP server using {sender_email}...")
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()  # Secure the connection
            server.ehlo()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
            print(f"Mail successfully sent to {recipient_email} for date {target_date}!")
            return True
    except Exception as e:
        print(f"Failed to send email due to: {e}")
        raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StudyPilot Daily Study Reminder")
    parser.add_argument(
        "--date", 
        type=str, 
        help="Target study date in YYYY-MM-DD format (defaults to today)"
    )
    args = parser.parse_args()

    # Load the flattened study data
    rows = load_data()
    if not rows:
        sys.exit(1)

    # Resolve target date
    target_date = args.date
    if not target_date:
        target_date = datetime.today().strftime("%Y-%m-%d")
        
    # Check if receiver email is configured
    receiver = os.getenv("RECEIVER_EMAIL")
    if not receiver:
        print("Error: RECEIVER_EMAIL environment variable not set in .env.")
        sys.exit(1)

    send_daily_nudge(rows, receiver, target_date)
