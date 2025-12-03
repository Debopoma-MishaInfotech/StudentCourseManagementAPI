from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import List
from datetime import datetime
import logging
import sys
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from database import create_db_and_tables, get_session
from models import Student, Course, Enrollment
from schemas import (
    StudentCreate, StudentUpdate, StudentResponse,
    CourseCreate, CourseUpdate, CourseResponse,
    EnrollmentCreate, EnrollmentUpdate, EnrollmentResponse
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api.log')
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Student Course Management API",
    description="A comprehensive API for managing students, courses, and enrollments",
    version="1.0.0"
)


# Global exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database-related errors"""
    logger.error(f"Database error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "A database error occurred. Please try again later."}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please contact support."}
    )


@app.on_event("startup")
def on_startup():
    """Create database tables on startup"""
    try:
        logger.info("Starting application...")
        create_db_and_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)
        raise


@app.get("/", tags=["Root"])
async def read_root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to Student Course Management API",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# ============= STUDENT ENDPOINTS =============

@app.post("/students/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED, tags=["Students"])
async def create_student(student: StudentCreate, session: Session = Depends(get_session)):
    """Create a new student"""
    try:
        logger.info(f"Creating student with email: {student.email}")
        
        # Check if email already exists
        existing_student = session.exec(select(Student).where(Student.email == student.email)).first()
        if existing_student:
            logger.warning(f"Attempted to create student with existing email: {student.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        db_student = Student(**student.model_dump())
        session.add(db_student)
        session.commit()
        session.refresh(db_student)
        
        logger.info(f"Student created successfully with ID: {db_student.id}")
        return db_student
    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error(f"Integrity error creating student: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create student. Email may already exist."
        )
    except Exception as e:
        logger.error(f"Error creating student: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the student"
        )


@app.get("/students/", response_model=List[StudentResponse], tags=["Students"])
async def read_students(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """Get all students with pagination"""
    try:
        logger.info(f"Fetching students with skip={skip}, limit={limit}")
        students = session.exec(select(Student).offset(skip).limit(limit)).all()
        logger.info(f"Retrieved {len(students)} students")
        return students
    except Exception as e:
        logger.error(f"Error fetching students: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching students"
        )


@app.get("/students/{student_id}", response_model=StudentResponse, tags=["Students"])
async def read_student(student_id: int, session: Session = Depends(get_session)):
    """Get a specific student by ID"""
    try:
        logger.info(f"Fetching student with ID: {student_id}")
        student = session.get(Student, student_id)
        if not student:
            logger.warning(f"Student not found with ID: {student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        logger.info(f"Student found: {student.name}")
        return student
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching student {student_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the student"
        )


@app.put("/students/{student_id}", response_model=StudentResponse, tags=["Students"])
async def update_student(student_id: int, student_update: StudentUpdate, session: Session = Depends(get_session)):
    """Update a student's information"""
    try:
        logger.info(f"Updating student with ID: {student_id}")
        db_student = session.get(Student, student_id)
        if not db_student:
            logger.warning(f"Student not found for update with ID: {student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Check email uniqueness if email is being updated
        if student_update.email and student_update.email != db_student.email:
            existing_student = session.exec(select(Student).where(Student.email == student_update.email)).first()
            if existing_student:
                logger.warning(f"Attempted to update with existing email: {student_update.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
        
        # Update only provided fields
        update_data = student_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_student, key, value)
        
        db_student.updated_at = datetime.utcnow()
        session.add(db_student)
        session.commit()
        session.refresh(db_student)
        
        logger.info(f"Student updated successfully: {db_student.id}")
        return db_student
    except HTTPException:
        raise
    except IntegrityError as e:
        logger.error(f"Integrity error updating student: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update student. Email may already exist."
        )
    except Exception as e:
        logger.error(f"Error updating student {student_id}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the student"
        )


@app.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Students"])
async def delete_student(student_id: int, session: Session = Depends(get_session)):
    """Delete a student"""
    try:
        logger.info(f"Deleting student with ID: {student_id}")
        student = session.get(Student, student_id)
        if not student:
            logger.warning(f"Student not found for deletion with ID: {student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        session.delete(student)
        session.commit()
        logger.info(f"Student deleted successfully: {student_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting student {student_id}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the student"
        )


# ============= COURSE ENDPOINTS =============

@app.post("/courses/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED, tags=["Courses"])
async def create_course(course: CourseCreate, session: Session = Depends(get_session)):
    """Create a new course"""
    try:
        logger.info(f"Creating course: {course.title}")
        db_course = Course(**course.model_dump())
        session.add(db_course)
        session.commit()
        session.refresh(db_course)
        logger.info(f"Course created successfully with ID: {db_course.id}")
        return db_course
    except Exception as e:
        logger.error(f"Error creating course: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the course"
        )


@app.get("/courses/", response_model=List[CourseResponse], tags=["Courses"])
async def read_courses(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """Get all courses with pagination"""
    try:
        logger.info(f"Fetching courses with skip={skip}, limit={limit}")
        courses = session.exec(select(Course).offset(skip).limit(limit)).all()
        logger.info(f"Retrieved {len(courses)} courses")
        return courses
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching courses"
        )


@app.get("/courses/{course_id}", response_model=CourseResponse, tags=["Courses"])
async def read_course(course_id: int, session: Session = Depends(get_session)):
    """Get a specific course by ID"""
    try:
        logger.info(f"Fetching course with ID: {course_id}")
        course = session.get(Course, course_id)
        if not course:
            logger.warning(f"Course not found with ID: {course_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        logger.info(f"Course found: {course.title}")
        return course
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching course {course_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the course"
        )


@app.put("/courses/{course_id}", response_model=CourseResponse, tags=["Courses"])
async def update_course(course_id: int, course_update: CourseUpdate, session: Session = Depends(get_session)):
    """Update a course's information"""
    try:
        logger.info(f"Updating course with ID: {course_id}")
        db_course = session.get(Course, course_id)
        if not db_course:
            logger.warning(f"Course not found for update with ID: {course_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Update only provided fields
        update_data = course_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_course, key, value)
        
        db_course.updated_at = datetime.utcnow()
        session.add(db_course)
        session.commit()
        session.refresh(db_course)
        
        logger.info(f"Course updated successfully: {db_course.id}")
        return db_course
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating course {course_id}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the course"
        )


@app.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Courses"])
async def delete_course(course_id: int, session: Session = Depends(get_session)):
    """Delete a course"""
    try:
        logger.info(f"Deleting course with ID: {course_id}")
        course = session.get(Course, course_id)
        if not course:
            logger.warning(f"Course not found for deletion with ID: {course_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        session.delete(course)
        session.commit()
        logger.info(f"Course deleted successfully: {course_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting course {course_id}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the course"
        )


# ============= ENROLLMENT ENDPOINTS =============

@app.post("/enrollments/", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED, tags=["Enrollments"])
async def create_enrollment(enrollment: EnrollmentCreate, session: Session = Depends(get_session)):
    """Enroll a student in a course"""
    try:
        logger.info(f"Creating enrollment for student {enrollment.student_id} in course {enrollment.course_id}")
        
        # Verify student exists
        student = session.get(Student, enrollment.student_id)
        if not student:
            logger.warning(f"Student not found: {enrollment.student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Verify course exists
        course = session.get(Course, enrollment.course_id)
        if not course:
            logger.warning(f"Course not found: {enrollment.course_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        # Check if already enrolled
        existing_enrollment = session.exec(
            select(Enrollment).where(
                Enrollment.student_id == enrollment.student_id,
                Enrollment.course_id == enrollment.course_id
            )
        ).first()
        if existing_enrollment:
            logger.warning(f"Student {enrollment.student_id} already enrolled in course {enrollment.course_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student already enrolled in this course"
            )
        
        db_enrollment = Enrollment(**enrollment.model_dump())
        session.add(db_enrollment)
        session.commit()
        session.refresh(db_enrollment)
        
        logger.info(f"Enrollment created successfully with ID: {db_enrollment.id}")
        return db_enrollment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating enrollment: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the enrollment"
        )


@app.get("/enrollments/", response_model=List[EnrollmentResponse], tags=["Enrollments"])
async def read_enrollments(skip: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    """Get all enrollments with pagination"""
    try:
        logger.info(f"Fetching enrollments with skip={skip}, limit={limit}")
        enrollments = session.exec(select(Enrollment).offset(skip).limit(limit)).all()
        logger.info(f"Retrieved {len(enrollments)} enrollments")
        return enrollments
    except Exception as e:
        logger.error(f"Error fetching enrollments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching enrollments"
        )


@app.get("/enrollments/{enrollment_id}", response_model=EnrollmentResponse, tags=["Enrollments"])
async def read_enrollment(enrollment_id: int, session: Session = Depends(get_session)):
    """Get a specific enrollment by ID"""
    try:
        logger.info(f"Fetching enrollment with ID: {enrollment_id}")
        enrollment = session.get(Enrollment, enrollment_id)
        if not enrollment:
            logger.warning(f"Enrollment not found with ID: {enrollment_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found"
            )
        return enrollment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching enrollment {enrollment_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the enrollment"
        )


@app.get("/students/{student_id}/enrollments", response_model=List[EnrollmentResponse], tags=["Enrollments"])
async def read_student_enrollments(student_id: int, session: Session = Depends(get_session)):
    """Get all enrollments for a specific student"""
    try:
        logger.info(f"Fetching enrollments for student: {student_id}")
        student = session.get(Student, student_id)
        if not student:
            logger.warning(f"Student not found: {student_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        enrollments = session.exec(select(Enrollment).where(Enrollment.student_id == student_id)).all()
        logger.info(f"Retrieved {len(enrollments)} enrollments for student {student_id}")
        return enrollments
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching student enrollments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching student enrollments"
        )


@app.get("/courses/{course_id}/enrollments", response_model=List[EnrollmentResponse], tags=["Enrollments"])
async def read_course_enrollments(course_id: int, session: Session = Depends(get_session)):
    """Get all enrollments for a specific course"""
    try:
        logger.info(f"Fetching enrollments for course: {course_id}")
        course = session.get(Course, course_id)
        if not course:
            logger.warning(f"Course not found: {course_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
        
        enrollments = session.exec(select(Enrollment).where(Enrollment.course_id == course_id)).all()
        logger.info(f"Retrieved {len(enrollments)} enrollments for course {course_id}")
        return enrollments
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching course enrollments: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching course enrollments"
        )


@app.put("/enrollments/{enrollment_id}", response_model=EnrollmentResponse, tags=["Enrollments"])
async def update_enrollment(enrollment_id: int, enrollment_update: EnrollmentUpdate, session: Session = Depends(get_session)):
    """Update an enrollment (typically to update grade)"""
    try:
        logger.info(f"Updating enrollment with ID: {enrollment_id}")
        db_enrollment = session.get(Enrollment, enrollment_id)
        if not db_enrollment:
            logger.warning(f"Enrollment not found for update with ID: {enrollment_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found"
            )
        
        # Update only provided fields
        update_data = enrollment_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_enrollment, key, value)
        
        session.add(db_enrollment)
        session.commit()
        session.refresh(db_enrollment)
        
        logger.info(f"Enrollment updated successfully: {enrollment_id}")
        return db_enrollment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating enrollment {enrollment_id}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the enrollment"
        )


@app.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Enrollments"])
async def delete_enrollment(enrollment_id: int, session: Session = Depends(get_session)):
    """Delete an enrollment (unenroll a student from a course)"""
    try:
        logger.info(f"Deleting enrollment with ID: {enrollment_id}")
        enrollment = session.get(Enrollment, enrollment_id)
        if not enrollment:
            logger.warning(f"Enrollment not found for deletion with ID: {enrollment_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found"
            )
        
        session.delete(enrollment)
        session.commit()
        logger.info(f"Enrollment deleted successfully: {enrollment_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting enrollment {enrollment_id}: {str(e)}", exc_info=True)
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the enrollment"
        )
