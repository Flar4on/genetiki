import asyncio
import hashlib
import logging
from datetime import date, datetime, timedelta, timezone

import uvicorn
from sqlalchemy import select

from src.api.app import create_app
from src.core.config import settings
from src.core.database import async_session, engine
from src.core.security import encrypt_pdn, hash_password
from src.models import Base
from src.models.baby import Baby
from src.models.notification import Notification, NotificationStatus
from src.models.parent import Parent
from src.models.screening import ResultType, ScreeningResult
from src.models.user import User, UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_ENABLED = settings.bot_token and settings.bot_token != "disabled"


async def create_tables():
    """Create tables if they don't exist (for development)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_admin_user():
    """Create default admin user if not exists."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.email == settings.admin_email)
        )
        if not result.scalar_one_or_none():
            admin = User(
                email=settings.admin_email,
                hashed_password=hash_password(settings.admin_password),
                full_name="Администратор",
                role=UserRole.admin,
            )
            session.add(admin)
            await session.commit()
            logger.info("Admin user created: %s", settings.admin_email)


async def create_test_data():
    """Create test parents with babies, screening results and notifications."""
    test_phone = "79991234567"
    phone_hash = hashlib.sha256(test_phone.encode()).hexdigest()

    async with async_session() as session:
        existing = await session.execute(
            select(Parent).where(Parent.phone_hash == phone_hash)
        )
        if existing.scalar_one_or_none():
            return

        # ── Test families ──
        families = [
            {
                "tid": 100000001, "name": "Иванова Мария Петровна",
                "phone": "+7 (999) 123-45-67", "region": "Якутск",
                "babies": [
                    {"name": "Иванов Артём", "bd": date(2025, 11, 15),
                     "hospital": "Перинатальный центр РБ№1-НЦМ", "collected": True},
                    {"name": "Иванова Алиса", "bd": date(2026, 2, 3),
                     "hospital": "Якутская городская больница №2", "collected": True},
                ],
            },
            {
                "tid": 100000002, "name": "Петрова Анна Сергеевна",
                "phone": "+7 (914) 200-00-02", "region": "Нерюнгри",
                "babies": [
                    {"name": "Петров Даниил", "bd": date(2026, 1, 10),
                     "hospital": "Нерюнгринская ЦРБ", "collected": True},
                ],
            },
            {
                "tid": 100000003, "name": "Сидорова Елена Ивановна",
                "phone": "+7 (914) 300-00-03", "region": "Мирный",
                "babies": [
                    {"name": "Сидоров Максим", "bd": date(2025, 12, 25),
                     "hospital": "Мирнинская ЦРБ", "collected": True},
                ],
            },
            {
                "tid": 100000004, "name": "Николаева Сардаана Дмитриевна",
                "phone": "+7 (914) 400-00-04", "region": "Вилюйск",
                "babies": [
                    {"name": "Николаев Айсен", "bd": date(2026, 1, 20),
                     "hospital": "Вилюйская ЦРБ", "collected": True},
                    {"name": "Николаева Куннэй", "bd": date(2026, 1, 20),
                     "hospital": "Вилюйская ЦРБ", "collected": True},
                ],
            },
            {
                "tid": 100000005, "name": "Фёдорова Туйаара Алексеевна",
                "phone": "+7 (914) 500-00-05", "region": "Алдан",
                "babies": [
                    {"name": "Фёдоров Тимур", "bd": date(2025, 10, 5),
                     "hospital": "Алданская ЦРБ", "collected": True},
                ],
            },
            {
                "tid": 100000006, "name": "Алексеева Нюргуяна Васильевна",
                "phone": "+7 (914) 600-00-06", "region": "Олёкминск",
                "babies": [
                    {"name": "Алексеев Эрхан", "bd": date(2026, 2, 14),
                     "hospital": "Олёкминская ЦРБ", "collected": True},
                ],
            },
            {
                "tid": 100000007, "name": "Васильева Айыына Николаевна",
                "phone": "+7 (914) 700-00-07", "region": "Ленск",
                "babies": [
                    {"name": "Васильев Арылхан", "bd": date(2025, 9, 18),
                     "hospital": "Ленская ЦРБ", "collected": True},
                ],
            },
            {
                "tid": 100000008, "name": "Егорова Сахаяна Петровна",
                "phone": "+7 (914) 800-00-08", "region": "Якутск",
                "babies": [
                    {"name": "Егорова Сайыына", "bd": date(2026, 2, 20),
                     "hospital": "Перинатальный центр РБ№1-НЦМ", "collected": False},
                ],
            },
            {
                "tid": 100000009, "name": "Михайлова Ольга Геннадьевна",
                "phone": "+7 (914) 900-00-09", "region": "Покровск",
                "babies": [
                    {"name": "Михайлов Илья", "bd": date(2025, 12, 1),
                     "hospital": "Хангаласская ЦРБ", "collected": True},
                ],
            },
            {
                "tid": 100000010, "name": "Попова Диана Руслановна",
                "phone": "+7 (914) 100-00-10", "region": "Намцы",
                "babies": [
                    {"name": "Попов Ньургун", "bd": date(2026, 1, 30),
                     "hospital": "Намская ЦРБ", "collected": True},
                ],
            },
        ]

        diseases = [
            ("E84", "Муковисцидоз"), ("E25", "Адреногенитальный синдром"),
            ("E03", "Врождённый гипотиреоз"), ("E70", "Фенилкетонурия"),
            ("E80.2", "Галактоземия"), ("D57", "Серповидноклеточная анемия"),
            ("E75.0", "Спинальная мышечная атрофия"),
        ]

        # Pre-define screening patterns per family for variety
        screening_patterns = [
            # family 0 (Иванова): 2 neg + 1 repeat + 1 neg
            [(0, "neg"), (1, "neg"), (2, "repeat"), (3, "neg")],
            # family 1 (Петрова): positive + notification escalated
            [(2, "pos"), (0, "neg"), (3, "neg")],
            # family 2 (Сидорова): all negative
            [(0, "neg"), (1, "neg"), (2, "neg"), (3, "neg"), (4, "neg")],
            # family 3 (Николаева): twins — repeat for one, neg for other
            [(2, "repeat"), (3, "neg")],  # baby 0
            # family 3 baby 1
            None,  # handled separately
            # family 4 (Фёдорова): positive
            [(0, "neg"), (6, "pos"), (3, "neg")],
            # family 5 (Алексеева): pending (no results yet)
            [],
            # family 6 (Васильева): all neg
            [(0, "neg"), (1, "neg"), (2, "neg")],
            # family 7 (Егорова): not collected yet
            [],
            # family 8 (Михайлова): repeat needed
            [(3, "repeat"), (0, "neg")],
            # family 9 (Попова): all neg
            [(0, "neg"), (2, "neg"), (3, "neg")],
        ]

        all_parents = []
        all_babies = []

        for i, fam in enumerate(families):
            phone_raw = "".join(c for c in fam["phone"] if c.isdigit())
            if phone_raw.startswith("8"):
                phone_raw = "7" + phone_raw[1:]
            p = Parent(
                telegram_id=fam["tid"],
                full_name=encrypt_pdn(fam["name"]),
                phone=encrypt_pdn(fam["phone"]),
                phone_hash=hashlib.sha256(phone_raw.encode()).hexdigest(),
                region=fam["region"],
                consent_given=True,
                is_active=True,
            )
            session.add(p)
            all_parents.append(p)

        await session.flush()

        for i, fam in enumerate(families):
            for b_data in fam["babies"]:
                baby = Baby(
                    parent_id=all_parents[i].id,
                    name=b_data["name"],
                    birth_date=b_data["bd"],
                    birth_hospital=b_data["hospital"],
                    sample_collected=b_data["collected"],
                )
                session.add(baby)
                all_babies.append((i, baby))

        await session.flush()

        # Create screening results and notifications
        baby_idx = 0
        for fam_idx, baby_obj in all_babies:
            # Determine which pattern to use
            # Map family babies to pattern index
            if fam_idx == 3 and baby_obj.name == "Николаева Куннэй":
                pattern = [(0, "neg"), (1, "neg"), (3, "neg")]
            else:
                pat_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10}
                pat_idx = pat_map.get(fam_idx, 0)
                if pat_idx < len(screening_patterns) and screening_patterns[pat_idx] is not None:
                    pattern = screening_patterns[pat_idx]
                else:
                    pattern = [(0, "neg"), (1, "neg")]

            base_date = datetime(
                baby_obj.birth_date.year, baby_obj.birth_date.month,
                min(baby_obj.birth_date.day + 5, 28), tzinfo=timezone.utc,
            )

            for dis_idx, res_type in pattern:
                code, name = diseases[dis_idx]
                rt = {"neg": ResultType.negative, "pos": ResultType.positive,
                      "repeat": ResultType.repeat_needed}[res_type]
                sr = ScreeningResult(
                    baby_id=baby_obj.id,
                    result_type=rt,
                    disease_code=code,
                    disease_name=name,
                    received_at=base_date,
                )
                session.add(sr)
                await session.flush()

                # Create notifications for non-negative results
                if rt == ResultType.positive:
                    parent = all_parents[fam_idx]
                    parent_name = fam["name"].split()[0]
                    n = Notification(
                        parent_id=parent.id,
                        screening_result_id=sr.id,
                        message_text=f"Внимание! У ребёнка {baby_obj.name} выявлен положительный результат скрининга ({name}). Необходима консультация генетика. Обратитесь в медико-генетический центр.",
                        status=NotificationStatus.escalated if fam_idx == 1 else NotificationStatus.sent,
                        sent_at=base_date + timedelta(hours=2),
                    )
                    session.add(n)
                elif rt == ResultType.repeat_needed:
                    parent = all_parents[fam_idx]
                    status = NotificationStatus.confirmed if fam_idx == 8 else NotificationStatus.sent
                    n = Notification(
                        parent_id=parent.id,
                        screening_result_id=sr.id,
                        message_text=f"По результатам скрининга для {baby_obj.name} требуется повторный забор крови ({name}). Пожалуйста, обратитесь в поликлинику.",
                        status=status,
                        sent_at=base_date + timedelta(hours=2),
                        confirmed_at=(base_date + timedelta(days=1)) if status == NotificationStatus.confirmed else None,
                    )
                    session.add(n)

            baby_idx += 1

        # Add extra info notifications for some parents
        for idx in [0, 2, 6, 9]:
            p = all_parents[idx]
            # Find first screening result for this parent's baby
            first_baby = [b for fi, b in all_babies if fi == idx][0]
            sr_result = await session.execute(
                select(ScreeningResult).where(ScreeningResult.baby_id == first_baby.id).limit(1)
            )
            sr_obj = sr_result.scalar_one_or_none()
            if sr_obj:
                n = Notification(
                    parent_id=p.id,
                    screening_result_id=sr_obj.id,
                    message_text=f"Результаты скрининга для {first_baby.name} получены. Все показатели в норме.",
                    status=NotificationStatus.confirmed,
                    sent_at=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
                    confirmed_at=datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc),
                )
                session.add(n)

        # Add a pending notification
        p5 = all_parents[5]
        baby5 = [b for fi, b in all_babies if fi == 5][0]
        sr5_result = await session.execute(
            select(ScreeningResult).where(ScreeningResult.baby_id == baby5.id).limit(1)
        )
        sr5_obj = sr5_result.scalar_one_or_none()
        if not sr5_obj:
            # No screening yet, create a placeholder
            sr5_obj = ScreeningResult(
                baby_id=baby5.id,
                result_type=ResultType.negative,
                disease_code="E84",
                disease_name="Муковисцидоз",
                received_at=datetime(2026, 2, 19, tzinfo=timezone.utc),
            )
            session.add(sr5_obj)
            await session.flush()
        n_pending = Notification(
            parent_id=p5.id,
            screening_result_id=sr5_obj.id,
            message_text=f"Результаты скрининга для {baby5.name} получены. Все показатели в норме.",
            status=NotificationStatus.pending,
        )
        session.add(n_pending)

        await session.commit()
        logger.info("Test data created: 10 families, portal login +7(999)123-45-67")


