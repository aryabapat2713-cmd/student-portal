"""
EWB Backend Development Internship Assignment
Project: Student Management Portal with Integrated Local AI Data Assistant
Author: Intern (Batch 1)
"""

from fastapi import FastAPI, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import ollama

# ==========================================
# 1. DATABASE CONFIGURATION & INITIALIZATION
# ==========================================

# Local SQLite engine setup specific to EWB tracker schema
SQLITE_FILE_URL = "sqlite:///./ewb_records.db"

db_engine = create_engine(SQLITE_FILE_URL, connect_args={"check_same_thread": False})
SessionDB = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
BaseModelFactory = declarative_base()

def get_database_connection():
    """Context manager dependency injected into FastAPI endpoints"""
    active_session = SessionDB()
    try:
        yield active_session
    finally:
        active_session.close()


# ==========================================
# 2. SQLALCHEMY ORM DATA STORAGE DEFINITION
# ==========================================

class StudentProfile(BaseModelFactory):
    __tablename__ = "internship_students"

    id_key = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(String, nullable=False)
    birth_date = Column(String, nullable=False)
    email_address = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=False)
    assigned_course = Column(String, nullable=True)
    residential_address = Column(String, nullable=True)
    joining_date = Column(String, nullable=True)


# Generate the local SQLite schema file instantly on app instantiation
BaseModelFactory.metadata.create_all(bind=db_engine)


# ==========================================
# 3. PYDANTIC SCHEMAS FOR DATA VALIDATION
# ==========================================

class NewStudentInput(BaseModel):
    full_name: str
    birth_date: str
    email_address: EmailStr
    phone_number: str
    assigned_course: Optional[str] = None
    residential_address: Optional[str] = None
    joining_date: Optional[str] = None

class ModifyStudentInput(BaseModel):
    full_name: Optional[str] = None
    birth_date: Optional[str] = None
    email_address: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    assigned_course: Optional[str] = None
    residential_address: Optional[str] = None
    joining_date: Optional[str] = None

class StudentOutputView(NewStudentInput):
    id_key: int

    class Config:
        from_attributes = True


# ==========================================
# 4. FASTAPI APP ROUTING & CORE CRUD OPERATIONS
# ==========================================

app = FastAPI(
    title="EWB Student Database Portal",
    description="Python Backend Assignment Solution containing Core CRUD + AI Model Queries",
    version="0.8.2"
)


@app.post("/students", response_model=StudentOutputView, status_code=status.HTTP_201_CREATED)
def register_new_student(payload: NewStudentInput, connection: Session = Depends(get_database_connection)):
    """CREATE Operation: Evaluates duplicates and registers a record."""
    duplicate_check = connection.query(StudentProfile).filter(StudentProfile.email_address == payload.email_address).first()
    if duplicate_check:
        raise HTTPException(status_code=400, detail="Registration error: This email address is already taken.")
    
    fresh_entry = StudentProfile(
        full_name=payload.full_name,
        birth_date=payload.birth_date,
        email_address=payload.email_address,
        phone_number=payload.phone_number,
        assigned_course=payload.assigned_course,
        residential_address=payload.residential_address,
        joining_date=payload.joining_date
    )
    
    connection.add(fresh_entry)
    connection.commit()
    connection.refresh(fresh_entry)
    return fresh_entry


@app.get("/students", response_model=List[StudentOutputView])
def fetch_all_or_filter_students(course_filter: Optional[str] = Query(None, alias="course"), connection: Session = Depends(get_database_connection)):
    """READ Operation: Fetches full array or scopes by target course."""
    base_lookup = connection.query(StudentProfile)
    if course_filter:
        base_lookup = base_lookup.filter(StudentProfile.assigned_course.ilontains(course_filter))
    return base_lookup.all()


