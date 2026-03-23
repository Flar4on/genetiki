from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import main_menu
from src.services.parent_service import get_parent_by_telegram_id

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    parent = await get_parent_by_telegram_id(session, message.from_user.id)
    if parent:
        await message.answer(
            "С возвращением! Выберите действие:",
            reply_markup=main_menu,
        )
    else:
        await message.answer(
            "Добро пожаловать в систему расширенного неонатального скрининга "
            "Республики Саха (Якутия)!\n\n"
            "Этот бот поможет вам:\n"
            "- Узнать о неонатальном скрининге\n"
            "- Зарегистрировать данные вашего ребёнка\n"
            "- Получить результаты скрининга\n\n"
            "Выберите действие:",
            reply_markup=main_menu,
        )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=main_menu)
    await callback.answer()
