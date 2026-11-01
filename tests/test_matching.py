"""Smoke tests for the rule matcher."""

import pytest
from pydantic import ValidationError

from acp.matching.matcher import match_students, match_teachers
from acp.matching.profiles import Opening, SchoolProgram, StudentProfile, TeacherProfile


def _teacher(**overrides: object) -> TeacherProfile:
    data: dict[str, object] = {
        "id": "teacher-ada",
        "display_name": "Ada Okonkwo",
        "subjects": ["Mathematics"],
        "grade_min": 9,
        "grade_max": 12,
        "mode": "in_person",
        "location": "Springfield",
        "license_active": True,
    }
    data.update(overrides)
    return TeacherProfile.model_validate(data)


def _opening(**overrides: object) -> Opening:
    data: dict[str, object] = {
        "id": "math-9-12",
        "subject": "Mathematics",
        "grade_min": 9,
        "grade_max": 12,
        "mode": "in_person",
        "location": "Springfield",
        "requires_license": True,
    }
    data.update(overrides)
    return Opening.model_validate(data)


def _student(**overrides: object) -> StudentProfile:
    data: dict[str, object] = {
        "id": "student-priya",
        "display_name": "Priya Shah",
        "grade_level": 10,
        "interests": ["Mathematics"],
        "mode": "in_person",
        "location": "Springfield",
    }
    data.update(overrides)
    return StudentProfile.model_validate(data)


def test_licensed_teacher_matches_opening() -> None:
    matches = match_teachers(_opening(), [_teacher()])
    assert len(matches) == 1
    assert matches[0].candidate_id == "teacher-ada"
    assert matches[0].score == 100
    assert "active license disclosed" in matches[0].reasons


def test_expired_license_is_excluded_when_required() -> None:
    matches = match_teachers(_opening(), [_teacher(id="teacher-ben", license_active=False)])
    assert matches == []


def test_wrong_subject_is_excluded() -> None:
    matches = match_teachers(_opening(), [_teacher(subjects=["Biology"])])
    assert matches == []


def test_in_person_requires_the_same_place() -> None:
    matches = match_teachers(_opening(), [_teacher(location="Shelbyville")])
    assert matches == []


def test_remote_pair_ignores_city() -> None:
    opening = _opening(mode="remote", location="Springfield", requires_license=False)
    teacher = _teacher(mode="remote", location="Capital City", license_active=False)
    matches = match_teachers(opening, [teacher])
    assert len(matches) == 1
    assert matches[0].score == 80


def test_hybrid_opening_accepts_in_person_teacher() -> None:
    matches = match_teachers(_opening(mode="hybrid"), [_teacher()])
    assert len(matches) == 1


def test_student_outside_grade_band_is_excluded() -> None:
    program = SchoolProgram(
        id="math-9-12",
        subject="Mathematics",
        grade_min=9,
        grade_max=12,
        mode="in_person",
        location="Springfield",
    )
    matches = match_students(program, [_student(), _student(id="student-leo", grade_level=4)])
    assert [item.candidate_id for item in matches] == ["student-priya"]


def test_grade_band_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        _teacher(grade_min=12, grade_max=9)
