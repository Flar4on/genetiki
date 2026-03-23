from datetime import date, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import HOSPITALS, hospital_keyboard, main_menu, remove_keyboard
from src.services.baby_service import create_baby
from src.services.parent_service import get_parent_by_telegram_id

router = Router()


class BabyStates(StatesGroup):
    name = State()
    birth_date = State()
    hospital = State()


@router.message(F.text == "У меня родился ребёнок")
async def start_add_baby(message: Message, state: FSMContext, session: AsyncSession):
    parent = await get_parent_by_telegram_id(session, message.from_user.id)
    if not parent:
        await message.answer(
            "Сначала необходимо зарегистрироваться.\n"
            'Нажмите "Я беременна / готовлюсь к родам".',
            reply_markup=main_menu,
        )
        return

    await message.answer(
        "Поздравляем с рождением малыша!\n\n"
        "Введите имя ребёнка:",
        reply_markup=remove_keyboard,
    )
    await state.set_state(BabyStates.name)


@router.message(BabyStates.name)
async def process_baby_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите корректное имя:")
        return

    await state.update_data(name=name)
    await message.answer(
        "Введите дату рождения ребёнка (в формате ДД.ММ.ГГГГ):"
    )
    await state.set_state(BabyStates.birth_date)


@router.message(BabyStates.birth_date)
async def process_birth_date(message: Message, state: FSMContext):
    try:
        birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer(
            "Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ\n"
            "Например: 15.01.2026"
        )
        return

    if birth_date > date.today():
        await message.answer("Дата рождения не может быть в будущем. Попробуйте ещё раз:")
        return

    await state.update_data(birth_date=birth_date.isoformat())
    await message.answer(
        "В каком роддоме родился ребёнок?",
        reply_markup=hospital_keyboard(),
    )
    await state.set_state(BabyStates.hospital)


@router.callback_query(BabyStates.hospital, F.data.startswith("hospital_"))
async def process_hospital(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    idx = int(callback.data.split("_")[1])
    hospital = HOSPITALS[idx]
    data = await state.get_data()

    parent = await get_parent_by_telegram_id(session, callback.from_user.id)
    birth_date = date.fromisoformat(data["birth_date"])

    baby = await create_baby(
        session=session,
        parent_id=parent.id,
        name=data["name"],
        birth_date=birth_date,
        birth_hospital=hospital,
    )

    await state.clear()
    await callback.message.answer(
        f"Ребёнок {data['name']} добавлен!\n\n"
        f"Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
        f"Роддом: {hospital}\n\n"
        "Мы уведомим вас о результатах неонатального скрининга "
        "через этот бот. Пожалуйста, не отключайте уведомления.",
        reply_markup=main_menu,
    )
    await callback.answer()
