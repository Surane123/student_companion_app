# app.py - Simple Student Companion App
# Run: uvicorn app:app --reload

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from textblob import TextBlob
import re
import random

app = FastAPI(title="Student Companion App")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Define request models
from datetime import datetime
from typing import List, Optional

class Note(BaseModel):
    note: str
    category: str
    priority: Optional[int] = 1  # 1-3 priority levels

class MoodText(BaseModel):
    text: str

class Task(BaseModel):
    title: str
    description: str
    due_date: str
    subject: str
    priority: int  # 1-3 priority levels
    status: str = "pending"  # pending, in-progress, completed

class StudySession(BaseModel):
    subject: str
    duration: int  # in minutes
    goals: List[str]
    completed_goals: List[str] = []

class TaskUpdate(BaseModel):
    status: str

# Enhanced storage with timestamps
reminders = []  # [{"note": str, "category": str, "priority": int, "timestamp": datetime, "keywords": List[str]}]
moods = []     # [{"text": str, "mood": str, "timestamp": datetime, "tip": str}]
tasks = []     # [{"id": str, "title": str, "description": str, "due_date": str, "subject": str, "priority": int, "status": str, "timestamp": datetime}]
study_sessions = []  # [{"subject": str, "duration": int, "goals": List[str], "completed_goals": List[str], "timestamp": datetime}]

# Study subjects and categories
SUBJECTS = [
    "Mathematics", "Physics", "Chemistry", "Biology",
    "History", "Literature", "Computer Science",
    "Economics", "Languages", "Other"
]

NOTE_CATEGORIES = [
    "Lecture Notes", "Study Tips", "Research Ideas",
    "Questions", "Homework", "Project Ideas", "Other"
]

# Study tips database
STUDY_TIPS = {
    "focus": [
        "Find a quiet study space",
        "Use the Pomodoro Technique (25 min study, 5 min break)",
        "Put your phone on silent mode",
        "Take regular short breaks",
    ],
    "memory": [
        "Create mind maps for complex topics",
        "Teach the concept to someone else",
        "Use spaced repetition technique",
        "Write summary notes after each study session",
    ],
    "motivation": [
        "Set specific, achievable goals",
        "Reward yourself after completing tasks",
        "Study with a friend or study group",
        "Track your progress regularly",
    ]
}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/add_note/")
async def add_note(note_data: Note):
    """Extract keywords from a note and create a reminder with category and priority"""
    if not note_data.note.strip():
        raise HTTPException(status_code=400, detail="Note cannot be empty")
    
    if note_data.category not in NOTE_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Choose from: {', '.join(NOTE_CATEGORIES)}")

    # Enhanced keyword extraction with academic focus
    keywords = [word.lower() for word in re.findall(r'\b\w+\b', note_data.note) 
               if len(word) > 3 and word.lower() not in ['have', 'that', 'with', 'this']]
    
    reminder = {
        "note": note_data.note,
        "keywords": keywords,
        "category": note_data.category,
        "priority": note_data.priority,
        "timestamp": datetime.now().isoformat()
    }
    reminders.append(reminder)
    return {
        "status": "Note added ✅",
        "keywords": keywords,
        "note": note_data.note,
        "category": note_data.category,
        "priority": note_data.priority
    }

@app.post("/mood_check/")
async def mood_check(mood_data: MoodText):
    """Detect student mood and provide personalized study tips"""
    if not mood_data.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    analysis = TextBlob(mood_data.text)
    polarity = analysis.sentiment.polarity
    subjectivity = analysis.sentiment.subjectivity

    # Enhanced mood analysis with specific study tips
    if polarity > 0.2:
        mood = "😊 Happy"
        if subjectivity > 0.5:
            tip = "Great mood! " + STUDY_TIPS["focus"][0]
        else:
            tip = "Excellent! " + STUDY_TIPS["motivation"][2]
    elif polarity < -0.2:
        mood = "😞 Sad"
        if "tired" in mood_data.text.lower() or "exhausted" in mood_data.text.lower():
            tip = "Take a refreshing break! " + STUDY_TIPS["focus"][3]
        else:
            tip = "It's okay to feel down. " + STUDY_TIPS["motivation"][1]
    else:
        mood = "😐 Neutral"
        tip = "Stay focused! " + STUDY_TIPS["memory"][0]

    mood_entry = {
        "text": mood_data.text,
        "mood": mood,
        "tip": tip,
        "timestamp": datetime.now().isoformat()
    }
    moods.append(mood_entry)
    return {"mood": mood, "tip": tip, "text": mood_data.text}

