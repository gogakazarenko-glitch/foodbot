import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# === НАСТРОЙКИ — СЮДА ВСТАВЬ СВОИ ТОКЕНЫ ПОЗЖЕ ===
BOT_TOKEN = "ТОКЕН_БОТА_ОТ_BOTFATHER" # замени на свой
ADMIN_ID = 123456789 # замени на свой Telegram ID (админ, куда приходят заказы)

# Логи
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# Пример меню (потом заменишь на своё кафе)
MENU = {
    "borch": {"name": "Борщ", "price": 350},
    "vareniki": {"name": "Вареники с картошкой", "price": 280},
    "kompot": {"name": "Компот", "price": 100},
}

# Корзина пользователя (в памяти, на старте хватит)
carts = {}

# Клавиатура главного меню
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("🍲 Меню"), KeyboardButton("🛒 Корзина"))
main_kb.add(KeyboardButton("📞 Контакты"))

# === Команда /start ===
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "Привет! 👋\nЯ бот доставки еды из кафе.\nВыбери, что хочешь:",
        reply_markup=main_kb
    )

# === Показ меню ===
@dp.message_handler(text="🍲 Меню")
async def show_menu(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=2)
    for key, item in MENU.items():
        btn = InlineKeyboardButton(
            text=f"{item['name']} — {item['price']} ₽",
            callback_data=f"add_{key}"
        )
        kb.add(btn)
    
    if message.from_user.id in carts and carts[message.from_user.id]:
        kb.add(InlineKeyboardButton("🛒 Перейти в корзину", callback_data="cart"))
    
    await message.answer("Выбери блюдо:", reply_markup=kb)

# === Добавление в корзину ===
@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    item_key = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    if user_id not in carts:
        carts[user_id] = {}
    
    if item_key in carts[user_id]:
        carts[user_id][item_key] += 1
    else:
        carts[user_id][item_key] = 1
    
    await callback.answer(f"Добавлено: {MENU[item_key]['name']}")
    await callback.message.edit_reply_markup() # убираем кнопки, чтоб не нажимали повторно

# === Показ корзины ===
@dp.message_handler(text="🛒 Корзина")
@dp.callback_query_handler(lambda c: c.data == "cart")
async def show_cart(message_or_callback):
    if isinstance(message_or_callback, types.Message):
        user_id = message_or_callback.from_user.id
        msg = message_or_callback
    else:
        user_id = message_or_callback.from_user.id
        msg = message_or_callback.message
    
    if user_id not in carts or not carts[user_id]:
        await msg.edit_text("Корзина пуста 😔\nДобавь что-нибудь из меню!", reply_markup=None)
        return
    
    total = 0
    text = "🛒 Твоя корзина:\n\n"
    kb = InlineKeyboardMarkup()
    
    for item_key, count in carts[user_id].items():
        item = MENU[item_key]
        price = item["price"] * count
        total += price
        text += f"• {item['name']} × {count} = {price} ₽\n"
        
        # кнопки + и -
        plus = InlineKeyboardButton("+", callback_data=f"plus_{item_key}")
        minus = InlineKeyboardButton("-", callback_data=f"minus_{item_key}")
        kb.row(plus, minus)
    
    text += f"\n💰 Итого: {total} ₽"
    
    pay_btn = InlineKeyboardButton("💳 Оплатить (СБП)", callback_data="pay")
    clear_btn = InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear")
    kb.add(pay_btn)
    kb.add(clear_btn)
    
    if isinstance(message_or_callback, types.Message):
        await msg.answer(text, reply_markup=kb)
    else:
        await msg.edit_text(text, reply_markup=kb)

# === Управление количеством ===
@dp.callback_query_handler(lambda c: c.data.startswith(("plus_", "minus_")))
async def change_quantity(callback: types.CallbackQuery):
    action, item_key = callback.data.split("_")
    user_id = callback.from_user.id
    
    if action == "plus":
        carts[user_id][item_key] += 1
    else:
        carts[user_id][item_key] -= 1
        if carts[user_id][item_key] <= 0:
            del carts[user_id][item_key]
            if not carts[user_id]:
                del carts[user_id]
    
    await show_cart(callback) # обновляем корзину
    await callback.answer()

# === Очистка корзины ===
@dp.callback_query_handler(lambda c: c.data == "clear")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in carts:
        del carts[user_id]
    await callback.message.edit_text("Корзина очищена 🗑", reply_markup=None)
    await callback.answer()

# === Оплата (заглушка, потом вставим ЮKassa) ===
@dp.callback_query_handler(lambda c: c.data == "pay")
async def process_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in carts or not carts[user_id]:
        await callback.answer("Корзина пуста!", show_alert=True)
        return
    
    total = sum(MENU[k]["price"] * v for k, v in carts[user_id].items())
    
    # Здесь будет настоящая оплата через ЮKassa СБП в один клик
    await callback.message.edit_text(
        f"Оплата {total} ₽ через СБП...\n"
        "(пока заглушка — в реальности здесь будет кнопка оплаты)\n\n"
        "Заказ принят и отправлен на кухню! 🚀"
    )
    
    # Уведомление админу
    order_text = f"🆕 Новый заказ от {callback.from_user.full_name} (ID: {user_id})\n\n"
    for k, v in carts[user_id].items():
        order_text += f"• {MENU[k]['name']} × {v} = {MENU[k]['price'] * v} ₽\n"
    order_text += f"\n💰 Итого: {total} ₽"
    
    await bot.send_message(ADMIN_ID, order_text)
    
    # Очищаем корзину после заказа
    del carts[user_id]
    
    await callback.answer("Заказ принят!")

# Запуск
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
