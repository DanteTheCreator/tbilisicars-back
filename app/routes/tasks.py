from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.models.admin import Admin
from app.models.admin_group import AdminGroup
from app.models.task import Task, TaskComment, TaskStatus, TaskPriority, task_assignees, task_group_assignees

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    assigned_to_ids: List[int] = []
    assigned_group_ids: List[int] = []
    priority: TaskPriority = TaskPriority.MEDIUM
    related_vehicle_id: Optional[int] = None
    related_booking_id: Optional[int] = None
    is_private: bool = False


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    assigned_to_ids: Optional[List[int]] = None
    assigned_group_ids: Optional[List[int]] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    related_vehicle_id: Optional[int] = None
    related_booking_id: Optional[int] = None
    is_private: Optional[bool] = None


class TaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    deadline: Optional[datetime]
    completed_at: Optional[datetime]
    status: TaskStatus
    priority: TaskPriority
    created_by_id: int
    related_vehicle_id: Optional[int]
    related_booking_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    # Include related user info
    created_by: dict
    assignees: List[dict] = []
    assigned_groups: List[dict] = []
    related_vehicle: Optional[dict] = None
    related_booking: Optional[dict] = None

    class Config:
        from_attributes = True


def _format_task(task: Task) -> dict:
    """Format a Task ORM object into a response dict."""
    return {
        "id": task.id,
        "name": task.name,
        "description": task.description,
        "deadline": task.deadline,
        "completed_at": task.completed_at,
        "status": task.status,
        "priority": task.priority,
        "created_by_id": task.created_by_id,
        "related_vehicle_id": task.related_vehicle_id,
        "related_booking_id": task.related_booking_id,
        "is_private": task.is_private,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "created_by": {
            "id": task.created_by.id,
            "username": task.created_by.username,
            "full_name": task.created_by.full_name
        },
        "assignees": [
            {"id": a.id, "username": a.username, "full_name": a.full_name}
            for a in task.assignees
        ],
        "assigned_groups": [
            {"id": g.id, "name": g.name}
            for g in task.assigned_groups
        ],
        "related_vehicle": {
            "id": task.related_vehicle.id,
            "brand": task.related_vehicle.brand_name or task.related_vehicle.make or "",
            "model": task.related_vehicle.model_name or task.related_vehicle.model or "",
            "name": f"{task.related_vehicle.make or ''} {task.related_vehicle.model or ''} ({task.related_vehicle.license_plate})".strip()
        } if task.related_vehicle else None,
        "related_booking": {
            "id": task.related_booking.id,
            "reference_number": task.related_booking.reference_number
        } if task.related_booking else None
    }


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None),
    assigned_to_me: bool = Query(False),
    created_by_me: bool = Query(False),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all tasks with optional filters."""
    # Get group IDs for current admin
    admin_with_groups = (
        db.query(Admin)
        .options(joinedload(Admin.groups))
        .filter(Admin.id == current_admin.id)
        .first()
    )
    my_group_ids = [g.id for g in admin_with_groups.groups] if admin_with_groups else []

    query = db.query(Task).options(
        joinedload(Task.created_by),
        joinedload(Task.assignees),
        joinedload(Task.assigned_groups),
        joinedload(Task.related_vehicle),
        joinedload(Task.related_booking)
    )

    # Apply filters
    if status_filter:
        query = query.filter(Task.status == status_filter)

    if assigned_to_me:
        query = query.filter(
            or_(
                Task.assignees.any(Admin.id == current_admin.id),
                Task.assigned_groups.any(AdminGroup.id.in_(my_group_ids)) if my_group_ids else False
            )
        )

    if created_by_me:
        query = query.filter(Task.created_by_id == current_admin.id)

    # "all" filter: no user-scoping, show everything for management visibility

    tasks = query.order_by(Task.deadline.asc().nullslast(), Task.created_at.desc()).all()

    # Deduplicate (joinedload on multiple collections can cause dupes)
    seen = set()
    unique_tasks = []
    for t in tasks:
        if t.id not in seen:
            seen.add(t.id)
            unique_tasks.append(t)

    # Filter out private tasks the current admin should not see
    visible_tasks = []
    is_filtered_view = assigned_to_me or created_by_me
    for t in unique_tasks:
        if not t.is_private:
            visible_tasks.append(t)
        elif not is_filtered_view:
            # Private tasks never appear in "All Tasks" view
            continue
        elif t.created_by_id == current_admin.id:
            visible_tasks.append(t)
        elif any(a.id == current_admin.id for a in t.assignees):
            visible_tasks.append(t)
        elif my_group_ids and any(g.id in my_group_ids for g in t.assigned_groups):
            visible_tasks.append(t)

    return [_format_task(task) for task in visible_tasks]


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new task."""
    # Validate and fetch all assignees
    assignees: List[Admin] = []
    for admin_id in task_data.assigned_to_ids:
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Admin with id {admin_id} not found"
            )
        assignees.append(admin)

    # Validate and fetch all assigned groups
    assigned_groups: List[AdminGroup] = []
    for group_id in task_data.assigned_group_ids:
        group = db.query(AdminGroup).filter(AdminGroup.id == group_id).first()
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with id {group_id} not found"
            )
        assigned_groups.append(group)

    task = Task(
        name=task_data.name,
        description=task_data.description,
        deadline=task_data.deadline,
        priority=task_data.priority,
        created_by_id=current_admin.id,
        related_vehicle_id=task_data.related_vehicle_id,
        related_booking_id=task_data.related_booking_id,
        status=TaskStatus.PENDING,
        is_private=task_data.is_private
    )
    task.assignees = assignees
    task.assigned_groups = assigned_groups

    db.add(task)
    db.commit()
    db.refresh(task)
    db.refresh(task, ['created_by', 'assignees', 'assigned_groups'])

    return _format_task(task)


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


