import pytest
import os
from datetime import date, timedelta
import progress as progress_mod
from progress import mark_slot, compute_adherence, get_remaining_syllabus, save_progress

TEST_PROGRESS_FILE = "test_progress_pytest.json"


@pytest.fixture(autouse=True)
def isolate_progress_file(monkeypatch):
    """Route all progress reads/writes to a throwaway test file."""
    monkeypatch.setattr(progress_mod, "PROGRESS_FILE", TEST_PROGRESS_FILE)
    yield
    if os.path.exists(TEST_PROGRESS_FILE):
        os.remove(TEST_PROGRESS_FILE)



def _sample_timetable():
    today = date.today().strftime("%Y-%m-%d")
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "timetable": [
            {
                "day": 1, "date": yesterday,
                "slots": [{"subject": "Physics", "duration_minutes": 60, "chapters_to_cover": ["Mechanics"]}],
                "total_study_minutes": 60,
            },
            {
                "day": 2, "date": today,
                "slots": [{"subject": "Physics", "duration_minutes": 60, "chapters_to_cover": ["Optics"]}],
                "total_study_minutes": 60,
            },
            {
                "day": 3, "date": tomorrow,
                "slots": [{"subject": "Physics", "duration_minutes": 60, "chapters_to_cover": ["Thermo"]}],
                "total_study_minutes": 60,
            },
        ]
    }


def test_adherence_ignores_future_days():
    timetable = _sample_timetable()
    progress = {"completed": {}}
    stats = compute_adherence(timetable, progress)
    # Only yesterday + today count (2 slots) — tomorrow hasn't happened yet
    assert stats["total_slots"] == 2


def test_adherence_counts_completed_past_slot():
    timetable = _sample_timetable()
    yesterday = timetable["timetable"][0]["date"]
    progress = {"completed": {}}
    mark_slot(yesterday, "Physics", "Mechanics", True, progress)

    stats = compute_adherence(timetable, progress)
    assert stats["completed_slots"] == 1
    assert stats["adherence_pct"] == 50.0


def test_remaining_syllabus_excludes_completed_chapters():
    timetable = _sample_timetable()
    yesterday = timetable["timetable"][0]["date"]
    progress = {"completed": {}}
    mark_slot(yesterday, "Physics", "Mechanics", True, progress)

    original_syllabus = [{"subject": "Physics", "chapters": ["Mechanics", "Optics", "Thermo"], "exam_date": "", "weightage": "high"}]
    remaining = get_remaining_syllabus(original_syllabus, timetable, progress)

    assert "Mechanics" not in remaining[0]["chapters"]
    assert "Optics" in remaining[0]["chapters"]
    assert remaining[0]["_fully_completed"] is False


def test_remaining_syllabus_flags_fully_completed_subject():
    timetable = {
        "timetable": [{
            "day": 1, "date": date.today().strftime("%Y-%m-%d"),
            "slots": [{"subject": "Biology", "duration_minutes": 30, "chapters_to_cover": ["Cells"]}],
            "total_study_minutes": 30,
        }]
    }
    progress = {"completed": {}}
    mark_slot(timetable["timetable"][0]["date"], "Biology", "Cells", True, progress)

    original_syllabus = [{"subject": "Biology", "chapters": ["Cells"], "exam_date": "", "weightage": "low"}]
    remaining = get_remaining_syllabus(original_syllabus, timetable, progress)

    assert remaining[0]["_fully_completed"] is True
    assert remaining[0]["chapters"] == []
