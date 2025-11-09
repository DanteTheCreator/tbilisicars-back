from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.models.admin import Admin
from app.models.task import Task, TaskStatus, TaskPriority

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    assigned_to_id: Optional[int] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    related_vehicle_id: Optional[int] = None
    related_booking_id: Optional[int] = None


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    assigned_to_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    related_vehicle_id: Optional[int] = None
    related_booking_id: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    completed_at: Optional[datetime]
    status: TaskStatus
    priority: TaskPriority
    created_by_id: int
    assigned_to_id: Optional[int]
    related_vehicle_id: Optional[int]
    related_booking_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    # Include related user info
    created_by: dict
    assigned_to: Optional[dict] = None
    related_vehicle: Optional[dict] = None
    related_booking: Optional[dict] = None
    
    class Config:
        from_attributes = True


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None),
    assigned_to_me: bool = Query(False),
    created_by_me: bool = Query(False),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all tasks with optional filters."""
    query = db.query(Task).options(
        joinedload(Task.created_by),
        joinedload(Task.assigned_to),
        joinedload(Task.related_vehicle),
        joinedload(Task.related_booking)
    )
    
    # Apply filters
    if status_filter:
        query = query.filter(Task.status == status_filter)
    
    if assigned_to_me:
        query = query.filter(Task.assigned_to_id == current_admin.id)
    
    if created_by_me:
        query = query.filter(Task.created_by_id == current_admin.id)
    
    # If no specific filters, show tasks relevant to the user
    if not assigned_to_me and not created_by_me:
        query = query.filter(
            or_(
                Task.assigned_to_id == current_admin.id,
                Task.created_by_id == current_admin.id
            )
        )
    
    tasks = query.order_by(Task.deadline.asc().nullslast(), Task.created_at.desc()).all()
    
    # Format response
    result = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "deadline": task.deadline,
            "completed_at": task.completed_at,
            "status": task.status,
            "priority": task.priority,
            "created_by_id": task.created_by_id,
            "assigned_to_id": task.assigned_to_id,
            "related_vehicle_id": task.related_vehicle_id,
            "related_booking_id": task.related_booking_id,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "created_by": {
                "id": task.created_by.id,
                "username": task.created_by.username,
                "full_name": task.created_by.full_name
            },
            "assigned_to": {
                "id": task.assigned_to.id,
                "username": task.assigned_to.username,
                "full_name": task.assigned_to.full_name
            } if task.assigned_to else None,
            "related_vehicle": {
                "id": task.related_vehicle.id,
                "brand": task.related_vehicle.brand,
                "model": task.related_vehicle.model,
                "name": task.related_vehicle.name
            } if task.related_vehicle else None,
            "related_booking": {
                "id": task.related_booking.id,
                "reference_number": task.related_booking.reference_number
            } if task.related_booking else None
        }
        result.append(task_dict)
    
    return result


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new task."""
    # Validate assigned_to_id if provided
    if task_data.assigned_to_id:
        assignee = db.query(Admin).filter(Admin.id == task_data.assigned_to_id).first()
        if not assignee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admin with id {task_data.assigned_to_id} not found"
            )
    
    task = Task(
        name=task_data.name,
        description=task_data.description,
        deadline=task_data.deadline,
        priority=task_data.priority,
        created_by_id=current_admin.id,
        assigned_to_id=task_data.assigned_to_id,
        related_vehicle_id=task_data.related_vehicle_id,
        related_booking_id=task_data.related_booking_id,
        status=TaskStatus.PENDING
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Load relationships
    db.refresh(task, ['created_by', 'assigned_to'])
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        deadline=task.deadline,
        completed_at=task.completed_at,
        status=task.status,
        priority=task.priority,
        created_by_id=task.created_by_id,
        assigned_to_id=task.assigned_to_id,
        related_vehicle_id=task.related_vehicle_id,
        related_booking_id=task.related_booking_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        created_by={
            "id": task.created_by.id,
            "username": task.created_by.username,
            "full_name": task.created_by.full_name
        },
        assigned_to={
            "id": task.assigned_to.id,
            "username": task.assigned_to.username,
            "full_name": task.assigned_to.full_name
        } if task.assigned_to else None
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific task by ID."""
    task = db.query(Task).options(
        joinedload(Task.created_by),
        joinedload(Task.assigned_to)
    ).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        deadline=task.deadline,
        completed_at=task.completed_at,
        status=task.status,
        priority=task.priority,
        created_by_id=task.created_by_id,
        assigned_to_id=task.assigned_to_id,
        related_vehicle_id=task.related_vehicle_id,
        related_booking_id=task.related_booking_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        created_by={
            "id": task.created_by.id,
            "username": task.created_by.username,
            "full_name": task.created_by.full_name
        },
        assigned_to={
            "id": task.assigned_to.id,
            "username": task.assigned_to.username,
            "full_name": task.assigned_to.full_name
        } if task.assigned_to else None
    )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Update fields if provided
    if task_data.name is not None:
        task.name = task_data.name
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.deadline is not None:
        task.deadline = task_data.deadline
    if task_data.assigned_to_id is not None:
        task.assigned_to_id = task_data.assigned_to_id
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.related_vehicle_id is not None:
        task.related_vehicle_id = task_data.related_vehicle_id
    if task_data.related_booking_id is not None:
        task.related_booking_id = task_data.related_booking_id
    
    if task_data.status is not None:
        task.status = task_data.status
        # Mark as completed when status changes to COMPLETED
        if task_data.status == TaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = datetime.utcnow()
    
    task.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(task, ['created_by', 'assigned_to'])
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        deadline=task.deadline,
        completed_at=task.completed_at,
        status=task.status,
        priority=task.priority,
        created_by_id=task.created_by_id,
        assigned_to_id=task.assigned_to_id,
        related_vehicle_id=task.related_vehicle_id,
        related_booking_id=task.related_booking_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        created_by={
            "id": task.created_by.id,
            "username": task.created_by.username,
            "full_name": task.created_by.full_name
        },
        assigned_to={
            "id": task.assigned_to.id,
            "username": task.assigned_to.username,
            "full_name": task.assigned_to.full_name
        } if task.assigned_to else None
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Only creator or super admin can delete tasks
    if task.created_by_id != current_admin.id and current_admin.admin_role.value != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this task"
        )
    
    db.delete(task)
    db.commit()
    
    return None


@router.get("/admins/list")
async def list_admins_for_assignment(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get list of all admins for task assignment."""
    admins = db.query(Admin).filter(Admin.is_active == True).all()
    
    return [
        {
            "id": admin.id,
            "username": admin.username,
            "full_name": admin.full_name,
            "admin_role": admin.admin_role.value if hasattr(admin.admin_role, 'value') else admin.admin_role
        }
        for admin in admins
    ]
