from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User, UserRole, LoginHistory
from app.models.quotation import Quotation, QuotationRevision, QuotationStatus
from app.schemas.auth import AdminUserCreate, UserUpdate, PasswordResetRequest

router = APIRouter(prefix="/admin/users", tags=["Admin User Management"])

@router.get("/agents")
def list_agents(
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User).filter(User.role == UserRole.AGENT)
    if search:
        query = query.filter((User.full_name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")) | (User.mobile.ilike(f"%{search}%")))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    agents = query.order_by(User.created_at.desc()).all()
    now = datetime.now(timezone.utc)
    five_min_ago = now - timedelta(minutes=5)

    result = []
    for agent in agents:
        # Determine online status based on active heartbeat within 5 minutes
        is_online = bool(agent.last_active_at and agent.last_active_at.replace(tzinfo=timezone.utc) >= five_min_ago)
        
        # Calculate quotation metrics
        quotes = db.query(Quotation).filter(Quotation.agent_id == agent.id).all()
        total_quotes = len(quotes)
        confirmed_orders = sum(1 for q in quotes if q.status == QuotationStatus.ORDER_CONFIRMED)
        
        result.append({
            "id": agent.id,
            "email": agent.email,
            "full_name": agent.full_name,
            "mobile": agent.mobile,
            "is_active": agent.is_active,
            "is_online": is_online,
            "last_active_at": agent.last_active_at,
            "created_at": agent.created_at,
            "total_quotations": total_quotes,
            "confirmed_orders": confirmed_orders,
            "conversion_rate": round((confirmed_orders / total_quotes * 100), 1) if total_quotes > 0 else 0.0
        })

    return result

@router.post("/agents", status_code=status.HTTP_201_CREATED)
def create_agent(
    user_in: AdminUserCreate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_user = User(
        email=user_in.email.lower().strip(),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        mobile=user_in.mobile,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit_event(db, current_admin, "CREATE_AGENT", "User", new_user.id, {"email": new_user.email}, request)
    return {"id": new_user.id, "email": new_user.email, "full_name": new_user.full_name, "role": new_user.role}

@router.put("/agents/{agent_id}")
def update_agent(
    agent_id: str,
    user_in: UserUpdate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    agent = db.query(User).filter(User.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if user_in.full_name is not None:
        agent.full_name = user_in.full_name
    if user_in.mobile is not None:
        agent.mobile = user_in.mobile
    if user_in.is_active is not None:
        agent.is_active = user_in.is_active

    db.commit()
    log_audit_event(db, current_admin, "UPDATE_AGENT", "User", agent.id, {"is_active": agent.is_active}, request)
    return {"message": "Agent profile updated successfully"}

@router.post("/agents/{agent_id}/reset-password")
def reset_agent_password(
    agent_id: str,
    pwd_data: PasswordResetRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    agent = db.query(User).filter(User.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if len(pwd_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    agent.hashed_password = get_password_hash(pwd_data.new_password)
    db.commit()
    log_audit_event(db, current_admin, "RESET_PASSWORD", "User", agent.id, {}, request)
    return {"message": "Agent password has been reset"}

@router.get("/agents/{agent_id}/login-history")
def get_agent_login_history(
    agent_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    history = db.query(LoginHistory).filter(LoginHistory.user_id == agent_id).order_by(LoginHistory.created_at.desc()).limit(50).all()
    return history
