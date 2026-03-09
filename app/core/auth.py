from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.models.admin import Admin
import logging

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer()

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.info(f"[AUTH] Created token expiring in {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes at {expire}")
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"[AUTH] Token verification failed: {type(e).__name__}: {str(e)}")
        return None


def authenticate_admin(db: Session, username: str, password: str) -> Optional[Admin]:
    """Authenticate an admin user."""
    logger.info(f"[AUTH] Login attempt for: {username}")
    admin = db.query(Admin).filter(
        (Admin.username == username) | (Admin.email == username)
    ).first()
    if not admin:
        logger.warning(f"[AUTH] User not found: {username}")
        return None

    logger.info(f"[AUTH] Found user: {admin.username}, is_active: {admin.is_active}")
    # Verify password but guard against passlib/bcrypt issues that can raise
    # ValueError (e.g. password > 72 bytes) or backend detection errors. If
    # verification fails or raises, treat as authentication failure rather
    # than letting an exception return a 500.
    try:
        ok = verify_password(password, admin.hashed_password)
        logger.info(f"[AUTH] Password verification result: {ok}")
    except ValueError:
        # Known bcrypt limitation: treat as auth failure
        logger.debug("Password verification failed due to ValueError (possible bcrypt length limit)")
        return None
    except Exception:
        # Unexpected errors should be logged and treated as auth failure to
        # avoid exposing stack traces to clients.
        logger.exception("Unexpected error during password verification")
        return None

    if not ok:
        logger.warning(f"[AUTH] Password mismatch for user: {username}")
        return None
    
    if not admin.is_active:
        logger.warning(f"[AUTH] User is inactive: {username}")
        return None
    
    # Update last login
    admin.last_login = datetime.utcnow()
    db.commit()
    
    return admin


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """Get current authenticated admin from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception
        
        admin_id_str = payload.get("sub")
        if admin_id_str is None:
            raise credentials_exception
        
        # Convert string to integer
        admin_id = int(admin_id_str)
            
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if admin is None or not admin.is_active:
        raise credentials_exception
    
    return admin


def get_current_super_admin(current_admin: Admin = Depends(get_current_admin)) -> Admin:
    """Get current authenticated admin with highest privileges."""
    logger.info(f"[AUTH] Checking super admin - user: {current_admin.username}, role: '{current_admin.admin_role}', type: {type(current_admin.admin_role)}")
    logger.info(f"[AUTH] Role comparison: '{current_admin.admin_role}' != 'admin' = {current_admin.admin_role != 'admin'}")
    if current_admin.admin_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_admin


def get_current_admin_or_higher(current_admin: Admin = Depends(get_current_admin)) -> Admin:
    """Get current authenticated admin with service manager role or higher (not rental agent)."""
    if current_admin.admin_role == "rental_agent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Higher privileges required"
        )
    return current_admin


def get_optional_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[Admin]:
    """Get current authenticated admin from JWT token, or None if not authenticated."""
    if credentials is None:
        return None
    
    try:
        payload = verify_token(credentials.credentials)
        if payload is None:
            return None
        
        admin_id_str = payload.get("sub")
        if admin_id_str is None:
            return None
        
        admin_id = int(admin_id_str)
        admin = db.query(Admin).filter(Admin.id == admin_id).first()
        if admin is None or not admin.is_active:
            return None
        
        return admin
    except (JWTError, ValueError, TypeError):
        return None


def require_role(required_role: str):
    """Require specific admin role or higher."""
    def role_dependency(current_admin: Admin = Depends(get_current_admin)) -> Admin:
        role_hierarchy = {
            "rental_agent": 0,
            "service_manager": 1,
            "regional_manager": 2,
            "admin": 3
        }
        
        if role_hierarchy.get(current_admin.admin_role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {required_role.value}"
            )
        return current_admin
    return role_dependency


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def permission_dependency(current_admin: Admin = Depends(get_current_admin)) -> Admin:
        # Admins have all permissions
        if current_admin.admin_role == "admin":
            return current_admin
        
        # Check specific permission
        if not getattr(current_admin, permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return current_admin
    return permission_dependency