async def notification_worker():
    """Background worker that sends pending notifications via Telegram."""
    if not BOT_ENABLED:
        logger.warning("Bot disabled — notification worker skipped")
        return

    from src.bot.bot import bot
    from src.bot.keyboards import confirm_notification_keyboard
    from src.services.notification_service import (
        get_notifications_to_escalate,
        get_pending_notifications,
        mark_escalated,
        mark_sent,
    )

    logger.info("Notification worker started")
    while True:
        try:
            async with async_session() as session:
                pending = await get_pending_notifications(session)
                for notification in pending:
                    try:
                        parent = notification.parent
                        if not parent:
                            continue
                        keyboard = confirm_notification_keyboard(str(notification.id))
                        await bot.send_message(
                            chat_id=parent.telegram_id,
                            text=notification.message_text,
                            reply_markup=keyboard,
                        )
                        await mark_sent(session, notification.id)
                        logger.info("Notification %s sent to %s", notification.id, parent.telegram_id)
                    except Exception as e:
                        logger.error("Failed to send notification %s: %s", notification.id, e)

                to_escalate = await get_notifications_to_escalate(session)
                for notification in to_escalate:
                    await mark_escalated(session, notification.id)
                    logger.warning("Notification %s escalated", notification.id)
        except Exception as e:
            logger.error("Notification worker error: %s", e)

        await asyncio.sleep(60)


async def run_bot():
    """Start the Telegram bot polling."""
    if not BOT_ENABLED:
        logger.warning("BOT_TOKEN not set or disabled — bot will not start")
        return

    from src.bot.bot import bot, dp
    from src.bot.middlewares import DbSessionMiddleware
    from src.bot.routers.baby import router as baby_router
    from src.bot.routers.info import router as info_router
    from src.bot.routers.notifications import router as notif_router
    from src.bot.routers.registration import router as reg_router
    from src.bot.routers.start import router as start_router

    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.include_router(start_router)
    dp.include_router(reg_router)
    dp.include_router(baby_router)
    dp.include_router(info_router)
    dp.include_router(notif_router)

    logger.info("Bot starting polling...")
    await dp.start_polling(bot)


async def run_api():
    """Start the FastAPI server."""
    app = create_app()
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    logger.info("Starting РНС Якутия system...")

    await create_tables()
    await create_admin_user()
    await create_test_data()

    tasks = [run_api()]
    if BOT_ENABLED:
        tasks.append(run_bot())
        tasks.append(notification_worker())
    else:
        logger.warning("Running without Telegram bot (BOT_TOKEN=disabled)")

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
