import hashlib
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decrypt_pdn, encrypt_pdn
from src.models.parent import Parent


def _normalize_phone(phone: str) -> str:
    """Normalize phone to digits only, ensure starts with 7."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits


def _hash_phone(phone: str) -> str:
    """SHA-256 hash of normalized phone for lookup."""
    normalized = _normalize_phone(phone)
    return hashlib.sha256(normalized.encode()).hexdigest()


async def get_parent_by_telegram_id(session: AsyncSession, telegram_id: int) -> Parent | None:
    result = await session.execute(select(Parent).where(Parent.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_parent_by_id(session: AsyncSession, parent_id: uuid.UUID) -> Parent | None:
    return await session.get(Parent, parent_id)


async def get_parent_by_phone_hash(session: AsyncSession, phone: str) -> Parent | None:
    """Find parent by phone number (hashed lookup)."""
    ph = _hash_phone(phone)
    result = await session.execute(
        select(Parent).where(Parent.phone_hash == ph, Parent.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def list_parents(
    session: AsyncSession, region: str | None = None, offset: int = 0, limit: int = 50
) -> list[Parent]:
    stmt = select(Parent).where(Parent.is_active.is_(True))
    if region:
        stmt = stmt.where(Parent.region == region)
    stmt = stmt.offset(offset).limit(limit).order_by(Parent.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_parents(session: AsyncSession, region: str | None = None) -> int:
    from sqlalchemy import func

    stmt = select(func.count(Parent.id)).where(Parent.is_active.is_(True))
    if region:
        stmt = stmt.where(Parent.region == region)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_parent(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    phone: str,
    region: str,
    consent_given: bool,
) -> Parent:
    parent = Parent(
        telegram_id=telegram_id,
        full_name=encrypt_pdn(full_name),
        phone=encrypt_pdn(phone),
        phone_hash=_hash_phone(phone),
        region=region,
        consent_given=consent_given,
    )
    session.add(parent)
    await session.commit()
    await session.refresh(parent)
    return parent


async def generate_otp(session: AsyncSession, parent: Parent) -> str:
    """Generate 6-digit OTP code, save to parent, return code."""
    code = f"{random.randint(0, 999999):06d}"
    parent.auth_code = code
    parent.auth_code_expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    await session.commit()
    return code


async def verify_otp(session: AsyncSession, parent: Parent, code: str) -> bool:
    """Verify OTP code. Returns True if valid, clears code after use."""
    if not parent.auth_code or not parent.auth_code_expires:
        return False
    if parent.auth_code != code:
        return False
    if datetime.now(timezone.utc) > parent.auth_code_expires:
        parent.auth_code = None
        parent.auth_code_expires = None
        await session.commit()
        return False
    # Valid — clear code
    parent.auth_code = None
    parent.auth_code_expires = None
    await session.commit()
    return True


def get_decrypted_name(parent: Parent) -> str:
    if parent.full_name:
        return decrypt_pdn(parent.full_name)
    return ""


def get_decrypted_phone(parent: Parent) -> str:
    if parent.phone:
        return decrypt_pdn(parent.phone)
    return ""
