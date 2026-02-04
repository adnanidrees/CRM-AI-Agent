# app/main.py
from __future__ import annotations

from datetime import datetime, timedelta
import os
import random
import string
from typing import Optional, Dict, Any, Generator, List

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db import get_db, engine
from app.models import Base, Tenant, User, OTP, ChannelAccount, Contact, Deal, Message
from app.config import settings
from app.security import (
    hash_password,
    verify_password,
    create_token,
    decode_token,
)


# -----------------------------
# Helpers
# -----------------------------
def generate_otp_code() -> str:
    # 6-digit numeric OTP
    return f"{random.randint(0, 999999):06d}"


def now_utc_naive() -> datetime:
    # Use naive UTC datetime for SQLite simplicity
    return datetime.utcnow()


# -----------------------------
# Schemas
# -----------------------------
class RegisterIn(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=6, max_length=200)


class RegisterOut(BaseModel):
    ok: bool
    tenant_id: int
    user_id: int
    status: str


class VerifyEmailIn(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=12)


class VerifyPhoneIn(BaseModel):
    phone: str = Field(..., min_length=6, max_length=30)
    code: str = Field(..., min_length=4, max_length=12)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    ok: bool
    access_token: str
    token_type: str = "bearer"


class SimulateIn(BaseModel):
    channel: str
    channel_user_id: str
    text: str
    contact_name: Optional[str] = None


class TenantRow(BaseModel):
    id: int
    name: str
    status: str
    created_at: str


# -----------------------------
# Auth Dependency
# -----------------------------
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = auth.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(status_code=403, detail="User disabled")

    return user


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    if user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


# -----------------------------
# FastAPI App
# -----------------------------
app = FastAPI(title="AI CRM SaaS", version="1.0.0")


@app.middleware("http")
async def force_utf8_json(request: Request, call_next):
    """
    Ensures JSON responses have utf-8 charset to avoid mojibake in PowerShell / clients.
    """
    response = await call_next(request)

    ctype = response.headers.get("content-type", "")
    if "application/json" in ctype and "charset" not in ctype.lower():
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


@app.on_event("startup")
def on_startup():
    # Create DB schema
    Base.metadata.create_all(bind=engine)

    # Bootstrap superadmin
    db: Session = next(get_db())
    try:
        su = db.query(User).filter(User.email == settings.SUPERADMIN_EMAIL).first()
        if not su:
            su = User(
                tenant_id=None,
                email=settings.SUPERADMIN_EMAIL,
                phone=None,
                password_hash=hash_password(settings.SUPERADMIN_PASSWORD),
                role="superadmin",
                email_verified=True,
                phone_verified=True,
                is_active=True,
            )
            db.add(su)
            db.commit()
            print(f"[BOOTSTRAP] SuperAdmin created: {settings.SUPERADMIN_EMAIL}")
    finally:
        db.close()


# -----------------------------
# Health
# -----------------------------
@app.get("/health")
def health():
    return {"ok": True}


