from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.domain import Task
from app.schemas.task import TaskCreate, TaskResponse
from app.core.logger import logger

router = APIRouter()

@router.post("/", response_model=TaskResponse)
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    task = Task(goal=task_in.goal, risk_level=task_in.risk_level)
    db.add(task)
    db.commit()
    db.refresh(task)
    
    logger.info(
        "Task created",
        extra={
            "task_id": task.id,
            "event": "TASK_CREATED",
            "status": "SUCCESS"
        }
    )
    return task

@router.get("/", response_model=List[TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(Task).all()
