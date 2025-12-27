import logging
import subprocess
import sys

# Устанавливаем aiogram, если нужно
subprocess.check_call([sys.executable, "-m", "pip", "install", "aiogram==3.4.0"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# === ТВОИ НАСТРОЙКИ ===
BOT_TOKEN = "8292431082:AAE6DxgeZU5gc1EvopKpnC0vkxgnnCSitzU" # твой токен
ADMIN_ID = 2027162196 # твой Telegram ID — теперь заказы будут приходить именно тебе

# Логи
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

# Меню (потом заменишь под реальное кафе)
MENU = {
    "borch": {"name": "Борщ", "price": 350},
    "vareniki": {"name": "Вареники с картошкой", "price": 280},
    "kompot": {"name": "Компот", "price": 100},
}

# Корзина пользователей
carts = {}

# Главная клавиатура
main_kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
main_kb.add(KeyboardButton("🍲 Меню"), KeyboardButton("🛒 Корзина"))
main_kb.add(KeyboardButton("📞 Контакты"))

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "Привет! 👋\nЯ бот доставки еды из кафе.\nВыбери, что хочешь:",
        reply_markup=main_kb
    )

@dp.message_handler(text="🍲 Меню")
async def show_menu(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=1)
    for key, item in MENU.items():
        btn = InlineKeyboardButton(
            text=f"{item['name']} — {item['price']} ₽",
            callback_data=f"add_{key}"
        )
        kb.add(btn)
    
    if message.from_user.id in carts and carts[message.from_user.id]:
        kb.add(InlineKeyboardButton("🛒 Перейти в корзину", callback_data="cart"))
    
    await message.answer("🍽 Выбери блюдо:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("add_"))
async def add_to_cart(callback: types.CallbackQuery):
    item_key = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    if user_id not in carts:
        carts[user_id] = {}
    
    carts[user_id][item_key] = carts[user_id].get(item_key, 0) + 1
    
    await callback.answer(f"Добавлено: {MENU[item_key]['name']}")
    await show_menu(callback.message)

@dp.message_handler(text="🛒 Корзина")
@dp.callback_query_handler(lambda c: c.data == "cart")
async def show_cart(query_or_message):
    if isinstance(query_or_message, types.CallbackQuery):
        user_id = query_or_message.from_user.id
        message = query_or_message.message
    else:
        user_id = query_or_message.from_user.id
        message = query_or_message
    
    if user_id not in carts or not carts[user_id]:
        await message.edit_text("🛒 Корзина пуста 😔\nДобавь что-нибудь из меню!", reply_markup=None)
        return
    
    total = 0
    text = "🛒 Твоя корзина:\n\n"
    kb = InlineKeyboardMarkup(row_width=2)
    
    for item_key, count in carts[user_id].items():
        item = MENU[item_key]
        price = item["price"] * count
        total += price
        text += f"• {item['name']} × {count} = {price} ₽\n"
        
        plus = InlineKeyboardButton("+", callback_data=f"plus_{item_key}")
        minus = InlineKeyboardButton("-", callback_data=f"minus_{item_key}")
        kb.row(plus, minus)
    
    text += f"\n💰 Итого: {total} ₽"
    
    kb.add(InlineKeyboardButton("💳 Оплатить (СБП)", callback_data="pay"))
    kb.add(InlineKeyboardButton("🗑 Очистить корзину", callback_data="clear"))
    
    await message.edit_text(text, reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith(("plus_", "minus_")))
async def change_quantity(callback: types.CallbackQuery):
    action, item_key = callback.data.split("_")
    user_id = callback.from_user.id
    
    if action == "plus":
        carts[user_id][item_key] = carts[user_id].get(item_key, 0) + 1
    else:
        carts[user_id][item_key] -= 1
        if carts[user_id][item_key] <= 0:
            del carts[user_id][item_key]
    
    if not carts[user_id]:
        del carts[user_id]
    
    await show_cart(callback)

@dp.callback_query_handler(lambda c: c.data == "clear")
async def clear_cart(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id in carts:
        del carts[user_id]
    await callback.message.edit_text("🛒 Корзина очищена!", reply_markup=None)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "pay")
async def process_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in carts or not carts[user_id]:
        await callback.answer("Корзина пуста!", show_alert=True)
        return
    
    total = sum(MENU[k]["price"] * v for k, v in carts[user_id].items())
    
    await callback.message.edit_text(
        f"Оплата {total} ₽ через СБП...\n\n"
        "Заказ принят и отправлен на кухню! 🚀\n"
        "(скоро добавим настоящую оплату в один клик)"
    )
    
    order_text = f"🆕 Новый заказ!\nОт: {callback.from_user.full_name} (ID: {user_id})\n\n"
    for k, v in carts[user_id].items():
        order_text += f"• {MENU[k]['name']} × {v} = {MENU[k]['price'] * v} ₽\n"
    order_text += f"\n💰 Итого: {total} ₽"
    
    await bot.send_message(ADMIN_ID, order_text)
    
    del carts[user_id]
    await callback.answer("Спасибо за заказ!")

if __name__ == "__main__":
    logging.info("Бот запущен и готов принимать заказы!")
    executor.start_polling(dp, skip_updates=True)
