import logging
import os
import uuid

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.core.config import settings
from src.core.security import create_access_token, decode_access_token
from src.models.notification import Notification, NotificationStatus
from src.models.parent import Parent
from src.services.notification_service import mark_confirmed
from src.services.parent_service import (
    generate_otp,
    get_decrypted_name,
    get_decrypted_phone,
    get_parent_by_phone_hash,
    verify_otp,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["portal"])

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


async def _get_portal_parent(request: Request, session: AsyncSession) -> Parent | None:
    token = request.cookies.get("portal_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        parent_id = payload.get("parent_id")
        if not parent_id:
            return None
    except Exception:
        return None
    return await session.get(Parent, uuid.UUID(parent_id))


# --- Login flow ---


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("portal_login.html", {"request": request, "step": "phone"})


@router.post("/login/send-code")
async def send_code(
    request: Request,
    phone: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    parent = await get_parent_by_phone_hash(session, phone)
    if not parent:
        return templates.TemplateResponse(
            "portal_login.html",
            {
                "request": request,
                "step": "phone",
                "error": "Номер не найден. Сначала зарегистрируйтесь через Telegram-бот.",
            },
        )

    code = await generate_otp(session, parent)

    # Send code via Telegram (or log if bot is disabled)
    bot_enabled = settings.bot_token and settings.bot_token != "disabled"
    if bot_enabled:
        try:
            from src.bot.bot import bot

            await bot.send_message(
                chat_id=parent.telegram_id,
                text=f"Ваш код для входа на портал РНС: <b>{code}</b>\n\nКод действителен 5 минут.",
            )
        except Exception as e:
            logger.error("Failed to send OTP to %s: %s", parent.telegram_id, e)
            return templates.TemplateResponse(
                "portal_login.html",
                {
                    "request": request,
                    "step": "phone",
                    "error": "Не удалось отправить код. Проверьте, что бот активен в Telegram.",
                },
            )
    else:
        # Dev mode: log the code
        logger.warning("BOT DISABLED — OTP code for %s: %s", parent.telegram_id, code)

    return templates.TemplateResponse(
        "portal_login.html",
        {"request": request, "step": "code", "phone": phone},
    )


@router.post("/login/verify")
async def verify_code(
    request: Request,
    phone: str = Form(...),
    code: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    parent = await get_parent_by_phone_hash(session, phone)
    if not parent:
        return templates.TemplateResponse(
            "portal_login.html",
            {"request": request, "step": "phone", "error": "Номер не найден."},
        )

    if not await verify_otp(session, parent, code.strip()):
        return templates.TemplateResponse(
            "portal_login.html",
            {
                "request": request,
                "step": "code",
                "phone": phone,
                "error": "Неверный или просроченный код. Попробуйте ещё раз.",
            },
        )

    token = create_access_token({"parent_id": str(parent.id), "type": "portal"})
    response = RedirectResponse(url="/portal/", status_code=302)
    response.set_cookie("portal_token", token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/portal/login", status_code=302)
    response.delete_cookie("portal_token")
    return response


# --- Dashboard ---


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_db)):
    parent = await _get_portal_parent(request, session)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    # Recent notifications (last 5)
    result = await session.execute(
        select(Notification)
        .where(Notification.parent_id == parent.id)
        .order_by(Notification.created_at.desc())
        .limit(5)
    )
    recent_notifications = result.scalars().all()

    return templates.TemplateResponse(
        "portal_dashboard.html",
        {
            "request": request,
            "parent": parent,
            "parent_name": get_decrypted_name(parent),
            "parent_phone": get_decrypted_phone(parent),
            "babies": parent.babies or [],
            "recent_notifications": recent_notifications,
        },
    )


# --- Children ---


@router.get("/children", response_class=HTMLResponse)
async def children_page(request: Request, session: AsyncSession = Depends(get_db)):
    parent = await _get_portal_parent(request, session)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    return templates.TemplateResponse(
        "portal_children.html",
        {
            "request": request,
            "parent": parent,
            "parent_name": get_decrypted_name(parent),
            "babies": parent.babies or [],
        },
    )


# --- Notifications ---


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, session: AsyncSession = Depends(get_db)):
    parent = await _get_portal_parent(request, session)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    result = await session.execute(
        select(Notification)
        .where(Notification.parent_id == parent.id)
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()

    return templates.TemplateResponse(
        "portal_notifications.html",
        {
            "request": request,
            "parent": parent,
            "parent_name": get_decrypted_name(parent),
            "notifications": notifications,
        },
    )


@router.post("/notifications/{notification_id}/confirm")
async def confirm_notification(
    notification_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    parent = await _get_portal_parent(request, session)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    notification = await session.get(Notification, notification_id)
    if notification and notification.parent_id == parent.id:
        await mark_confirmed(session, notification_id)

    return RedirectResponse(url="/portal/notifications", status_code=302)


# --- Info ---


@router.get("/info", response_class=HTMLResponse)
async def info_page(request: Request, session: AsyncSession = Depends(get_db)):
    parent = await _get_portal_parent(request, session)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    return templates.TemplateResponse(
        "portal_info.html",
        {
            "request": request,
            "parent": parent,
            "parent_name": get_decrypted_name(parent),
        },
    )
