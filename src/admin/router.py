import os

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db
from src.core.security import create_access_token, decode_access_token, verify_password
from src.models.baby import Baby
from src.models.notification import Notification, NotificationStatus
from src.models.parent import Parent
from src.models.screening import ResultType, ScreeningResult
from src.models.user import User
from src.services.parent_service import get_decrypted_name, get_decrypted_phone

router = APIRouter(prefix="/admin", tags=["admin"])

templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


def _get_token(request: Request) -> str | None:
    return request.cookies.get("access_token")


async def _get_admin_user(request: Request, session: AsyncSession) -> User | None:
    token = _get_token(request)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if not email:
            return None
    except Exception:
        return None
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Неверный email или пароль"}
        )

    token = create_access_token({"sub": user.email, "role": user.role.value})
    response = RedirectResponse(url="/admin/", status_code=302)
    response.set_cookie("access_token", token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_db)):
    user = await _get_admin_user(request, session)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    total_parents = (await session.execute(select(func.count(Parent.id)))).scalar_one()
    total_babies = (await session.execute(select(func.count(Baby.id)))).scalar_one()
    total_screenings = (
        await session.execute(select(func.count(ScreeningResult.id)))
    ).scalar_one()
    positive_count = (
        await session.execute(
            select(func.count(ScreeningResult.id)).where(
                ScreeningResult.result_type == ResultType.positive
            )
        )
    ).scalar_one()
    pending_notifs = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.status.in_(
                    [NotificationStatus.pending, NotificationStatus.sent]
                )
            )
        )
    ).scalar_one()
    confirmed_notifs = (
        await session.execute(
            select(func.count(Notification.id)).where(
                Notification.status == NotificationStatus.confirmed
            )
        )
    ).scalar_one()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "total_parents": total_parents,
            "total_babies": total_babies,
            "total_screenings": total_screenings,
            "positive_count": positive_count,
            "pending_notifs": pending_notifs,
            "confirmed_notifs": confirmed_notifs,
        },
    )


@router.get("/parents", response_class=HTMLResponse)
async def parents_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await _get_admin_user(request, session)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await session.execute(
        select(Parent).where(Parent.is_active.is_(True)).order_by(Parent.created_at.desc()).limit(100)
    )
    parents_raw = result.scalars().all()
    parents = []
    for p in parents_raw:
        parents.append(
            {
                "id": str(p.id),
                "full_name": get_decrypted_name(p),
                "phone": get_decrypted_phone(p),
                "region": p.region,
                "registration_date": p.registration_date.strftime("%d.%m.%Y") if p.registration_date else "—",
                "babies_count": len(p.babies) if p.babies else 0,
            }
        )

    return templates.TemplateResponse(
        "parents.html", {"request": request, "user": user, "parents": parents}
    )


@router.get("/babies", response_class=HTMLResponse)
async def babies_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await _get_admin_user(request, session)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await session.execute(
        select(Baby).order_by(Baby.created_at.desc()).limit(100)
    )
    babies = result.scalars().all()

    return templates.TemplateResponse(
        "babies.html", {"request": request, "user": user, "babies": babies}
    )


@router.get("/screening", response_class=HTMLResponse)
async def screening_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await _get_admin_user(request, session)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await session.execute(
        select(ScreeningResult).order_by(ScreeningResult.received_at.desc()).limit(100)
    )
    results = result.scalars().all()

    return templates.TemplateResponse(
        "screening.html", {"request": request, "user": user, "results": results}
    )


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await _get_admin_user(request, session)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    result = await session.execute(
        select(Notification).order_by(Notification.created_at.desc()).limit(100)
    )
    notifications = result.scalars().all()

    return templates.TemplateResponse(
        "notifications.html",
        {"request": request, "user": user, "notifications": notifications},
    )


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await _get_admin_user(request, session)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    # Region stats
    region_result = await session.execute(
        select(Parent.region, func.count(Parent.id).label("cnt"))
        .where(Parent.is_active.is_(True), Parent.region.isnot(None))
        .group_by(Parent.region)
        .order_by(func.count(Parent.id).desc())
    )
    region_stats = [{"region": r.region, "count": r.cnt} for r in region_result.all()]

    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "user": user, "region_stats": region_stats},
    )
