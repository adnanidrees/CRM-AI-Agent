from __future__ import annotations
import secrets
from datetime import datetime, timedelta
from passlib.context import CryptContext

# Use PBKDF2 to avoid bcrypt backend/version issues on Windows.
pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"

def hash_code(code: str) -> str:
    return pwd.hash(code)

def verify_code(code: str, hashed: str) -> bool:
    return pwd.verify(code, hashed)

def expires_in(minutes: int):
    return datetime.utcnow() + timedelta(minutes=minutes)

def send_email_mock(to_email: str, code: str):
    print(f"[MOCK EMAIL OTP] to={to_email} code={code}")

def send_sms_mock(to_phone: str, code: str):
    print(f"[MOCK SMS OTP] to={to_phone} code={code}")