@app.get("/students/{student_id}", response_model=StudentOutputView)
def retrieve_single_student_by_id(student_id: int, connection: Session = Depends(get_database_connection)):
    """READ Operation: Pulls single record match or surfaces clear 404 error."""
    matched_entry = connection.query(StudentProfile).filter(StudentProfile.id_key == student_id).first()
    if not matched_entry:
        raise HTTPException(status_code=404, detail=f"Database missing record for Student ID {student_id}")
    return matched_entry


@app.patch("/students/{student_id}", response_model=StudentOutputView)
def modify_existing_student_record(student_id: int, incoming_data: ModifyStudentInput, connection: Session = Depends(get_database_connection)):
    """UPDATE Operation: Evaluates structural field items and patches targeted parameters."""
    record_query = connection.query(StudentProfile).filter(StudentProfile.id_key == student_id)
    target_student = record_query.first()
    
    if not target_student:
        raise HTTPException(status_code=404, detail=f"Cannot alter record: ID {student_id} not found.")
    
    clean_updates = incoming_data.model_dump(exclude_unset=True)
    
    if "email_address" in clean_updates and clean_updates["email_address"] != target_student.email_address:
        email_clash_check = connection.query(StudentProfile).filter(StudentProfile.email_address == clean_updates["email_address"]).first()
        if email_clash_check:
            raise HTTPException(status_code=400, detail="Conflict: Email already tied to a separate student record.")
            
    record_query.update(clean_updates, synchronize_session=False)
    connection.commit()
    connection.refresh(target_student)
    return target_student


@app.delete("/students/{student_id}", status_code=status.HTTP_200_OK)
def remove_student_from_system(student_id: int, connection: Session = Depends(get_database_connection)):
    """DELETE Operation: Wipes structural student records entirely from persistent storage."""
    record_query = connection.query(StudentProfile).filter(StudentProfile.id_key == student_id)
    target_student = record_query.first()
    
    if not target_student:
        raise HTTPException(status_code=404, detail=f"Cannot delete record: Student matching ID {student_id} does not exist.")
        
    record_query.delete(synchronize_session=False)
    connection.commit()
    return {"status_alert": f"Success. Profile linked to ID {student_id} was removed from the server database."}


# ==========================================
# 5. OPTIONAL EXTRA ASSIGNMENT: OLLAMA INTEGRATION
# ==========================================

@app.post("/students/ai-query-engine")
def query_local_ollama_model(user_question: str = Query(..., description="Ask questions about database entries directly"), connection: Session = Depends(get_database_connection)):
    """
    BONUS LOCAL AI ASSIGNMENT: 
    Queries structural profiles, strips confidential attributes, 
    and uses llama3.2:1b locally to answer contextual text entries.
    """
    all_records = connection.query(StudentProfile).all()
    if not all_records:
        return {"ai_insight": "The database storage is completely empty. Add entries first."}
        
    # Build text baseline context blocks safely
    raw_context_block = "ACTIVE STUDENT ROSTER REGISTRY:\n"
    for item in all_records:
        raw_context_block += f"* ID Num: {item.id_key} | Full Name: {item.full_name} | Program Study: {item.assigned_course or 'Unassigned'} | Date of Birth: {item.birth_date}\n"
        
    # Keep behavior locked explicitly inside safe system constraints
    guiding_rules = (
        "Contextual Query Framework Protocol Instructions:\n"
        "You are a backend system assistant tool processing specialized classroom data rosters.\n"
        "Answer the user prompt cleanly by relying ONLY on the system registry notes compiled below. "
        "Keep responses simple, precise, and completely natural to read.\n\n"
        f"Data Baseline Context:\n{raw_context_block}"
    )
    
    try:
        llm_response = ollama.generate(
            model='llama3.2:1b',
            prompt=f"{guiding_rules}\n\nUser Question: {user_question}"
        )
        return {
            "submitted_question": user_question,
            "ai_insight": llm_response['response'].strip()
        }
    except Exception as network_error:
        raise HTTPException(
            status_code=502,
            detail=f"Local engine connectivity fault. Check Ollama daemon logs. Trace: {str(network_error)}"
        )
 
