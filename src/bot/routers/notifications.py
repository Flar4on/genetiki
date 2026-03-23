import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.notification_service import mark_confirmed

router = Router()


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_notification(callback: CallbackQuery, session: AsyncSession):
    notification_id_str = callback.data.replace("confirm_", "")
    try:
        notification_id = uuid.UUID(notification_id_str)
    except ValueError:
        await callback.answer("Ошибка обработки подтверждения.")
        return

    await mark_confirmed(session, notification_id)

    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Информация получена. Спасибо!",
    )
    await callback.answer("Спасибо за подтверждение!")
