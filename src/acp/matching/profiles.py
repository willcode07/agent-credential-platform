"""Launch-market profiles.

These are the attributes a matcher is allowed to see after selective
disclosure. They are not the underlying credentials.

# OPEN QUESTION: the grade scale is a US-style 1–12 integer. Other school
# systems, and a later HR product, need a different notion of "level."
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Mode = Literal["in_person", "remote", "hybrid"]


def _check_grade_band(grade_min: int, grade_max: int) -> None:
    if not 1 <= grade_min <= 12 or not 1 <= grade_max <= 12:
        raise ValueError("grades must be between 1 and 12")
    if grade_min > grade_max:
        raise ValueError("grade_min cannot exceed grade_max")


class TeacherProfile(BaseModel):
    """A teacher as presented to the matcher. Built from revealed claims."""

    id: str
    display_name: str
    subjects: list[str] = Field(min_length=1)
    grade_min: int
    grade_max: int
    mode: Mode
    location: str
    license_active: bool

    @model_validator(mode="after")
    def grades_in_range(self) -> "TeacherProfile":
        _check_grade_band(self.grade_min, self.grade_max)
        return self


class StudentProfile(BaseModel):
    """A student as presented to the matcher. Built from revealed claims."""

    id: str
    display_name: str
    grade_level: int = Field(ge=1, le=12)
    interests: list[str] = Field(min_length=1)
    mode: Mode
    location: str


class SchoolProgram(BaseModel):
    """Something a school offers students, such as a subject in a grade band."""

    id: str
    subject: str
    grade_min: int
    grade_max: int
    mode: Mode
    location: str

    @model_validator(mode="after")
    def grades_in_range(self) -> "SchoolProgram":
        _check_grade_band(self.grade_min, self.grade_max)
        return self


class Opening(SchoolProgram):
    """A staffing need. Same shape as a program, plus a license rule."""

    requires_license: bool = True


class SchoolProfile(BaseModel):
    """A school and the openings and programs it wants matched."""

    id: str
    name: str
    location: str
    openings: list[Opening]
    programs: list[SchoolProgram]


class Match(BaseModel):
    """One scored pairing. ``score`` is an explanatory rank, not a probability."""

    candidate_id: str
    candidate_role: Literal["teacher", "student"]
    target_id: str
    score: int
    reasons: list[str]
