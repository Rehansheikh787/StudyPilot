import json
import os
import sys
import re
from datetime import date, datetime
from groq import Groq
from dotenv import load_dotenv

# Ensure Unicode output works correctly on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set. Please create a '.env' file with your key.")
    return Groq(api_key=api_key)

def load_syllabus(path="syllabus.json"):
    # Resolve relative to the script's directory if path is a relative path
    if not os.path.isabs(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(script_dir, path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"The syllabus database '{os.path.basename(path)}' was not found.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    

def calculate_priority(subject, today=None):
    if today is None:
        today = date.today()

    exam_date_str = subject.get("exam_date")
    weightage_str = str(subject.get("weightage", "0%")).strip()

    # Parse the weightage (handle qualitative weights as well)
    try:
        clean_w = weightage_str.replace("%", "").strip().lower()
        if "high" in clean_w:
            weightage = 80.0
        elif "medium" in clean_w:
            weightage = 50.0
        elif "low" in clean_w:
            weightage = 20.0
        else:
            weightage = float(clean_w)
    except:
        weightage = 10.0

    # Days remaining until the exam
    if exam_date_str:
        try:
            exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
            days_remaining = max((exam_date - today).days, 1)
        except Exception as e:
            print(f"Warning: Could not parse exam date '{exam_date_str}': {e}. Defaulting remaining days to 30.", file=sys.stderr)
            days_remaining = 30
    else:
        days_remaining = 30
    
    # Priority score (higher weightage + fewer days left to the exam =  higher priority)
    priority = (weightage / days_remaining) * 100
    return priority


def allocate_hours(subjects, daily_hours=4):
    if not subjects:
        print("Warning: The syllabus list is empty. No hours can be allocated.", file=sys.stderr)
        return []

    scored = []
    for subject in subjects:
        score = calculate_priority(subject)
        scored.append({
            "subject" : subject.get("subject", "Unknown Subject"),
            "chapters" : subject.get("chapters", []),
            "exam_date" : subject.get("exam_date", "Not specified"),
            "priority_score" : score
        })
    
    scored.sort(key=lambda x: x["priority_score"], reverse=True)

    total_score = sum(s["priority_score"] for s in scored)
    if total_score == 0:
        total_score = 1.0  # Prevent division by zero if all scores are 0

    # Allocate minutes proportionally
    total_daily_minutes = daily_hours * 60

    for subject in scored:
        proportion = subject["priority_score"] / total_score
        minutes = round(proportion * total_daily_minutes)
        subject["daily_minutes"] = max(minutes, 20)

    return scored


def generate_weekly_plan(allocated_subjects, daily_hours=4, days_ahead=7):
    today = date.today()

    subjects_summary = ""

    for subject in allocated_subjects:
        subjects_summary += f"""
                Subject : {subject['subject']}
                Chapters : {', '.join(subject['chapters'])}
                Exam Date : {subject['exam_date']}
                Priority Score: {subject['priority_score']}
                Daily study time : {subject['daily_minutes']} minutes
            """
        
    prompt = f"""
            You are a study planner AI.

            Today is {today.strftime('%A, %d %B %Y')}.
            The student has {daily_hours} hours to study per day.
            Create a {days_ahead}-day study timetable.

            Here are the subjects with their priority scores and daily time allocations:
            {subjects_summary}

            Rules:
            1. Higher priority subjects get more time each day.
            2. Sequence chapters logically — foundational topics before advanced ones.
            3. Include short 10-minute breaks between subjects.
            4. On days 6 and 7 (weekend), add a 30-minute revision slot for the highest priority subject.
            5. Return ONLY valid JSON — no explanation, no markdown.

            Return this exact format:
            {{
            "timetable": [
                {{
                "day": 1,
                "date": "YYYY-MM-DD",
                "slots": [
                    {{
                    "subject": "string",
                    "duration_minutes": number,
                    "chapters_to_cover": ["string"],
                    "notes": "string"
                    }}
                ],
                "total_study_minutes": number
                }}
            ],
            "weekly_summary": "string"
            }}
            """

    client = get_groq_client()
    response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=3000
                )
    
    return response.choices[0].message.content

def clean_json_response(raw):
    """
    Cleans the raw LLM response by extracting only the JSON block.
    Uses regex to handle code blocks and outer braces robustly.
    """
    cleaned = raw.strip()
    
    # Try markdown block first
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    else:
        # Fall back to outer braces
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("No JSON found in LLM response.")
        cleaned = cleaned[start:end + 1]
        
    return cleaned


def display_timetable(timetable_data):
    print("\n" + "="*60)
    print("📚 YOUR STUDY TIMETABLE")
    print("="*60)

    for day in timetable_data.get("timetable", []):
        day_num = day.get("day", "?")
        day_date = day.get("date", "Unknown date")
        print(f"\n📅 Day {day_num} — {day_date}")
        print("-" * 40)
        for slot in day.get("slots", []):
            duration = slot.get("duration_minutes", 0)
            subject = slot.get("subject", "Unknown subject")
            chapters_list = slot.get("chapters_to_cover") or []
            chapters = ", ".join(chapters_list) if isinstance(chapters_list, list) else str(chapters_list)
            print(f"  ⏰  {duration} min | {subject}")
            print(f"      Chapters: {chapters}")
            if slot.get("notes"):
                print(f"      Note: {slot['notes']}")
        print(f"  Total: {day.get('total_study_minutes', 0)} minutes")

    print("\n" + "="*60)
    print("📌 WEEKLY SUMMARY")
    print(timetable_data.get("weekly_summary", ""))
    print("="*60 + "\n")

def add_metadata_to_timetable(timetable_data, subjects_list):
    """
    Appends subject-specific metadata (like exam dates) back to each daily slot
    since the LLM output might not preserve/include it.
    """
    exam_dates = {}
    for s in subjects_list:
        subj_name = s.get("subject")
        exam_d = s.get("exam_date")
        if subj_name:
            exam_dates[subj_name.strip().lower()] = exam_d
            
    # Add exam_date to slots
    for day in timetable_data.get("timetable", []):
        for slot in day.get("slots", []):
            subj = slot.get("subject", "").strip().lower()
            slot["exam_date"] = exam_dates.get(subj, "Not specified")
            
    return timetable_data

def main():
    try:
        print("Loading syllabus")
        subjects = load_syllabus()

        try:
            daily_hours = float(input("How many hours per day you can study? (default 4)"))
        except:
            daily_hours = 4.0

        print("Allocating study time across subjects")
        allocated = allocate_hours(subjects, daily_hours)

        print("Priority order")
        for i , subject in enumerate(allocated, 1):
            print(f" {i}. {subject['subject']} - Score: {subject['priority_score']} - {subject['daily_minutes']} min/day ")

        raw = generate_weekly_plan(allocated, daily_hours)
        cleaned = clean_json_response(raw)

        timetable_data = json.loads(cleaned)
        timetable_data = add_metadata_to_timetable(timetable_data, allocated)
        display_timetable(timetable_data)
        
        output_filename = "timetable.json"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, output_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(timetable_data, f, indent=2)
        
        print(f"saved to {output_filename}")
    except Exception as e:
        print(f"Timetable generation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
