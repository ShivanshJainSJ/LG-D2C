from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.models.audit import AuditLog

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_token_from_header_or_cookie(request: Request, token: str = Depends(oauth2_scheme)) -> str:
    if token:
        return token
    # Fallback to HTTP-only cookie if present
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        if cookie_token.startswith("Bearer "):
            return cookie_token[7:]
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_user(
    request: Request,
    token: str = Depends(get_token_from_header_or_cookie),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")
    
    # Invalidate token if issued before user changed their password
    token_iat = payload.get("iat")
    if token_iat is not None and user.password_changed_at is not None:
        pwd_changed_ts = user.password_changed_at.replace(tzinfo=timezone.utc).timestamp() if user.password_changed_at.tzinfo is None else user.password_changed_at.timestamp()
        if token_iat < (pwd_changed_ts - 1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been invalidated due to a password change. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Update last heartbeat/active timestamp
    user.last_active_at = datetime.now(timezone.utc)
    db.commit()

    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    return current_user

def require_agent(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.AGENT, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent privileges required"
        )
    return current_user

def log_audit_event(
    db: Session,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: str = None,
    details: dict = None,
    request: Request = None
):
    ip_address = request.client.host if request and request.client else None
    audit_entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else "system",
        actor_role=actor.role.value if actor else "SYSTEM",
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details) if details else None,
        ip_address=ip_address
    )
    db.add(audit_entry)
    db.commit()
