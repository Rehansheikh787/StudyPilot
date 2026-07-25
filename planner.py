import json
import os
import sys
from datetime import date, datetime, timedelta
from dotenv import load_dotenv

from ai_provider import generate_structured, WeeklyTimetable, TimetableDay, TimetableSlot

# Ensure Unicode output works correctly on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()


def load_syllabus(path="syllabus.json"):
    if not os.path.isabs(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(script_dir, path)

    if not os.path.exists(path):
        raise FileNotFoundError(f"The syllabus database '{os.path.basename(path)}' was not found.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── Priority & allocation — deterministic, unchanged, unit-tested ───

def calculate_priority(subject, today=None):
    if today is None:
        today = date.today()

    exam_date_str = subject.get("exam_date")
    weightage_str = str(subject.get("weightage", "0%")).strip()

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
    except Exception:
        weightage = 10.0

    if exam_date_str:
        try:
            exam_date = datetime.strptime(exam_date_str, "%Y-%m-%d").date()
            days_remaining = max((exam_date - today).days, 1)
        except Exception as e:
            print(f"Warning: Could not parse exam date '{exam_date_str}': {e}. Defaulting remaining days to 30.", file=sys.stderr)
            days_remaining = 30
    else:
        days_remaining = 30

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
            "subject": subject.get("subject", "Unknown Subject"),
            "chapters": subject.get("chapters", []),
            "exam_date": subject.get("exam_date", "Not specified"),
            "priority_score": score
        })

    scored.sort(key=lambda x: x["priority_score"], reverse=True)

    total_score = sum(s["priority_score"] for s in scored)
    if total_score == 0:
        total_score = 1.0

    total_daily_minutes = daily_hours * 60

    for subject in scored:
        proportion = subject["priority_score"] / total_score
        minutes = round(proportion * total_daily_minutes)
        subject["daily_minutes"] = max(minutes, 20)

    return scored


# ─── AI-generated weekly plan — now schema-locked with fallback ──────

def _build_prompt(allocated_subjects, daily_hours, days_ahead, start_date):
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

            Today is {start_date.strftime('%A, %d %B %Y')}.
            The student has {daily_hours} hours to study per day.
            Create a {days_ahead}-day study timetable starting from today.

            Here are the subjects with their priority scores, remaining chapters,
            and daily time allocations:
            {subjects_summary}

            Rules:
            1. Higher priority subjects get more time each day.
            2. Sequence chapters logically — foundational topics before advanced ones.
            3. Include short 10-minute breaks between subjects.
            4. Add a revision slot for the highest priority subject on the last day.
            5. Only schedule chapters listed above — do not invent new ones.
            6. Return ONLY valid JSON — no explanation, no markdown.

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
    return prompt


def _local_fallback_plan(allocated_subjects, daily_hours, days_ahead, start_date) -> WeeklyTimetable:
    """
    Deterministic, no-AI fallback: round-robins through each subject's
    remaining chapters across the requested days, respecting each
    subject's proportional daily-minute allocation. No narrative
    sequencing intelligence, but it never leaves the user with a blank
    plan just because both AI providers were unavailable.
    """
    days = []
    # Track a per-subject cursor into its chapter list so chapters aren't repeated
    cursors = {s["subject"]: 0 for s in allocated_subjects}

    for d in range(days_ahead):
        day_date = start_date + timedelta(days=d)
        slots = []
        total_minutes = 0
        for subject in allocated_subjects:
            chapters = subject.get("chapters", []) or ["General revision"]
            cursor = cursors[subject["subject"]]
            chapter = chapters[cursor % len(chapters)]
            cursors[subject["subject"]] += 1

            minutes = subject["daily_minutes"]
            slots.append(TimetableSlot(
                subject=subject["subject"],
                duration_minutes=minutes,
                chapters_to_cover=[chapter],
                notes="Auto-generated (local fallback — AI providers unavailable)",
                exam_date=subject.get("exam_date", ""),
            ))
            total_minutes += minutes

        days.append(TimetableDay(
            day=d + 1,
            date=day_date.strftime("%Y-%m-%d"),
            slots=slots,
            total_study_minutes=total_minutes,
        ))

    return WeeklyTimetable(
        timetable=days,
        weekly_summary=(
            "This plan was generated in local fallback mode because no AI provider "
            "was reachable. Chapters were assigned round-robin by priority; consider "
            "regenerating once your GEMINI_API_KEY or GROQ_API_KEY is available."
        ),
    )


def generate_weekly_plan(allocated_subjects, daily_hours=4, days_ahead=7, start_date=None):
    """
    Generates a weekly plan via Gemini -> Groq -> local fallback.
    Returns (timetable_dict, provider_used).
    """
    if start_date is None:
        start_date = date.today()

    prompt = _build_prompt(allocated_subjects, daily_hours, days_ahead, start_date)

    def local_fallback():
        return _local_fallback_plan(allocated_subjects, daily_hours, days_ahead, start_date)

    result, provider = generate_structured(
        prompt=prompt,
        schema=WeeklyTimetable,
        local_fallback_fn=local_fallback,
    )

    return result.model_dump(), provider


def display_timetable(timetable_data):
    print("\n" + "=" * 60)
    print("📚 YOUR STUDY TIMETABLE")
    print("=" * 60)

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

    print("\n" + "=" * 60)
    print("📌 WEEKLY SUMMARY")
    print(timetable_data.get("weekly_summary", ""))
    print("=" * 60 + "\n")


def add_metadata_to_timetable(timetable_data, subjects_list):
    exam_dates = {}
    for s in subjects_list:
        subj_name = s.get("subject")
        exam_d = s.get("exam_date")
        if subj_name:
            exam_dates[subj_name.strip().lower()] = exam_d

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
        except Exception:
            daily_hours = 4.0

        print("Allocating study time across subjects")
        allocated = allocate_hours(subjects, daily_hours)

        print("Priority order")
        for i, subject in enumerate(allocated, 1):
            print(f" {i}. {subject['subject']} - Score: {subject['priority_score']} - {subject['daily_minutes']} min/day ")

        timetable_data, provider = generate_weekly_plan(allocated, daily_hours)
        print(f"Plan generated using: {provider}")
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
