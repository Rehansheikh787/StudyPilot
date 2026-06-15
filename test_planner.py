import pytest
from datetime import date, timedelta
from planner import calculate_priority, allocate_hours

def test_calculate_priority_closer_date():
    # Subject A: weightage 20%, exam in 5 days -> priority score = (20 / 5) * 100 = 400
    subject_a = {
        "subject": "Maths",
        "weightage": "20%",
        "exam_date": (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
    }
    # Subject B: weightage 20%, exam in 10 days -> priority score = (20 / 10) * 100 = 200
    subject_b = {
        "subject": "Physics",
        "weightage": "20%",
        "exam_date": (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    }
    
    score_a = calculate_priority(subject_a)
    score_b = calculate_priority(subject_b)
    
    assert score_a > score_b
    assert abs(score_a - 400.0) < 1.0
    assert abs(score_b - 200.0) < 1.0

def test_calculate_priority_higher_weightage():
    # Subject A: weightage 40%, exam in 10 days -> score = (40 / 10) * 100 = 400
    subject_a = {
        "subject": "Chemistry",
        "weightage": "40%",
        "exam_date": (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    }
    # Subject B: weightage 10%, exam in 10 days -> score = (10 / 10) * 100 = 100
    subject_b = {
        "subject": "Biology",
        "weightage": "10%",
        "exam_date": (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
    }
    
    score_a = calculate_priority(subject_a)
    score_b = calculate_priority(subject_b)
    
    assert score_a > score_b
    assert abs(score_a - 400.0) < 1.0
    assert abs(score_b - 100.0) < 1.0

def test_calculate_priority_invalid_date():
    # If date is invalid, it defaults to 30 days
    subject = {
        "subject": "English",
        "weightage": "30%",
        "exam_date": "invalid-date"
    }
    score = calculate_priority(subject)
    # score = (30 / 30) * 100 = 100
    assert abs(score - 100.0) < 1.0

def test_allocate_hours_empty():
    assert allocate_hours([]) == []

def test_allocate_hours_minimum_allocation():
    # If the daily hours are small, check that it still allocates at least 20 minutes (the minimum)
    subjects = [
        {"subject": "A", "weightage": "50%", "exam_date": (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")},
        {"subject": "B", "weightage": "50%", "exam_date": (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")}
    ]
    # Daily hours = 1 (60 minutes total)
    allocated = allocate_hours(subjects, daily_hours=1)
    
    assert len(allocated) == 2
    for item in allocated:
        assert item["daily_minutes"] >= 20
