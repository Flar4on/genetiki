from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# --- Main menu ---

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Я беременна / готовлюсь к родам")],
        [KeyboardButton(text="У меня родился ребёнок")],
        [KeyboardButton(text="Узнать о неонатальном скрининге")],
        [KeyboardButton(text="Мой профиль"), KeyboardButton(text="Личный кабинет")],
    ],
    resize_keyboard=True,
)

# --- Registration ---

share_contact = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True,
)

consent_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Даю согласие", callback_data="consent_yes"),
            InlineKeyboardButton(text="Отказываюсь", callback_data="consent_no"),
        ]
    ]
)

remove_keyboard = ReplyKeyboardRemove()

# --- Regions of Yakutia ---

YAKUTIA_REGIONS = [
    "Якутск",
    "Алданский",
    "Аллаиховский",
    "Амгинский",
    "Анабарский",
    "Булунский",
    "Верхневилюйский",
    "Верхнеколымский",
    "Верхоянский",
    "Вилюйский",
    "Горный",
    "Жиганский",
    "Кобяйский",
    "Ленский",
    "Мегино-Кангаласский",
    "Мирнинский",
    "Момский",
    "Намский",
    "Нерюнгринский",
    "Нижнеколымский",
    "Нюрбинский",
    "Оймяконский",
    "Олёкминский",
    "Оленёкский",
    "Среднеколымский",
    "Сунтарский",
    "Таттинский",
    "Томпонский",
    "Усть-Алданский",
    "Усть-Майский",
    "Усть-Янский",
    "Хангаласский",
    "Чурапчинский",
    "Эвено-Бытантайский",
]


def region_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, region in enumerate(YAKUTIA_REGIONS):
        row.append(InlineKeyboardButton(text=region, callback_data=f"region_{i}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Hospitals ---

HOSPITALS = [
    "ПЦ РБ №1-НЦМ (Якутск)",
    "Якутская городская больница №2",
    "Алданская ЦРБ",
    "Нерюнгринская ЦРБ",
    "Мирнинская ЦРБ",
    "Ленская ЦРБ",
    "Вилюйская ЦРБ",
    "Другой",
]


def hospital_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=h, callback_data=f"hospital_{i}")]
        for i, h in enumerate(HOSPITALS)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- FAQ ---

faq_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Что такое неонатальный скрининг?", callback_data="faq_what")],
        [InlineKeyboardButton(text="Зачем берут кровь из пятки?", callback_data="faq_why")],
        [InlineKeyboardButton(text="Это безопасно?", callback_data="faq_safe")],
        [InlineKeyboardButton(text="Что если результат положительный?", callback_data="faq_positive")],
        [InlineKeyboardButton(text="Контакты медико-генетического центра", callback_data="faq_contacts")],
        [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
    ]
)


# --- Notification confirmation ---

def confirm_notification_keyboard(notification_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Я получил(а) информацию",
                    callback_data=f"confirm_{notification_id}",
                )
            ]
        ]
    )
