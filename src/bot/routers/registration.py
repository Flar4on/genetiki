from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards import (
    YAKUTIA_REGIONS,
    consent_keyboard,
    main_menu,
    region_keyboard,
    remove_keyboard,
    share_contact,
)
from src.services.parent_service import create_parent, get_parent_by_telegram_id

router = Router()


class RegistrationStates(StatesGroup):
    full_name = State()
    phone = State()
    region = State()
    consent = State()


@router.message(F.text == "Я беременна / готовлюсь к родам")
async def start_registration(message: Message, state: FSMContext, session: AsyncSession):
    parent = await get_parent_by_telegram_id(session, message.from_user.id)
    if parent:
        await message.answer(
            "Вы уже зарегистрированы! Можете добавить ребёнка или "
            "посмотреть информацию о скрининге.",
            reply_markup=main_menu,
        )
        return

    await message.answer(
        "Давайте пройдём регистрацию.\n\n"
        "Введите ваше ФИО (полностью):",
        reply_markup=remove_keyboard,
    )
    await state.set_state(RegistrationStates.full_name)


@router.message(RegistrationStates.full_name)
async def process_full_name(message: Message, state: FSMContext):
    if len(message.text.strip()) < 3:
        await message.answer("Пожалуйста, введите корректное ФИО:")
        return

    await state.update_data(full_name=message.text.strip())
    await message.answer(
        "Отлично! Теперь поделитесь номером телефона.\n"
        "Нажмите кнопку ниже или введите номер вручную:",
        reply_markup=share_contact,
    )
    await state.set_state(RegistrationStates.phone)


@router.message(RegistrationStates.phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await message.answer(
        "Выберите ваш район:",
        reply_markup=region_keyboard(),
    )
    await state.set_state(RegistrationStates.region)


@router.message(RegistrationStates.phone)
async def process_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    # Basic phone validation
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 10:
        await message.answer(
            "Пожалуйста, введите корректный номер телефона "
            "(минимум 10 цифр) или нажмите кнопку:",
            reply_markup=share_contact,
        )
        return

    await state.update_data(phone=phone)
    await message.answer(
        "Выберите ваш район:",
        reply_markup=region_keyboard(),
    )
    await state.set_state(RegistrationStates.region)


@router.callback_query(RegistrationStates.region, F.data.startswith("region_"))
async def process_region(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    region = YAKUTIA_REGIONS[idx]
    await state.update_data(region=region)

    await callback.message.answer(
        f"Район: {region}\n\n"
        "Для работы с вашими данными нам необходимо ваше согласие "
        "на обработку персональных данных в соответствии с "
        "Федеральным законом №152-ФЗ.\n\n"
        "Ваши данные будут использованы исключительно для "
        "информирования о результатах неонатального скрининга.",
        reply_markup=consent_keyboard,
    )
    await state.set_state(RegistrationStates.consent)
    await callback.answer()


@router.callback_query(RegistrationStates.consent, F.data == "consent_yes")
async def process_consent_yes(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()

    await create_parent(
        session=session,
        telegram_id=callback.from_user.id,
        full_name=data["full_name"],
        phone=data["phone"],
        region=data["region"],
        consent_given=True,
    )

    await state.clear()
    await callback.message.answer(
        "Вы успешно зарегистрированы!\n\n"
        "Теперь вы сможете получать уведомления о результатах "
        "неонатального скрининга вашего ребёнка.\n\n"
        "Когда ваш малыш родится, не забудьте добавить его данные "
        'через кнопку "У меня родился ребёнок".',
        reply_markup=main_menu,
    )
    await callback.answer()


@router.callback_query(RegistrationStates.consent, F.data == "consent_no")
async def process_consent_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "К сожалению, без согласия на обработку персональных данных "
        "мы не можем зарегистрировать вас в системе.\n\n"
        "Вы всегда можете вернуться и зарегистрироваться позже.",
        reply_markup=main_menu,
    )
    await callback.answer()