@router.get("/groups/list")
async def list_groups_for_assignment(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get list of all admin groups for task assignment."""
    from sqlalchemy.orm import joinedload as jl
    groups = (
        db.query(AdminGroup)
        .options(jl(AdminGroup.members))
        .order_by(AdminGroup.name)
        .all()
    )

    seen = set()
    unique = []
    for g in groups:
        if g.id not in seen:
            seen.add(g.id)
            unique.append(g)

    return [
        {
            "id": group.id,
            "name": group.name,
            "member_ids": [m.id for m in group.members]
        }
        for group in unique
    ]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific task by ID."""
    task = db.query(Task).options(
        joinedload(Task.created_by),
        joinedload(Task.assignees),
        joinedload(Task.assigned_groups)
    ).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Check access for private tasks
    if task.is_private:
        admin_with_groups = (
            db.query(Admin)
            .options(joinedload(Admin.groups))
            .filter(Admin.id == current_admin.id)
            .first()
        )
        my_group_ids = [g.id for g in admin_with_groups.groups] if admin_with_groups else []
        is_creator = task.created_by_id == current_admin.id
        is_assignee = any(a.id == current_admin.id for a in task.assignees)
        is_in_group = my_group_ids and any(g.id in my_group_ids for g in task.assigned_groups)
        if not (is_creator or is_assignee or is_in_group):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

    return _format_task(task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a task."""
    task = db.query(Task).options(
        joinedload(Task.created_by),
        joinedload(Task.assignees),
        joinedload(Task.assigned_groups)
    ).filter(Task.id == task_id).first()

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
    if task_data.priority is not None:
        task.priority = task_data.priority
    if task_data.related_vehicle_id is not None:
        task.related_vehicle_id = task_data.related_vehicle_id
    if task_data.related_booking_id is not None:
        task.related_booking_id = task_data.related_booking_id
    if task_data.is_private is not None:
        task.is_private = task_data.is_private

    if task_data.assigned_to_ids is not None:
        assignees: List[Admin] = []
        for admin_id in task_data.assigned_to_ids:
            admin = db.query(Admin).filter(Admin.id == admin_id).first()
            if not admin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Admin with id {admin_id} not found"
                )
            assignees.append(admin)
        task.assignees = assignees

    if task_data.assigned_group_ids is not None:
        assigned_groups: List[AdminGroup] = []
        for group_id in task_data.assigned_group_ids:
            group = db.query(AdminGroup).filter(AdminGroup.id == group_id).first()
            if not group:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Group with id {group_id} not found"
                )
            assigned_groups.append(group)
        task.assigned_groups = assigned_groups

    if task_data.status is not None:
        task.status = task_data.status
        if task_data.status == TaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = datetime.now()

    task.updated_at = datetime.now()

    db.commit()
    db.refresh(task, ['created_by', 'assignees', 'assigned_groups'])

    return _format_task(task)


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

    # Only creator or admin can delete tasks
    if task.created_by_id != current_admin.id and current_admin.admin_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this task"
        )

    db.delete(task)
    db.commit()

    return None


# ─── Task Comments ─────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str


@router.get("/{task_id}/comments")
async def list_task_comments(
    task_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all comments for a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    comments = (
        db.query(TaskComment)
        .options(joinedload(TaskComment.admin))
        .filter(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.asc())
        .all()
    )

    return [
        {
            "id": c.id,
            "content": c.content,
            "admin": {
                "id": c.admin.id,
                "username": c.admin.username,
                "full_name": c.admin.full_name,
            },
            "created_at": c.created_at,
        }
        for c in comments
    ]


@router.post("/{task_id}/comments", status_code=status.HTTP_201_CREATED)
async def create_task_comment(
    task_id: int,
    data: CommentCreate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Add a comment to a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    comment = TaskComment(
        task_id=task_id,
        admin_id=current_admin.id,
        content=data.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    admin = db.query(Admin).filter(Admin.id == current_admin.id).first()

    return {
        "id": comment.id,
        "content": comment.content,
        "admin": {
            "id": admin.id,
            "username": admin.username,
            "full_name": admin.full_name,
        },
        "created_at": comment.created_at,
    }


@router.delete("/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_comment(
    task_id: int,
    comment_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a comment. Only the comment author or admin role can delete."""
    comment = (
        db.query(TaskComment)
        .filter(TaskComment.id == comment_id, TaskComment.task_id == task_id)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.admin_id != current_admin.id and current_admin.admin_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment")

    db.delete(comment)
    db.commit()
    return None
