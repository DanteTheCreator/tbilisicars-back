from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc

from app.core.auth import get_current_admin
from app.core.db import get_db
from app.models.admin import Admin
from app.models.case import Case, CaseComment, CaseAttachment, CasePriority, CaseStatus

router = APIRouter(prefix="/cases", tags=["Cases"])

# Pydantic Models
class CaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    priority: CasePriority = CasePriority.MEDIUM
    related_booking_id: Optional[int] = None
    related_user_id: Optional[int] = None
    assigned_admin_ids: List[int] = []


class CaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CaseStatus] = None
    priority: Optional[CasePriority] = None
    related_booking_id: Optional[int] = None
    related_user_id: Optional[int] = None


class CommentCreate(BaseModel):
    content: str


class AssignAdminRequest(BaseModel):
    admin_ids: List[int]


class AdminBasic(BaseModel):
    id: int
    username: str
    full_name: str
    
    class Config:
        from_attributes = True


class AttachmentResponse(BaseModel):
    id: int
    filename: str
    file_path: str
    file_size: int
    content_type: str
    admin: AdminBasic
    created_at: datetime
    
    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: int
    content: str
    admin: AdminBasic
    attachments: List[AttachmentResponse]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: CaseStatus
    priority: CasePriority
    created_by: AdminBasic
    assigned_admins: List[AdminBasic]
    comments: List[CommentResponse]
    attachments: List[AttachmentResponse]
    related_booking_id: Optional[int]
    related_user_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CaseListItem(BaseModel):
    id: int
    name: str
    status: CaseStatus
    priority: CasePriority
    created_by: AdminBasic
    assigned_admins: List[AdminBasic]
    comments_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Routes
@router.get("", response_model=List[CaseListItem])
async def list_cases(
    status_filter: Optional[CaseStatus] = None,
    priority_filter: Optional[CasePriority] = None,
    assigned_to_me: bool = False,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all cases with optional filters."""
    query = db.query(Case).options(
        joinedload(Case.created_by),
        joinedload(Case.assigned_admins),
        joinedload(Case.comments)
    )
    
    # Apply filters
    if status_filter:
        query = query.filter(Case.status == status_filter)
    
    if priority_filter:
        query = query.filter(Case.priority == priority_filter)
    
    if assigned_to_me:
        query = query.join(Case.assigned_admins).filter(Admin.id == current_admin.id)
    
    cases = query.order_by(desc(Case.created_at)).all()
    
    # Build response with comment count
    result = []
    for case in cases:
        result.append(CaseListItem(
            id=case.id,
            name=case.name,
            status=case.status,
            priority=case.priority,
            created_by=AdminBasic.model_validate(case.created_by),
            assigned_admins=[AdminBasic.model_validate(admin) for admin in case.assigned_admins],
            comments_count=len(case.comments),
            created_at=case.created_at,
            updated_at=case.updated_at
        ))
    
    return result


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new case."""
    # Create the case
    new_case = Case(
        name=case_data.name,
        description=case_data.description,
        priority=case_data.priority,
        created_by_id=current_admin.id,
        related_booking_id=case_data.related_booking_id,
        related_user_id=case_data.related_user_id
    )
    
    db.add(new_case)
    db.flush()
    
    # Assign admins if provided
    if case_data.assigned_admin_ids:
        assigned_admins = db.query(Admin).filter(Admin.id.in_(case_data.assigned_admin_ids)).all()
        new_case.assigned_admins = assigned_admins
    
    db.commit()
    db.refresh(new_case)
    
    return CaseResponse.model_validate(new_case)


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific case with all details."""
    case = db.query(Case).options(
        joinedload(Case.created_by),
        joinedload(Case.assigned_admins),
        joinedload(Case.comments).joinedload(CaseComment.admin),
        joinedload(Case.comments).joinedload(CaseComment.attachments).joinedload(CaseAttachment.admin),
        joinedload(Case.attachments).joinedload(CaseAttachment.admin)
    ).filter(Case.id == case_id).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return CaseResponse.model_validate(case)


@router.patch("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: int,
    case_update: CaseUpdate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Update fields
    update_data = case_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(case, field, value)
    
    db.commit()
    db.refresh(case)
    
    return CaseResponse.model_validate(case)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    db.delete(case)
    db.commit()
    
    return None


@router.post("/{case_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    case_id: int,
    comment_data: CommentCreate,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Add a comment to a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    comment = CaseComment(
        case_id=case_id,
        admin_id=current_admin.id,
        content=comment_data.content
    )
    
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return CommentResponse.model_validate(comment)


@router.post("/{case_id}/assign", response_model=CaseResponse)
async def assign_admins(
    case_id: int,
    assignment: AssignAdminRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Assign or reassign admins to a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Get the admins
    admins = db.query(Admin).filter(Admin.id.in_(assignment.admin_ids)).all()
    
    # Replace current assignments
    case.assigned_admins = admins
    
    db.commit()
    db.refresh(case)
    
    return CaseResponse.model_validate(case)


@router.post("/{case_id}/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    case_id: int,
    file: UploadFile = File(...),
    comment_id: Optional[int] = Form(None),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Upload an attachment to a case or comment."""
    case = db.query(Case).filter(Case.id == case_id).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    if comment_id:
        comment = db.query(CaseComment).filter(
            CaseComment.id == comment_id,
            CaseComment.case_id == case_id
        ).first()
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
    
    # Create upload directory if it doesn't exist
    upload_dir = Path("/app/uploads/cases") / str(case_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = Path(file.filename).suffix
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = upload_dir / unique_filename
    
    # Save file
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Get file size
    file_size = file_path.stat().st_size
    
    # Create attachment record
    attachment = CaseAttachment(
        case_id=case_id,
        comment_id=comment_id,
        admin_id=current_admin.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream"
    )
    
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    
    return AttachmentResponse.model_validate(attachment)


@router.delete("/{case_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    case_id: int,
    comment_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a comment from a case."""
    comment = db.query(CaseComment).filter(
        CaseComment.id == comment_id,
        CaseComment.case_id == case_id
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Only the comment author or admin can delete
    if comment.admin_id != current_admin.id and current_admin.admin_role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    db.delete(comment)
    db.commit()
    
    return None


@router.get("/attachments/{attachment_id}/file")
async def download_attachment(
    attachment_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Download or view an attachment file."""
    attachment = db.query(CaseAttachment).filter(CaseAttachment.id == attachment_id).first()
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    file_path = Path(attachment.file_path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=str(file_path),
        filename=attachment.filename,
        media_type=attachment.content_type
    )
