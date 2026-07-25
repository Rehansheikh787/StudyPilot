"""
progress.py — Progress tracking and adaptive replanning for StudyPilot.

This is what turns StudyPilot from a one-shot "generate a PDF and forget it"
script into an actual planner: it tracks which scheduled sessions were
completed, computes adherence stats, and can regenerate the remaining
schedule around what's genuinely left to cover — instead of blindly
re-scheduling chapters the student already finished.
"""

import os
import json
from datetime import date, datetime, timedelta

PROGRESS_FILE = "progress.json"


def _resolve_path(path):
    if not os.path.isabs(path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(script_dir, path)
    return path


def load_progress(path=PROGRESS_FILE):
    """
    progress.json shape:
    {
      "completed": {
         "<date>|<subject>|<chapter>": true
      }
    }
    Keyed this way so completion state survives a full plan regeneration —
    it's tied to (date, subject, chapter), not to a slot index that would
    shift around every time the plan changes.
    """
    path = _resolve_path(path)
    if not os.path.exists(path):
        return {"completed": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"completed": {}}


def save_progress(data, path=PROGRESS_FILE):
    path = _resolve_path(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _slot_key(day_date, subject, chapter):
    return f"{day_date}|{subject}|{chapter}"


def mark_slot(day_date, subject, chapter, completed, progress=None):
    progress = progress if progress is not None else load_progress()
    key = _slot_key(day_date, subject, chapter)
    if completed:
        progress["completed"][key] = True
    else:
        progress["completed"].pop(key, None)
    save_progress(progress)
    return progress


def is_slot_completed(day_date, subject, chapter, progress=None):
    progress = progress if progress is not None else load_progress()
    return progress["completed"].get(_slot_key(day_date, subject, chapter), False)


def compute_adherence(timetable_data, progress=None, as_of=None):
    """
    Returns adherence stats for all days up to (and including) `as_of`
    (defaults to today) — i.e. days that have already happened, so it's
    a fair "did you do what you planned" measure rather than penalizing
    future days that haven't occurred yet.
    """
    progress = progress if progress is not None else load_progress()
    if as_of is None:
        as_of = date.today()

    total_slots = 0
    completed_slots = 0
    total_minutes = 0
    completed_minutes = 0
    per_subject = {}

    for day in timetable_data.get("timetable", []):
        try:
            day_date = datetime.strptime(day.get("date", ""), "%Y-%m-%d").date()
        except Exception:
            continue
        if day_date > as_of:
            continue

        for slot in day.get("slots", []):
            subject = slot.get("subject", "Unknown")
            minutes = slot.get("duration_minutes", 0)
            chapters = slot.get("chapters_to_cover") or ["General"]
            chapter = chapters[0] if isinstance(chapters, list) else str(chapters)

            total_slots += 1
            total_minutes += minutes
            per_subject.setdefault(subject, {"total": 0, "done": 0})
            per_subject[subject]["total"] += 1

            if is_slot_completed(day.get("date"), subject, chapter, progress):
                completed_slots += 1
                completed_minutes += minutes
                per_subject[subject]["done"] += 1

    adherence_pct = round((completed_slots / total_slots) * 100, 1) if total_slots else 0.0

    return {
        "total_slots": total_slots,
        "completed_slots": completed_slots,
        "adherence_pct": adherence_pct,
        "total_minutes": total_minutes,
        "completed_minutes": completed_minutes,
        "per_subject": per_subject,
    }


def get_remaining_syllabus(original_syllabus, timetable_data, progress=None):
    """
    Builds a "what's actually left" syllabus by removing chapters that have
    been marked complete anywhere in the existing timetable. This is fed
    back into planner.allocate_hours() + generate_weekly_plan() to produce
    a replan that doesn't re-schedule work the student already finished.
    """
    progress = progress if progress is not None else load_progress()

    completed_chapters_by_subject = {}
    for day in timetable_data.get("timetable", []):
        for slot in day.get("slots", []):
            subject = slot.get("subject", "")
            chapters = slot.get("chapters_to_cover") or []
            chapter = chapters[0] if chapters else None
            if chapter and is_slot_completed(day.get("date"), subject, chapter, progress):
                completed_chapters_by_subject.setdefault(subject, set()).add(chapter)

    remaining = []
    for subject in original_syllabus:
        name = subject.get("subject", "")
        done = completed_chapters_by_subject.get(name, set())
        remaining_chapters = [c for c in subject.get("chapters", []) if c not in done]

        # Keep the subject even if fully complete, but flag it, so the UI
        # can show "✅ done" instead of silently dropping it
        new_subject = dict(subject)
        new_subject["chapters"] = remaining_chapters
        new_subject["_fully_completed"] = len(remaining_chapters) == 0 and len(subject.get("chapters", [])) > 0
        remaining.append(new_subject)

    return remaining


def days_until_earliest_exam(syllabus):
    today = date.today()
    soonest = None
    for s in syllabus:
        try:
            d = datetime.strptime(s.get("exam_date", ""), "%Y-%m-%d").date()
            if d >= today and (soonest is None or d < soonest):
                soonest = d
        except Exception:
            continue
    if soonest is None:
        return 7
    return max((soonest - today).days, 1)
