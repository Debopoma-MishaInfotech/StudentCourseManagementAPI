from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# Student Schemas
class StudentBase(BaseModel):
    """Base schema for student with common attributes"""
    name: str = Field(..., min_length=1, max_length=100, description="Student's full name")
    email: EmailStr = Field(..., description="Student's email address")
    age: int = Field(..., ge=1, le=150, description="Student's age")


class StudentCreate(StudentBase):
    """Schema for creating a new student"""
    pass


class StudentUpdate(BaseModel):
    """Schema for updating a student (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    age: Optional[int] = Field(None, ge=1, le=150)


class StudentResponse(StudentBase):
    """Schema for student response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Course Schemas
class CourseBase(BaseModel):
    """Base schema for course with common attributes"""
    title: str = Field(..., min_length=1, max_length=200, description="Course title")
    description: Optional[str] = Field(None, max_length=1000, description="Course description")
    credits: int = Field(..., ge=1, le=10, description="Number of credits")
    instructor: str = Field(..., min_length=1, max_length=100, description="Instructor name")


class CourseCreate(CourseBase):
    """Schema for creating a new course"""
    pass


class CourseUpdate(BaseModel):
    """Schema for updating a course (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    credits: Optional[int] = Field(None, ge=1, le=10)
    instructor: Optional[str] = Field(None, min_length=1, max_length=100)


class CourseResponse(CourseBase):
    """Schema for course response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Enrollment Schemas
class EnrollmentBase(BaseModel):
    """Base schema for enrollment with common attributes"""
    student_id: int = Field(..., description="Student ID")
    course_id: int = Field(..., description="Course ID")
    grade: Optional[str] = Field(None, max_length=2, description="Grade (e.g., A, B+, C)")


class EnrollmentCreate(EnrollmentBase):
    """Schema for creating a new enrollment"""
    pass


class EnrollmentUpdate(BaseModel):
    """Schema for updating an enrollment"""
    grade: Optional[str] = Field(None, max_length=2, description="Grade (e.g., A, B+, C)")


class EnrollmentResponse(EnrollmentBase):
    """Schema for enrollment response"""
    id: int
    enrollment_date: datetime

    class Config:
        from_attributes = True
