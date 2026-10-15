from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user, log_audit_event
from app.models.user import User, LoginHistory, UserRole
from app.schemas.auth import LoginRequest, TokenResponse, PasswordResetRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ip_addr = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    user = db.query(User).filter(User.email == login_data.email.lower().strip()).first()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        if user:
            # Record failed login
            db.add(LoginHistory(user_id=user.id, ip_address=ip_addr, user_agent=user_agent, status="FAILED"))
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact an Administrator."
        )

    # Record successful login
    db.add(LoginHistory(user_id=user.id, ip_address=ip_addr, user_agent=user_agent, status="SUCCESS"))
    user.last_active_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject=user.id, role=user.role.value)
    
    # Also set HTTP-only cookie for secure browser sessions
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        samesite="lax",
        secure=False # Set to True in production with HTTPS
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email
    )

@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "mobile": current_user.mobile,
        "is_active": current_user.is_active,
        "last_active_at": current_user.last_active_at
    }

@router.post("/change-password")
def change_password(
    pwd_data: PasswordResetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if len(pwd_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    current_user.hashed_password = get_password_hash(pwd_data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
