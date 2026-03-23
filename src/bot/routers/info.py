from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from src.bot.keyboards import faq_keyboard, main_menu

router = Router()

FAQ_ANSWERS = {
    "faq_what": (
        "<b>Что такое неонатальный скрининг?</b>\n\n"
        "Неонатальный скрининг — это массовое обследование новорождённых "
        "для выявления наследственных заболеваний. С 2023 года в России "
        "проводится расширенный скрининг на 36 заболеваний.\n\n"
        "Анализ берётся у каждого новорождённого на 2-й день жизни "
        "(у недоношенных — на 7-й день). Это позволяет выявить заболевание "
        "до появления симптомов и начать лечение на ранней стадии."
    ),
    "faq_why": (
        "<b>Зачем берут кровь из пятки?</b>\n\n"
        "Из пятки новорождённого берут несколько капель крови на специальный "
        "тест-бланк (фильтровальную бумагу). Этот метод называется «сухое "
        "пятно крови».\n\n"
        "Пятка выбрана потому что:\n"
        "- Это наименее болезненное место для забора\n"
        "- Кровоток в пятке достаточный для анализа\n"
        "- Процедура безопасна и занимает несколько минут\n\n"
        "Образец отправляется в медико-генетический центр для анализа "
        "методом тандемной масс-спектрометрии (ТМС)."
    ),
    "faq_safe": (
        "<b>Безопасен ли неонатальный скрининг?</b>\n\n"
        "Да, процедура абсолютно безопасна!\n\n"
        "- Забирается всего несколько капель крови\n"
        "- Используется одноразовый стерильный скарификатор\n"
        "- Риск инфицирования исключён\n"
        "- Процедура занимает 1-2 минуты\n"
        "- Ребёнок испытывает минимальный дискомфорт\n\n"
        "Скрининг рекомендован Всемирной организацией здравоохранения "
        "и проводится во всех развитых странах."
    ),
    "faq_positive": (
        "<b>Что если результат положительный?</b>\n\n"
        "Положительный результат скрининга — это ещё НЕ диагноз!\n\n"
        "Это означает, что необходимо дополнительное обследование. "
        "В большинстве случаев повторный анализ показывает норму.\n\n"
        "Если результат положительный:\n"
        "1. Вам придёт уведомление через этот бот\n"
        "2. Свяжитесь с педиатром как можно скорее\n"
        "3. Врач назначит подтверждающие исследования\n"
        "4. При подтверждении — назначается лечение\n\n"
        "Раннее выявление и лечение позволяют предотвратить "
        "тяжёлые последствия заболевания."
    ),
    "faq_contacts": (
        "<b>Контакты медико-генетического центра</b>\n\n"
        "Медико-генетический центр РБ №1 — НЦМ\n"
        "г. Якутск, ул. Сергеляхское шоссе, 4\n\n"
        "Телефон регистратуры: +7 (4112) 39-45-16\n"
        "Горячая линия по РНС: +7 (4112) 39-45-17\n\n"
        "Режим работы: Пн-Пт 8:30 — 17:00"
    ),
}


@router.message(F.text == "Узнать о неонатальном скрининге")
async def show_faq(message: Message):
    await message.answer(
        "Выберите интересующий вопрос:",
        reply_markup=faq_keyboard,
    )


@router.callback_query(F.data.startswith("faq_"))
async def answer_faq(callback: CallbackQuery):
    answer = FAQ_ANSWERS.get(callback.data)
    if answer:
        await callback.message.answer(answer, reply_markup=faq_keyboard)
    await callback.answer()


@router.message(F.text == "Мой профиль")
async def show_profile(message: Message, session):
    from src.services.parent_service import (
        get_decrypted_name,
        get_decrypted_phone,
        get_parent_by_telegram_id,
    )

    parent = await get_parent_by_telegram_id(session, message.from_user.id)
    if not parent:
        await message.answer(
            "Вы ещё не зарегистрированы.\n"
            'Нажмите "Я беременна / готовлюсь к родам" для регистрации.',
            reply_markup=main_menu,
        )
        return

    name = get_decrypted_name(parent)
    babies_text = ""
    if parent.babies:
        babies_list = []
        for baby in parent.babies:
            bdate = baby.birth_date.strftime("%d.%m.%Y") if baby.birth_date else "—"
            babies_list.append(f"  - {baby.name} ({bdate})")
        babies_text = "\n".join(babies_list)
    else:
        babies_text = "  Нет добавленных детей"

    await message.answer(
        f"<b>Ваш профиль</b>\n\n"
        f"ФИО: {name}\n"
        f"Район: {parent.region}\n"
        f"Дата регистрации: {parent.registration_date.strftime('%d.%m.%Y')}\n\n"
        f"<b>Дети:</b>\n{babies_text}",
        reply_markup=main_menu,
    )


@router.message(F.text == "Личный кабинет")
async def show_portal_link(message: Message, session):
    from src.services.parent_service import get_parent_by_telegram_id

    parent = await get_parent_by_telegram_id(session, message.from_user.id)
    if not parent:
        await message.answer(
            "Сначала зарегистрируйтесь через бот.",
            reply_markup=main_menu,
        )
        return

    await message.answer(
        "<b>Личный кабинет</b>\n\n"
        "Откройте портал в браузере и войдите по номеру телефона:\n\n"
        "http://localhost:8000/portal/login\n\n"
        "Вам придёт одноразовый код для входа в этот чат.",
        reply_markup=main_menu,
    )
