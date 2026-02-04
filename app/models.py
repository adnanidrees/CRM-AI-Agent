from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, synonym


def utcnow_naive() -> datetime:
    # Naive UTC datetime (SQLite friendly)
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending/active

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    users: Mapped[List["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    channels: Mapped[List["ChannelAccount"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    contacts: Mapped[List["Contact"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    deals: Mapped[List["Deal"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    messages: Mapped[List["Message"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("name", name="uq_tenants_name"),)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # tenant_id NULL => superadmin/system user
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True)

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="tenant_admin")  # superadmin/tenant_admin/agent

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # ✅ add to prevent startup crash when bootstrap uses is_active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    tenant: Mapped[Optional["Tenant"]] = relationship(back_populates="users")
    otps: Mapped[List["OTP"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_tenant_id", "tenant_id"),
    )


class OTP(Base):
    __tablename__ = "otps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # email/phone
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # naive UTC (SQLite safe)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # ✅ main.py ke different versions "used" ya "is_used" pass karte hain
    used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_used = synonym("used")  # compatibility alias

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    user: Mapped["User"] = relationship(back_populates="otps")

    __table_args__ = (Index("ix_otps_user_kind", "user_id", "kind"),)


class ChannelAccount(Base):
    __tablename__ = "channel_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)  # whatsapp/instagram/facebook/email
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    app_secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    tenant: Mapped["Tenant"] = relationship(back_populates="channels")

    __table_args__ = (
        Index("ix_channel_accounts_tenant", "tenant_id"),
        Index("ix_channel_accounts_channel", "channel"),
    )


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    channel_user_id: Mapped[str] = mapped_column(String(100), nullable=False)

    contact_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    tenant: Mapped["Tenant"] = relationship(back_populates="contacts")
    deals: Mapped[List["Deal"]] = relationship(back_populates="contact", cascade="all, delete-orphan")
    messages: Mapped[List["Message"]] = relationship(back_populates="contact", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tenant_id", "channel", "channel_user_id", name="uq_contact_channel_user"),
        Index("ix_contacts_tenant", "tenant_id"),
    )


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    contact_id: Mapped[int] = mapped_column(Integer, ForeignKey("contacts.id"), nullable=False)

    stage: Mapped[str] = mapped_column(String(50), default="new")
    status: Mapped[str] = mapped_column(String(50), default="open")

    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    budget: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    tenant: Mapped["Tenant"] = relationship(back_populates="deals")
    contact: Mapped["Contact"] = relationship(back_populates="deals")

    __table_args__ = (Index("ix_deals_tenant", "tenant_id"),)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False)
    contact_id: Mapped[int] = mapped_column(Integer, ForeignKey("contacts.id"), nullable=False)

    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # in/out/system
    text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive)

    tenant: Mapped["Tenant"] = relationship(back_populates="messages")
    contact: Mapped["Contact"] = relationship(back_populates="messages")

    __table_args__ = (Index("ix_messages_tenant", "tenant_id"),)