# -----------------------------
# Auth
# -----------------------------
@app.post("/auth/register", response_model=RegisterOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    # basic duplicate checks
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create tenant
    tenant = Tenant(name=payload.company_name, status="pending")
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Create user as tenant_admin
    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role="tenant_admin",
        email_verified=False,
        phone_verified=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create OTPs (hashed, latest unused)
    email_code = generate_otp_code()
    phone_code = generate_otp_code()

    expires_at = now_utc_naive() + timedelta(seconds=int(settings.OTP_TTL_SECONDS))

    otp_email = OTP(
        user_id=user.id,
        kind="email",
        code_hash=hash_password(email_code),
        expires_at=expires_at,
        used=False,
    )
    otp_phone = OTP(
        user_id=user.id,
        kind="phone",
        code_hash=hash_password(phone_code),
        expires_at=expires_at,
        used=False,
    )

    db.add_all([otp_email, otp_phone])
    db.commit()

    # Mock delivery for dev
    print(f"[MOCK EMAIL OTP] to={user.email} code={email_code}")
    if user.phone:
        print(f"[MOCK SMS OTP] to={user.phone} code={phone_code}")

    return {"ok": True, "tenant_id": tenant.id, "user_id": user.id, "status": tenant.status}


@app.post("/auth/verify-email")
def verify_email(payload: VerifyEmailIn, db: Session = Depends(get_db)):
    # Pick latest unused email OTP for the user (join via User)
    otp = (
        db.query(OTP)
        .join(User, User.id == OTP.user_id)
        .filter(User.email == payload.email)
        .filter(OTP.kind == "email")
        .filter(OTP.used == False)  # noqa: E712
        .order_by(desc(OTP.id))
        .first()
    )
    if not otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if otp.expires_at < now_utc_naive():
        raise HTTPException(status_code=400, detail="OTP expired")

    if not verify_password(payload.code, otp.code_hash):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp.used = True
    user = db.query(User).filter(User.id == otp.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.email_verified = True
    db.commit()

    return {"ok": True}


@app.post("/auth/verify-phone")
def verify_phone(payload: VerifyPhoneIn, db: Session = Depends(get_db)):
    otp = (
        db.query(OTP)
        .join(User, User.id == OTP.user_id)
        .filter(User.phone == payload.phone)
        .filter(OTP.kind == "phone")
        .filter(OTP.used == False)  # noqa: E712
        .order_by(desc(OTP.id))
        .first()
    )
    if not otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if otp.expires_at < now_utc_naive():
        raise HTTPException(status_code=400, detail="OTP expired")

    if not verify_password(payload.code, otp.code_hash):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    otp.used = True
    user = db.query(User).filter(User.id == otp.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.phone_verified = True
    db.commit()

    return {"ok": True}


@app.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(status_code=403, detail="User disabled")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(subject=user.email, role=user.role, tenant_id=user.tenant_id)
    return {"ok": True, "access_token": token, "token_type": "bearer"}


# -----------------------------
# Admin
# -----------------------------
@app.get("/admin/tenants", response_model=List[TenantRow])
def admin_tenants(_: User = Depends(require_superadmin), db: Session = Depends(get_db)):
    tenants = db.query(Tenant).order_by(Tenant.id.asc()).all()
    out = []
    for t in tenants:
        out.append(
            {
                "id": t.id,
                "name": t.name,
                "status": t.status,
                "created_at": t.created_at.isoformat() if getattr(t, "created_at", None) else "",
            }
        )
    return out


# -----------------------------
# Simulate inbound message (requires auth)
# -----------------------------
@app.post("/simulate")
def simulate(payload: SimulateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Simulates inbound messages from channels for testing.
    - Requires Bearer token
    - Creates/updates Contact + Message
    - Creates Deal if missing
    - Very basic stage logic for demo
    """
    if user.tenant_id is None:
        # superadmin can simulate, but needs tenant context — for simplicity forbid here
        raise HTTPException(status_code=400, detail="Superadmin cannot simulate without tenant")

    tenant_id = user.tenant_id

    # Find or create contact
    contact = (
        db.query(Contact)
        .filter(Contact.tenant_id == tenant_id)
        .filter(Contact.channel == payload.channel)
        .filter(Contact.channel_user_id == payload.channel_user_id)
        .first()
    )
    if not contact:
        contact = Contact(
            tenant_id=tenant_id,
            channel=payload.channel,
            channel_user_id=payload.channel_user_id,
            contact_name=payload.contact_name,
            phone=payload.channel_user_id if payload.channel == "whatsapp" else None,
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
    else:
        # update name if provided
        if payload.contact_name and not contact.contact_name:
            contact.contact_name = payload.contact_name
            db.commit()

    # Store inbound message
    msg = Message(
        tenant_id=tenant_id,
        contact_id=contact.id,
        channel=payload.channel,
        direction="in",
        text=payload.text,
    )
    db.add(msg)
    db.commit()

    # Find or create deal
    deal = (
        db.query(Deal)
        .filter(Deal.tenant_id == tenant_id)
        .filter(Deal.contact_id == contact.id)
        .filter(Deal.status == "open")
        .order_by(desc(Deal.id))
        .first()
    )
    if not deal:
        deal = Deal(
            tenant_id=tenant_id,
            contact_id=contact.id,
            stage="new",
            status="open",
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)

    # Simple bot reply + stage
    text_lower = payload.text.lower()
    if "price" in text_lower or "rate" in text_lower:
        reply = "Share your city + budget and I’ll finalize the order."
        deal.stage = "qualified"
    else:
        reply = "Thanks! Share your city + budget so I can guide you."
        deal.stage = deal.stage or "new"

    db.commit()

    # Store outbound message
    out_msg = Message(
        tenant_id=tenant_id,
        contact_id=contact.id,
        channel=payload.channel,
        direction="out",
        text=reply,
    )
    db.add(out_msg)
    db.commit()

    return {"ok": True, "reply": reply, "stage": deal.stage}
