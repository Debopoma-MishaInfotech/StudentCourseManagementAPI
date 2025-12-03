import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models import Student, Course, Enrollment


# Create in-memory SQLite database for testing
@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh database session for each test"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with dependency override"""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ============= ROOT ENDPOINT TESTS =============

def test_read_root(client: TestClient):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


# ============= STUDENT TESTS =============

def test_create_student(client: TestClient):
    """Test creating a new student"""
    response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"
    assert data["age"] == 20
    assert "id" in data
    assert "created_at" in data


def test_create_student_duplicate_email(client: TestClient):
    """Test creating student with duplicate email fails"""
    # Create first student
    client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    # Try to create second student with same email
    response = client.post(
        "/students/",
        json={"name": "Jane Doe", "email": "john@example.com", "age": 22}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_create_student_invalid_email(client: TestClient):
    """Test creating student with invalid email fails"""
    response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "invalid-email", "age": 20}
    )
    assert response.status_code == 422  # Validation error


def test_create_student_invalid_age(client: TestClient):
    """Test creating student with invalid age fails"""
    response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 0}
    )
    assert response.status_code == 422  # Validation error


def test_read_students(client: TestClient):
    """Test getting all students"""
    # Create test students
    client.post("/students/", json={"name": "John Doe", "email": "john@example.com", "age": 20})
    client.post("/students/", json={"name": "Jane Smith", "email": "jane@example.com", "age": 22})
    
    response = client.get("/students/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "John Doe"
    assert data[1]["name"] == "Jane Smith"


def test_read_students_pagination(client: TestClient):
    """Test students pagination"""
    # Create 5 students
    for i in range(5):
        client.post(
            "/students/",
            json={"name": f"Student {i}", "email": f"student{i}@example.com", "age": 20 + i}
        )
    
    # Test skip and limit
    response = client.get("/students/?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Student 2"


def test_read_student(client: TestClient):
    """Test getting a specific student"""
    # Create a student
    create_response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    student_id = create_response.json()["id"]
    
    # Get the student
    response = client.get(f"/students/{student_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student_id
    assert data["name"] == "John Doe"


def test_read_student_not_found(client: TestClient):
    """Test getting non-existent student returns 404"""
    response = client.get("/students/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_student(client: TestClient):
    """Test updating a student"""
    # Create a student
    create_response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    student_id = create_response.json()["id"]
    
    # Update the student
    response = client.put(
        f"/students/{student_id}",
        json={"name": "John Updated", "age": 21}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "John Updated"
    assert data["age"] == 21
    assert data["email"] == "john@example.com"  # Email unchanged


def test_update_student_email(client: TestClient):
    """Test updating student email"""
    # Create a student
    create_response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    student_id = create_response.json()["id"]
    
    # Update email
    response = client.put(
        f"/students/{student_id}",
        json={"email": "newemail@example.com"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newemail@example.com"


def test_update_student_duplicate_email(client: TestClient):
    """Test updating student with duplicate email fails"""
    # Create two students
    client.post("/students/", json={"name": "John", "email": "john@example.com", "age": 20})
    response2 = client.post("/students/", json={"name": "Jane", "email": "jane@example.com", "age": 22})
    student2_id = response2.json()["id"]
    
    # Try to update student2 with student1's email
    response = client.put(
        f"/students/{student2_id}",
        json={"email": "john@example.com"}
    )
    assert response.status_code == 400


def test_update_student_not_found(client: TestClient):
    """Test updating non-existent student returns 404"""
    response = client.put(
        "/students/9999",
        json={"name": "Updated"}
    )
    assert response.status_code == 404


def test_delete_student(client: TestClient):
    """Test deleting a student"""
    # Create a student
    create_response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    student_id = create_response.json()["id"]
    
    # Delete the student
    response = client.delete(f"/students/{student_id}")
    assert response.status_code == 204
    
    # Verify student is deleted
    get_response = client.get(f"/students/{student_id}")
    assert get_response.status_code == 404


def test_delete_student_not_found(client: TestClient):
    """Test deleting non-existent student returns 404"""
    response = client.delete("/students/9999")
    assert response.status_code == 404


# ============= COURSE TESTS =============

def test_create_course(client: TestClient):
    """Test creating a new course"""
    response = client.post(
        "/courses/",
        json={
            "title": "Introduction to Python",
            "description": "Learn Python basics",
            "credits": 3,
            "instructor": "Dr. Smith"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Introduction to Python"
    assert data["credits"] == 3
    assert "id" in data


def test_create_course_minimal(client: TestClient):
    """Test creating course with minimal data"""
    response = client.post(
        "/courses/",
        json={
            "title": "Data Structures",
            "credits": 4,
            "instructor": "Dr. Jones"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["description"] is None


def test_create_course_invalid_credits(client: TestClient):
    """Test creating course with invalid credits fails"""
    response = client.post(
        "/courses/",
        json={
            "title": "Invalid Course",
            "credits": 0,  # Invalid: must be >= 1
            "instructor": "Dr. Smith"
        }
    )
    assert response.status_code == 422


def test_read_courses(client: TestClient):
    """Test getting all courses"""
    # Create test courses
    client.post("/courses/", json={"title": "Python 101", "credits": 3, "instructor": "Dr. A"})
    client.post("/courses/", json={"title": "Java 101", "credits": 4, "instructor": "Dr. B"})
    
    response = client.get("/courses/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_read_course(client: TestClient):
    """Test getting a specific course"""
    # Create a course
    create_response = client.post(
        "/courses/",
        json={"title": "Python 101", "credits": 3, "instructor": "Dr. Smith"}
    )
    course_id = create_response.json()["id"]
    
    # Get the course
    response = client.get(f"/courses/{course_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == course_id
    assert data["title"] == "Python 101"


def test_read_course_not_found(client: TestClient):
    """Test getting non-existent course returns 404"""
    response = client.get("/courses/9999")
    assert response.status_code == 404


def test_update_course(client: TestClient):
    """Test updating a course"""
    # Create a course
    create_response = client.post(
        "/courses/",
        json={"title": "Python 101", "credits": 3, "instructor": "Dr. Smith"}
    )
    course_id = create_response.json()["id"]
    
    # Update the course
    response = client.put(
        f"/courses/{course_id}",
        json={"title": "Advanced Python", "credits": 4}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Advanced Python"
    assert data["credits"] == 4


def test_update_course_not_found(client: TestClient):
    """Test updating non-existent course returns 404"""
    response = client.put(
        "/courses/9999",
        json={"title": "Updated"}
    )
    assert response.status_code == 404


def test_delete_course(client: TestClient):
    """Test deleting a course"""
    # Create a course
    create_response = client.post(
        "/courses/",
        json={"title": "Python 101", "credits": 3, "instructor": "Dr. Smith"}
    )
    course_id = create_response.json()["id"]
    
    # Delete the course
    response = client.delete(f"/courses/{course_id}")
    assert response.status_code == 204
    
    # Verify course is deleted
    get_response = client.get(f"/courses/{course_id}")
    assert get_response.status_code == 404


def test_delete_course_not_found(client: TestClient):
    """Test deleting non-existent course returns 404"""
    response = client.delete("/courses/9999")
    assert response.status_code == 404


# ============= ENROLLMENT TESTS =============

def test_create_enrollment(client: TestClient):
    """Test enrolling a student in a course"""
    # Create student and course
    student_response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    course_response = client.post(
        "/courses/",
        json={"title": "Python 101", "credits": 3, "instructor": "Dr. Smith"}
    )
    
    student_id = student_response.json()["id"]
    course_id = course_response.json()["id"]
    
    # Create enrollment
    response = client.post(
        "/enrollments/",
        json={"student_id": student_id, "course_id": course_id, "grade": "A"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["student_id"] == student_id
    assert data["course_id"] == course_id
    assert data["grade"] == "A"
    assert "id" in data


def test_create_enrollment_no_grade(client: TestClient):
    """Test creating enrollment without grade"""
    # Create student and course
    student_response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    course_response = client.post(
        "/courses/",
        json={"title": "Python 101", "credits": 3, "instructor": "Dr. Smith"}
    )
    
    student_id = student_response.json()["id"]
    course_id = course_response.json()["id"]
    
    # Create enrollment without grade
    response = client.post(
        "/enrollments/",
        json={"student_id": student_id, "course_id": course_id}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["grade"] is None


def test_create_enrollment_student_not_found(client: TestClient):
    """Test enrollment with non-existent student fails"""
    # Create only course
    course_response = client.post(
        "/courses/",
        json={"title": "Python 101", "credits": 3, "instructor": "Dr. Smith"}
    )
    course_id = course_response.json()["id"]
    
    response = client.post(
        "/enrollments/",
        json={"student_id": 9999, "course_id": course_id}
    )
    assert response.status_code == 404
    assert "student" in response.json()["detail"].lower()


def test_create_enrollment_course_not_found(client: TestClient):
    """Test enrollment with non-existent course fails"""
    # Create only student
    student_response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    student_id = student_response.json()["id"]
    
    response = client.post(
        "/enrollments/",
        json={"student_id": student_id, "course_id": 9999}
    )
    assert response.status_code == 404
    assert "course" in response.json()["detail"].lower()


def test_create_enrollment_duplicate(client: TestClient):
    """Test duplicate enrollment fails"""
    # Create student and course
    student_response = client.post(
        "/students/",
        json={"name": "John Doe", "email": "john@example.com", "age": 20}
    )
    course_response = client.post(
        "/courses/",
        json={"title": "Python 101", "credits": 3, "instructor": "Dr. Smith"}
    )
    
    student_id = student_response.json()["id"]
    course_id = course_response.json()["id"]
    
    # Create first enrollment
    client.post(
        "/enrollments/",
        json={"student_id": student_id, "course_id": course_id}
    )
    
    # Try to create duplicate
    response = client.post(
        "/enrollments/",
        json={"student_id": student_id, "course_id": course_id}
    )
    assert response.status_code == 400
    assert "already enrolled" in response.json()["detail"].lower()


def test_read_enrollments(client: TestClient):
    """Test getting all enrollments"""
    # Create students, courses, and enrollments
    student1 = client.post("/students/", json={"name": "John", "email": "john@example.com", "age": 20}).json()
    student2 = client.post("/students/", json={"name": "Jane", "email": "jane@example.com", "age": 22}).json()
    course1 = client.post("/courses/", json={"title": "Python", "credits": 3, "instructor": "Dr. A"}).json()
    course2 = client.post("/courses/", json={"title": "Java", "credits": 4, "instructor": "Dr. B"}).json()
    
    client.post("/enrollments/", json={"student_id": student1["id"], "course_id": course1["id"]})
    client.post("/enrollments/", json={"student_id": student2["id"], "course_id": course2["id"]})
    
    response = client.get("/enrollments/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_read_enrollment(client: TestClient):
    """Test getting a specific enrollment"""
    # Create enrollment
    student = client.post("/students/", json={"name": "John", "email": "john@example.com", "age": 20}).json()
    course = client.post("/courses/", json={"title": "Python", "credits": 3, "instructor": "Dr. A"}).json()
    enrollment = client.post(
        "/enrollments/",
        json={"student_id": student["id"], "course_id": course["id"], "grade": "A"}
    ).json()
    
    response = client.get(f"/enrollments/{enrollment['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == enrollment["id"]
    assert data["grade"] == "A"


def test_read_enrollment_not_found(client: TestClient):
    """Test getting non-existent enrollment returns 404"""
    response = client.get("/enrollments/9999")
    assert response.status_code == 404


def test_read_student_enrollments(client: TestClient):
    """Test getting all enrollments for a student"""
    # Create student and multiple courses
    student = client.post("/students/", json={"name": "John", "email": "john@example.com", "age": 20}).json()
    course1 = client.post("/courses/", json={"title": "Python", "credits": 3, "instructor": "Dr. A"}).json()
    course2 = client.post("/courses/", json={"title": "Java", "credits": 4, "instructor": "Dr. B"}).json()
    
    # Enroll student in both courses
    client.post("/enrollments/", json={"student_id": student["id"], "course_id": course1["id"]})
    client.post("/enrollments/", json={"student_id": student["id"], "course_id": course2["id"]})
    
    response = client.get(f"/students/{student['id']}/enrollments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_read_student_enrollments_not_found(client: TestClient):
    """Test getting enrollments for non-existent student returns 404"""
    response = client.get("/students/9999/enrollments")
    assert response.status_code == 404


def test_read_course_enrollments(client: TestClient):
    """Test getting all enrollments for a course"""
    # Create course and multiple students
    course = client.post("/courses/", json={"title": "Python", "credits": 3, "instructor": "Dr. A"}).json()
    student1 = client.post("/students/", json={"name": "John", "email": "john@example.com", "age": 20}).json()
    student2 = client.post("/students/", json={"name": "Jane", "email": "jane@example.com", "age": 22}).json()
    
    # Enroll both students in course
    client.post("/enrollments/", json={"student_id": student1["id"], "course_id": course["id"]})
    client.post("/enrollments/", json={"student_id": student2["id"], "course_id": course["id"]})
    
    response = client.get(f"/courses/{course['id']}/enrollments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_read_course_enrollments_not_found(client: TestClient):
    """Test getting enrollments for non-existent course returns 404"""
    response = client.get("/courses/9999/enrollments")
    assert response.status_code == 404


def test_update_enrollment(client: TestClient):
    """Test updating an enrollment grade"""
    # Create enrollment
    student = client.post("/students/", json={"name": "John", "email": "john@example.com", "age": 20}).json()
    course = client.post("/courses/", json={"title": "Python", "credits": 3, "instructor": "Dr. A"}).json()
    enrollment = client.post(
        "/enrollments/",
        json={"student_id": student["id"], "course_id": course["id"]}
    ).json()
    
    # Update grade
    response = client.put(
        f"/enrollments/{enrollment['id']}",
        json={"grade": "A+"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grade"] == "A+"


def test_update_enrollment_not_found(client: TestClient):
    """Test updating non-existent enrollment returns 404"""
    response = client.put(
        "/enrollments/9999",
        json={"grade": "A"}
    )
    assert response.status_code == 404


def test_delete_enrollment(client: TestClient):
    """Test deleting an enrollment"""
    # Create enrollment
    student = client.post("/students/", json={"name": "John", "email": "john@example.com", "age": 20}).json()
    course = client.post("/courses/", json={"title": "Python", "credits": 3, "instructor": "Dr. A"}).json()
    enrollment = client.post(
        "/enrollments/",
        json={"student_id": student["id"], "course_id": course["id"]}
    ).json()
    
    # Delete enrollment
    response = client.delete(f"/enrollments/{enrollment['id']}")
    assert response.status_code == 204
    
    # Verify deletion
    get_response = client.get(f"/enrollments/{enrollment['id']}")
    assert get_response.status_code == 404


def test_delete_enrollment_not_found(client: TestClient):
    """Test deleting non-existent enrollment returns 404"""
    response = client.delete("/enrollments/9999")
    assert response.status_code == 404
