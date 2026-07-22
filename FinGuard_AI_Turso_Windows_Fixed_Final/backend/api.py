"""FastAPI layer with JWT bearer and HttpOnly-cookie authentication."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Generator

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal, engine, initialize_database
from backend.logging_config import configure_logging
from backend.ml_service import load_model_registry
from backend.models import AuditLog, BankAccount, StatementImport, Transaction, TransactionType, User, UserRole, UserStatus
from backend.security import create_access_token, decode_access_token, mask_email, password_is_strong
from backend.sqlite_manager import database_overview, table_counts
from backend.services import authenticate_user, log_audit, register_user

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="FinGuard AI API",
    description="Secure personal-finance intelligence API for the FinGuard academic MVP.",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
bearer = HTTPBearer(auto_error=False)


class RegisterPayload(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()[:64]
    return request.client.host[:64] if request.client else None


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else request.cookies.get("finguard_access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_access_token(token)
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not active")
    if payload.get("role") != user.role.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token role is no longer valid")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ready", "docs": "/docs", "version": "4.0.0", "database_engine": "SQLite"}


@app.get("/api/v1/health")
def health() -> dict[str, object]:
    database_status = "online"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as error:
        database_status = f"offline: {type(error).__name__}"
    return {
        "status": "online" if database_status == "online" else "degraded",
        "environment": settings.environment,
        "database": database_status,
        "database_engine": "SQLite",
        "database_path": str(settings.sqlite_path),
        "local_only": settings.local_only,
    }


@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterPayload, db: Session = Depends(get_db)) -> dict:
    valid, message = password_is_strong(payload.password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
    try:
        user = register_user(db, payload.full_name, str(payload.email), payload.password)
        db.flush()
        return {"id": user.id, "email": user.email, "role": user.role.value}
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


@app.post("/api/v1/auth/login")
def login(payload: LoginPayload, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    try:
        user = authenticate_user(
            db,
            str(payload.email),
            payload.password,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent", "")[:255],
        )
    except PermissionError as error:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(error))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id, user.role.value)
    response.set_cookie(
        "finguard_access_token",
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.access_token_minutes * 60,
        "user": {"id": user.id, "name": user.full_name, "role": user.role.value},
    }


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    response.delete_cookie("finguard_access_token", path="/")
    log_audit(db, "LOGOUT", user.id, "USER", str(user.id), ip_address=_client_ip(request), user_agent=request.headers.get("user-agent", "")[:255])
    return {"message": "Logged out"}


@app.get("/api/v1/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "name": user.full_name, "email": user.email, "role": user.role.value, "status": user.status.value}


@app.get("/api/v1/transactions")
def transactions(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    transaction_type: TransactionType | None = Query(None),
) -> dict:
    query = select(Transaction).where(Transaction.user_id == user.id)
    count_query = select(func.count(Transaction.id)).where(Transaction.user_id == user.id)
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)
        count_query = count_query.where(Transaction.transaction_type == transaction_type)
    rows = db.scalars(query.order_by(Transaction.transaction_date.desc()).offset(offset).limit(limit)).all()
    total = db.scalar(count_query) or 0
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": row.id,
                "date": row.transaction_date,
                "description": row.description,
                "type": row.transaction_type.value,
                "amount": float(row.amount),
                "risk": row.risk_level,
                "account_id": row.bank_account_id,
                "statement_id": row.statement_import_id,
            }
            for row in rows
        ],
    }


@app.get("/api/v1/models")
def models(_: User = Depends(current_user)) -> list[dict]:
    return load_model_registry()


@app.get("/api/v1/admin/summary")
def admin_summary(_: User = Depends(admin_user), db: Session = Depends(get_db)) -> dict:
    users = db.scalars(select(User)).all()
    txs = db.scalars(select(Transaction)).all()
    return {
        "total_users": len(users),
        "active_users": sum(user.status == UserStatus.ACTIVE for user in users),
        "total_accounts": db.scalar(select(func.count(BankAccount.id))) or 0,
        "total_statements": db.scalar(select(func.count(StatementImport.id))) or 0,
        "total_transactions": len(txs),
        "total_income": sum(float(item.amount) for item in txs if item.transaction_type == TransactionType.INCOME),
        "total_expense": sum(float(item.amount) for item in txs if item.transaction_type == TransactionType.EXPENSE),
        "audit_events": db.scalar(select(func.count(AuditLog.id))) or 0,
        "user_preview": [{"id": user.id, "name": user.full_name, "email": mask_email(user.email), "role": user.role.value, "status": user.status.value} for user in users[:20]],
    }


@app.get("/api/v1/admin/database")
def admin_database(_: User = Depends(admin_user)) -> dict:
    """Return SQLite health and table counts without exposing sensitive rows."""
    overview = database_overview()
    return {**overview, "table_counts": table_counts()}
