"""
Vercel serverless entry point for НС Якутия (demo mode).

All data is stored in-memory using dataclasses instead of SQLAlchemy.
No database, Redis, or Max bot required.
"""

import hashlib
import os
import traceback
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import jwt

# ── Config ──

SECRET_KEY = "vercel-demo-rns-yakutia-2026"
ALGORITHM = "HS256"
ADMIN_EMAIL = "admin@rns.local"
ADMIN_PASSWORD = "123"
PORTAL_PASSWORD = "123"


def _find_base_dir() -> str:
    """Find the project root by looking for src/admin/templates/."""
    candidates = [
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
        "/var/task",
        "/var/task/user",
    ]
    for c in candidates:
        if os.path.isdir(os.path.join(c, "src", "admin", "templates")):
            return c
    return candidates[0]


BASE_DIR = _find_base_dir()


# ── JWT helpers ──


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(hours=24)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ── Enums (must match templates' .value checks) ──


class UserRole(str, Enum):
    admin = "admin"
    geneticist = "geneticist"
    pediatrician = "pediatrician"


class ResultType(str, Enum):
    positive = "positive"
    negative = "negative"
    repeat_needed = "repeat_needed"


class NotificationStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    delivered = "delivered"
    confirmed = "confirmed"
    escalated = "escalated"


# ── Dataclass models ──


def _uuid(name: str) -> uuid.UUID:
    """Deterministic UUID so IDs survive cold restarts."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"rns.demo.{name}")


@dataclass
class User:
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ScreeningResult:
    id: uuid.UUID
    baby_id: uuid.UUID
    result_type: ResultType
    disease_code: Optional[str] = None
    disease_name: Optional[str] = None
    received_at: Optional[datetime] = None
    source: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Baby:
    id: uuid.UUID
    parent_id: uuid.UUID
    name: Optional[str] = None
    birth_date: Optional[date] = None
    birth_hospital: Optional[str] = None
    sample_collected: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    screening_results: list = field(default_factory=list)


@dataclass
class Notification:
    id: uuid.UUID
    parent_id: uuid.UUID
    screening_result_id: uuid.UUID
    message_text: str
    status: NotificationStatus = NotificationStatus.pending
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Parent:
    id: uuid.UUID
    telegram_id: int
    full_name: Optional[str] = None
    phone: Optional[str] = None
    phone_hash: Optional[str] = None
    region: Optional[str] = None
    registration_date: Optional[datetime] = None
    consent_given: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    babies: list = field(default_factory=list)
    notifications: list = field(default_factory=list)


# ── In-memory store ──

DB: dict = {"users": [], "parents": [], "babies": [], "screenings": [], "notifications": []}


def _phone_hash(phone: str) -> str:
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return hashlib.sha256(digits.encode()).hexdigest()


def seed_data():
    """Populate DB with the same 10 families as create_test_data()."""
    if DB["parents"]:
        return

    admin = User(
        id=_uuid("admin"),
        email=ADMIN_EMAIL,
        full_name="Администратор",
        role=UserRole.admin,
    )
    DB["users"].append(admin)

    families = [
        {"tid": 100000001, "name": "Иванова Мария Петровна", "phone": "+7 (999) 123-45-67", "region": "Якутск",
         "babies": [
             {"name": "Иванов Артём", "bd": date(2025, 11, 15), "hospital": "Перинатальный центр РБ№1-НЦМ", "collected": True},
             {"name": "Иванова Алиса", "bd": date(2026, 2, 3), "hospital": "Якутская городская больница №2", "collected": True},
         ]},
        {"tid": 100000002, "name": "Петрова Анна Сергеевна", "phone": "+7 (914) 200-00-02", "region": "Нерюнгри",
         "babies": [{"name": "Петров Даниил", "bd": date(2026, 1, 10), "hospital": "Нерюнгринская ЦРБ", "collected": True}]},
        {"tid": 100000003, "name": "Сидорова Елена Ивановна", "phone": "+7 (914) 300-00-03", "region": "Мирный",
         "babies": [{"name": "Сидоров Максим", "bd": date(2025, 12, 25), "hospital": "Мирнинская ЦРБ", "collected": True}]},
        {"tid": 100000004, "name": "Николаева Сардаана Дмитриевна", "phone": "+7 (914) 400-00-04", "region": "Вилюйск",
         "babies": [
             {"name": "Николаев Айсен", "bd": date(2026, 1, 20), "hospital": "Вилюйская ЦРБ", "collected": True},
             {"name": "Николаева Куннэй", "bd": date(2026, 1, 20), "hospital": "Вилюйская ЦРБ", "collected": True},
         ]},
        {"tid": 100000005, "name": "Фёдорова Туйаара Алексеевна", "phone": "+7 (914) 500-00-05", "region": "Алдан",
         "babies": [{"name": "Фёдоров Тимур", "bd": date(2025, 10, 5), "hospital": "Алданская ЦРБ", "collected": True}]},
        {"tid": 100000006, "name": "Алексеева Нюргуяна Васильевна", "phone": "+7 (914) 600-00-06", "region": "Олёкминск",
         "babies": [{"name": "Алексеев Эрхан", "bd": date(2026, 2, 14), "hospital": "Олёкминская ЦРБ", "collected": True}]},
        {"tid": 100000007, "name": "Васильева Айыына Николаевна", "phone": "+7 (914) 700-00-07", "region": "Ленск",
         "babies": [{"name": "Васильев Арылхан", "bd": date(2025, 9, 18), "hospital": "Ленская ЦРБ", "collected": True}]},
        {"tid": 100000008, "name": "Егорова Сахаяна Петровна", "phone": "+7 (914) 800-00-08", "region": "Якутск",
         "babies": [{"name": "Егорова Сайыына", "bd": date(2026, 2, 20), "hospital": "Перинатальный центр РБ№1-НЦМ", "collected": False}]},
        {"tid": 100000009, "name": "Михайлова Ольга Геннадьевна", "phone": "+7 (914) 900-00-09", "region": "Покровск",
         "babies": [{"name": "Михайлов Илья", "bd": date(2025, 12, 1), "hospital": "Хангаласская ЦРБ", "collected": True}]},
        {"tid": 100000010, "name": "Попова Диана Руслановна", "phone": "+7 (914) 100-00-10", "region": "Намцы",
         "babies": [{"name": "Попов Ньургун", "bd": date(2026, 1, 30), "hospital": "Намская ЦРБ", "collected": True}]},
    ]

    diseases = [
        ("E84", "Муковисцидоз"), ("E25", "Адреногенитальный синдром"),
        ("E03", "Врождённый гипотиреоз"), ("E70", "Фенилкетонурия"),
        ("E80.2", "Галактоземия"), ("D57", "Серповидноклеточная анемия"),
        ("E75.0", "Спинальная мышечная атрофия"),
    ]

    screening_map = {
        "Иванов Артём": [(0, "neg"), (1, "neg")],
        "Иванова Алиса": [(2, "repeat"), (3, "neg")],
        "Петров Даниил": [(2, "pos"), (0, "neg"), (3, "neg")],
        "Сидоров Максим": [(0, "neg"), (1, "neg"), (2, "neg"), (3, "neg"), (4, "neg")],
        "Николаев Айсен": [(2, "repeat"), (3, "neg")],
        "Николаева Куннэй": [(0, "neg"), (1, "neg"), (3, "neg")],
        "Фёдоров Тимур": [(0, "neg"), (6, "pos"), (3, "neg")],
        "Алексеев Эрхан": [],
        "Васильев Арылхан": [(0, "neg"), (1, "neg"), (2, "neg")],
        "Егорова Сайыына": [],
        "Михайлов Илья": [(3, "repeat"), (0, "neg")],
        "Попов Ньургун": [(0, "neg"), (2, "neg"), (3, "neg")],
    }

    rt_map = {"neg": ResultType.negative, "pos": ResultType.positive, "repeat": ResultType.repeat_needed}

    sr_counter = 0
    notif_counter = 0

    for fi, fam in enumerate(families):
        parent = Parent(
            id=_uuid(f"parent-{fi}"),
            telegram_id=fam["tid"],
            full_name=fam["name"],
            phone=fam["phone"],
            phone_hash=_phone_hash(fam["phone"]),
            region=fam["region"],
            registration_date=datetime(2025, 10, 1, tzinfo=timezone.utc) + timedelta(days=fi * 7),
            consent_given=True,
            is_active=True,
        )
        DB["parents"].append(parent)

        for bi, b_data in enumerate(fam["babies"]):
            baby = Baby(
                id=_uuid(f"baby-{fi}-{bi}"),
                parent_id=parent.id,
                name=b_data["name"],
                birth_date=b_data["bd"],
                birth_hospital=b_data["hospital"],
                sample_collected=b_data["collected"],
            )
            DB["babies"].append(baby)
            parent.babies.append(baby)

            pattern = screening_map.get(b_data["name"], [])
            base_dt = datetime(b_data["bd"].year, b_data["bd"].month,
                               min(b_data["bd"].day + 5, 28), tzinfo=timezone.utc)

            for dis_idx, res_key in pattern:
                code, dname = diseases[dis_idx]
                sr = ScreeningResult(
                    id=_uuid(f"sr-{sr_counter}"),
                    baby_id=baby.id,
                    result_type=rt_map[res_key],
                    disease_code=code,
                    disease_name=dname,
                    received_at=base_dt,
                )
                DB["screenings"].append(sr)
                baby.screening_results.append(sr)
                sr_counter += 1

                if rt_map[res_key] == ResultType.positive:
                    n = Notification(
                        id=_uuid(f"notif-{notif_counter}"),
                        parent_id=parent.id,
                        screening_result_id=sr.id,
                        message_text=f"Внимание! У ребёнка {baby.name} выявлен положительный результат скрининга ({dname}). Необходима консультация генетика.",
                        status=NotificationStatus.escalated if fi == 1 else NotificationStatus.sent,
                        sent_at=base_dt + timedelta(hours=2),
                    )
                    DB["notifications"].append(n)
                    parent.notifications.append(n)
                    notif_counter += 1
                elif rt_map[res_key] == ResultType.repeat_needed:
                    status = NotificationStatus.confirmed if fi == 8 else NotificationStatus.sent
                    n = Notification(
                        id=_uuid(f"notif-{notif_counter}"),
                        parent_id=parent.id,
                        screening_result_id=sr.id,
                        message_text=f"По результатам скрининга для {baby.name} требуется повторный забор крови ({dname}). Обратитесь в поликлинику.",
                        status=status,
                        sent_at=base_dt + timedelta(hours=2),
                        confirmed_at=(base_dt + timedelta(days=1)) if status == NotificationStatus.confirmed else None,
                    )
                    DB["notifications"].append(n)
                    parent.notifications.append(n)
                    notif_counter += 1

    for idx in [0, 2, 6, 9]:
        p = DB["parents"][idx]
        if p.babies and p.babies[0].screening_results:
            sr0 = p.babies[0].screening_results[0]
            n = Notification(
                id=_uuid(f"notif-{notif_counter}"),
                parent_id=p.id,
                screening_result_id=sr0.id,
                message_text=f"Результаты скрининга для {p.babies[0].name} получены. Все показатели в норме.",
                status=NotificationStatus.confirmed,
                sent_at=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
                confirmed_at=datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc),
            )
            DB["notifications"].append(n)
            p.notifications.append(n)
            notif_counter += 1

    p5 = DB["parents"][5]
    if p5.babies:
        sr_placeholder = ScreeningResult(
            id=_uuid(f"sr-{sr_counter}"),
            baby_id=p5.babies[0].id,
            result_type=ResultType.negative,
            disease_code="E84",
            disease_name="Муковисцидоз",
            received_at=datetime(2026, 2, 19, tzinfo=timezone.utc),
        )
        DB["screenings"].append(sr_placeholder)
        p5.babies[0].screening_results.append(sr_placeholder)

        n = Notification(
            id=_uuid(f"notif-{notif_counter}"),
            parent_id=p5.id,
            screening_result_id=sr_placeholder.id,
            message_text=f"Результаты скрининга для {p5.babies[0].name} получены. Все показатели в норме.",
            status=NotificationStatus.pending,
            created_at=datetime(2026, 2, 19, 12, 0, tzinfo=timezone.utc),
        )
        DB["notifications"].append(n)
        p5.notifications.append(n)


seed_data()


# ── FastAPI app ──

app = FastAPI(title="НС Якутия (Демо)")

admin_tpl = Jinja2Templates(directory=os.path.join(BASE_DIR, "src", "admin", "templates"))
portal_tpl = Jinja2Templates(directory=os.path.join(BASE_DIR, "src", "portal", "templates"))
landing_tpl = Jinja2Templates(directory=os.path.join(BASE_DIR, "src"))

static_dir = os.path.join(BASE_DIR, "src", "admin", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── Template helper — compatible with both old and new Starlette ──


def _render(tpl: Jinja2Templates, request: Request, name: str, ctx: Optional[dict] = None):
    """Render template with compatibility for all FastAPI/Starlette versions."""
    context = ctx or {}
    context["request"] = request
    try:
        # Starlette >= 0.37 (new API): request is first positional arg
        return tpl.TemplateResponse(request, name=name, context=context)
    except TypeError:
        # Starlette < 0.37 (old API): name is first positional arg
        return tpl.TemplateResponse(name=name, context=context)


# ── Debug ──


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return _render(landing_tpl, request, "landing.html")


# ── Helpers ──


def _find_parent_by_phone(phone: str) -> Optional[Parent]:
    ph = _phone_hash(phone)
    for p in DB["parents"]:
        if p.phone_hash == ph and p.is_active:
            return p
    return None


def _find_parent_by_id(parent_id: str) -> Optional[Parent]:
    try:
        uid = uuid.UUID(parent_id)
    except ValueError:
        return None
    for p in DB["parents"]:
        if p.id == uid:
            return p
    return None


def _get_admin(request: Request) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if not email:
            return None
    except Exception:
        return None
    for u in DB["users"]:
        if u.email == email:
            return u
    return None


def _get_portal_parent(request: Request) -> Optional[Parent]:
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
    return _find_parent_by_id(parent_id)


# ══════════════════════════════════════════════
#  DEMO AUTO-LOGIN
# ══════════════════════════════════════════════


@app.get("/demo/admin")
async def demo_admin():
    """Auto-login as admin and redirect to dashboard."""
    token = create_access_token({"sub": ADMIN_EMAIL, "role": "admin"})
    response = RedirectResponse(url="/admin/", status_code=302)
    response.set_cookie("access_token", token, httponly=True, max_age=86400)
    return response


@app.get("/demo/portal")
async def demo_portal():
    """Auto-login as first parent and redirect to portal."""
    parent = DB["parents"][0]
    token = create_access_token({"parent_id": str(parent.id), "type": "portal"})
    response = RedirectResponse(url="/portal/", status_code=302)
    response.set_cookie("portal_token", token, httponly=True, max_age=86400)
    return response


# ══════════════════════════════════════════════
#  ADMIN ROUTES
# ══════════════════════════════════════════════


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return _render(admin_tpl, request, "login.html")


@app.post("/admin/login")
async def admin_login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    if email != ADMIN_EMAIL or password != ADMIN_PASSWORD:
        return _render(admin_tpl, request, "login.html", {"error": "Неверный email или пароль"})

    token = create_access_token({"sub": email, "role": "admin"})
    response = RedirectResponse(url="/admin/", status_code=302)
    response.set_cookie("access_token", token, httponly=True, max_age=86400)
    return response


@app.get("/admin/logout")
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    return _render(admin_tpl, request, "dashboard.html", {
        "user": user,
        "total_parents": len(DB["parents"]),
        "total_babies": len(DB["babies"]),
        "total_screenings": len(DB["screenings"]),
        "positive_count": sum(1 for s in DB["screenings"] if s.result_type == ResultType.positive),
        "pending_notifs": sum(1 for n in DB["notifications"] if n.status in (NotificationStatus.pending, NotificationStatus.sent)),
        "confirmed_notifs": sum(1 for n in DB["notifications"] if n.status == NotificationStatus.confirmed),
    })


@app.get("/admin/parents", response_class=HTMLResponse)
async def admin_parents(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    parents = [{
        "id": str(p.id),
        "full_name": p.full_name,
        "phone": p.phone,
        "region": p.region,
        "registration_date": p.registration_date.strftime("%d.%m.%Y") if p.registration_date else "—",
        "babies_count": len(p.babies),
    } for p in DB["parents"]]

    return _render(admin_tpl, request, "parents.html", {"user": user, "parents": parents})


@app.get("/admin/babies", response_class=HTMLResponse)
async def admin_babies(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    return _render(admin_tpl, request, "babies.html", {"user": user, "babies": DB["babies"]})


@app.get("/admin/screening", response_class=HTMLResponse)
async def admin_screening(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    return _render(admin_tpl, request, "screening.html", {"user": user, "results": DB["screenings"]})


@app.get("/admin/notifications", response_class=HTMLResponse)
async def admin_notifications(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    return _render(admin_tpl, request, "notifications.html", {"user": user, "notifications": DB["notifications"]})


@app.get("/admin/analytics", response_class=HTMLResponse)
async def admin_analytics(request: Request):
    user = _get_admin(request)
    if not user:
        return RedirectResponse(url="/admin/login", status_code=302)

    region_counter = Counter(p.region for p in DB["parents"] if p.region)
    region_stats = [{"region": r, "count": c} for r, c in region_counter.most_common()]

    return _render(admin_tpl, request, "analytics.html", {"user": user, "region_stats": region_stats})


# ══════════════════════════════════════════════
#  PORTAL ROUTES
# ══════════════════════════════════════════════


@app.get("/portal/login", response_class=HTMLResponse)
async def portal_login_page(request: Request):
    return _render(portal_tpl, request, "portal_login.html")


@app.post("/portal/login")
async def portal_login_submit(request: Request, phone: str = Form(...), password: str = Form(...)):
    parent = _find_parent_by_phone(phone)
    if not parent:
        return _render(portal_tpl, request, "portal_login.html", {
            "error": "Номер не найден.",
        })

    if password != PORTAL_PASSWORD:
        return _render(portal_tpl, request, "portal_login.html", {
            "error": "Неверный пароль.",
        })

    token = create_access_token({"parent_id": str(parent.id), "type": "portal"})
    response = RedirectResponse(url="/portal/", status_code=302)
    response.set_cookie("portal_token", token, httponly=True, max_age=86400)
    return response


@app.get("/portal/logout")
async def portal_logout():
    response = RedirectResponse(url="/portal/login", status_code=302)
    response.delete_cookie("portal_token")
    return response


@app.get("/portal/", response_class=HTMLResponse)
async def portal_dashboard(request: Request):
    parent = _get_portal_parent(request)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    recent = sorted(parent.notifications, key=lambda n: n.created_at, reverse=True)[:5]

    return _render(portal_tpl, request, "portal_dashboard.html", {
        "parent": parent,
        "parent_name": parent.full_name,
        "parent_phone": parent.phone,
        "babies": parent.babies,
        "recent_notifications": recent,
    })


@app.get("/portal/children", response_class=HTMLResponse)
async def portal_children(request: Request):
    parent = _get_portal_parent(request)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    return _render(portal_tpl, request, "portal_children.html", {
        "parent": parent,
        "parent_name": parent.full_name,
        "babies": parent.babies,
    })


@app.get("/portal/notifications", response_class=HTMLResponse)
async def portal_notifications(request: Request):
    parent = _get_portal_parent(request)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    notifs = sorted(parent.notifications, key=lambda n: n.created_at, reverse=True)

    return _render(portal_tpl, request, "portal_notifications.html", {
        "parent": parent,
        "parent_name": parent.full_name,
        "notifications": notifs,
    })


@app.post("/portal/notifications/{notification_id}/confirm")
async def portal_confirm_notification(notification_id: str, request: Request):
    parent = _get_portal_parent(request)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    try:
        nid = uuid.UUID(notification_id)
    except ValueError:
        return RedirectResponse(url="/portal/notifications", status_code=302)

    for n in parent.notifications:
        if n.id == nid:
            n.status = NotificationStatus.confirmed
            n.confirmed_at = datetime.now(timezone.utc)
            break

    return RedirectResponse(url="/portal/notifications", status_code=302)


@app.get("/portal/info", response_class=HTMLResponse)
async def portal_info(request: Request):
    parent = _get_portal_parent(request)
    if not parent:
        return RedirectResponse(url="/portal/login", status_code=302)

    return _render(portal_tpl, request, "portal_info.html", {
        "parent": parent,
        "parent_name": parent.full_name,
    })