@app.post("/add_task/")
async def add_task(task: Task):
    """Add a new study task or assignment"""
    if task.subject not in SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Invalid subject. Choose from: {', '.join(SUBJECTS)}")
    
    task_entry = {
        **task.dict(),
        "id": str(len(tasks) + 1),  # Simple numeric ID
        "timestamp": datetime.now().isoformat()
    }
    tasks.append(task_entry)
    return {"status": "Task added ✅", **task_entry}  # Return the task with its ID

@app.post("/study_session/")
async def record_study_session(session: StudySession):
    """Record a study session with goals and duration"""
    if session.subject not in SUBJECTS:
        raise HTTPException(status_code=400, detail=f"Invalid subject. Choose from: {', '.join(SUBJECTS)}")
    
    if session.duration < 5 or session.duration > 480:  # 8 hours max
        raise HTTPException(status_code=400, detail="Duration must be between 5 and 480 minutes")

    session_entry = {
        **session.dict(),
        "timestamp": datetime.now().isoformat()
    }
    study_sessions.append(session_entry)
    
    # Generate personalized tip based on session duration
    if session.duration > 120:  # More than 2 hours
        tip = STUDY_TIPS["focus"][1]  # Pomodoro technique
    else:
        tip = STUDY_TIPS["memory"][random.randint(0, len(STUDY_TIPS["memory"])-1)]
    
    return {
        "status": "Study session recorded ✅",
        "tip": tip,
        **session.dict()
    }

@app.get("/study_stats/")
async def get_study_stats():
    """Get study statistics and analytics"""
    total_study_time = sum(session["duration"] for session in study_sessions)
    subjects_studied = {}
    for session in study_sessions:
        subjects_studied[session["subject"]] = subjects_studied.get(session["subject"], 0) + session["duration"]
    
    # Calculate completion rates and priorities
    tasks_completed = len([t for t in tasks if t["status"] == "completed"])
    total_tasks = len(tasks)
    completion_rate = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 0
    
    return {
        "total_study_time_minutes": total_study_time,
        "subjects_breakdown": subjects_studied,
        "task_completion_rate": round(completion_rate, 2),
        "total_notes": len(reminders),
        "mood_tracking": {
            "positive": len([m for m in moods if "Happy" in m["mood"]]),
            "neutral": len([m for m in moods if "Neutral" in m["mood"]]),
            "negative": len([m for m in moods if "Sad" in m["mood"]])
        }
    }

@app.get("/study_tips/{category}")
async def get_study_tips(category: str):
    """Get study tips by category"""
    if category not in STUDY_TIPS:
        raise HTTPException(status_code=400, detail=f"Invalid category. Choose from: {', '.join(STUDY_TIPS.keys())}")
    return {"category": category, "tips": STUDY_TIPS[category]}

@app.put("/update_task_status/{task_id}")
async def update_task_status(task_id: str, task_update: TaskUpdate):
    """Update the status of a task"""
    if task_update.status not in ["pending", "in-progress", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    for task in tasks:
        if task.get("id") == task_id:
            task["status"] = task_update.status
            return {"message": "Task status updated", "task": task}
    
    raise HTTPException(status_code=404, detail="Task not found")

@app.get("/all_data/")
def all_data():
    """Show all saved data including notes, moods, tasks, and study sessions"""
    return {
        "reminders": reminders,
        "mood_logs": moods,
        "tasks": tasks,
        "study_sessions": study_sessions,
        "available_subjects": SUBJECTS,
        "note_categories": NOTE_CATEGORIES
    }
