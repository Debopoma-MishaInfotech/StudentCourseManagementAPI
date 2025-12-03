from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Student(SQLModel, table=True):
    """Student model for database"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=100)
    email: str = Field(unique=True, index=True)
    age: int = Field(ge=1, le=150)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Course(SQLModel, table=True):
    """Course model for database"""
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    credits: int = Field(ge=1, le=10)
    instructor: str = Field(min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Enrollment(SQLModel, table=True):
    """Enrollment model linking students and courses"""
    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id")
    course_id: int = Field(foreign_key="course.id")
    grade: Optional[str] = Field(default=None, max_length=2)
    enrollment_date: datetime = Field(default_factory=datetime.utcnow)
