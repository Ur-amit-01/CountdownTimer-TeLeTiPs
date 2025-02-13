import os
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, MessageNotModified
from motor.motor_asyncio import AsyncIOMotorClient

# Bot Configuration
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
FOOTER_MESSAGE = os.environ["FOOTER_MESSAGE"]

# MongoDB Setup
MONGO_URI = "mongodb+srv://your_mongodb_uri"
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["countdown_db"]
countdowns = db["countdowns"]

bot = Client(
    "Countdown-TeLeTiPs",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

stoptimer = False

# Main Menu Buttons
TELETIPS_MAIN_MENU_BUTTONS = [
    [
        InlineKeyboardButton("👨‍💻 DEVELOPER", url="https://t.me/axa_bachha"),
        InlineKeyboardButton("HELP ❓", callback_data="HELP_CALLBACK")
    ]
]

async def countdown_task(chat_id, msg_id, end_time, event_text):
    global stoptimer
    while time.time() < end_time and not stoptimer:
        remaining_time = int(end_time - time.time())
        if remaining_time <= 0:
            break

        d, h, m, s = (
            remaining_time // (3600 * 24),
            (remaining_time % (3600 * 24)) // 3600,
            (remaining_time % 3600) // 60,
            remaining_time % 60
        )

        countdown_text = f"{event_text}\n\n⏳ {d}d {h}h {m}m {s}s\n\n<i>{FOOTER_MESSAGE}</i>"

        try:
            await bot.edit_message_text(chat_id, msg_id, countdown_text)
        except:
            pass

        await asyncio.sleep(5)

    await bot.send_message(chat_id, "🚨 Beep! Beep!! **TIME'S UP!!!**")
    await countdowns.delete_one({"chat_id": chat_id, "msg_id": msg_id})

@bot.on_message(filters.command("set"))
async def set_timer(client, message):
    global stoptimer
    try:
        if message.chat.id > 0:
            return await message.reply("⛔️ Use this command in a **group chat**.")

        user = await client.get_chat_member(message.chat.id, message.from_user.id)
        if not user.privileges:
            return await message.reply("👮🏻‍♂️ Only **admins** can execute this command.")

        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            return await message.reply("❌ **Incorrect format.**\n\n✅ Use: `/set <seconds> \"event\"`\nExample: `/set 10 \"Test countdown\"`")

        countdown_time = int(args[1])
        event_text = args[2]
        end_time = time.time() + countdown_time

        msg = await message.reply(f"⏳ Countdown Started for {countdown_time} seconds!")

        await countdowns.insert_one(
            {"chat_id": message.chat.id, "msg_id": msg.message_id, "end_time": end_time, "event_text": event_text}
        )

        asyncio.create_task(countdown_task(message.chat.id, msg.message_id, end_time, event_text))

    except Exception as e:
        await message.reply(f"Error: {str(e)}")

@bot.on_message(filters.command("stopc"))
async def stop_timer(client, message):
    global stoptimer
    user = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if not user.privileges:
        return await message.reply("👮🏻‍♂️ Only **admins** can execute this command.")

    stoptimer = True
    await message.reply("🛑 Countdown stopped.")

@bot.on_message(filters.command("clearcountdowns"))
async def clear_all_countdowns(_, message):
    await countdowns.delete_many({})
    await message.reply("✅ All countdowns cleared!")

@bot.on_message(filters.command("listcountdowns"))
async def list_active_countdowns(_, message):
    active_countdowns = await countdowns.find().to_list(length=100)
    if not active_countdowns:
        return await message.reply("No active countdowns.")

    msg = "⏳ Active Countdowns:\n"
    for countdown in active_countdowns:
        remaining_time = int(countdown["end_time"] - time.time())
        minutes, seconds = divmod(remaining_time, 60)
        msg += f"🔹 Chat ID: `{countdown['chat_id']}` - {minutes}m {seconds}s left\n"

    await message.reply(msg)

async def resume_countdowns():
    async for countdown in countdowns.find():
        chat_id = countdown["chat_id"]
        msg_id = countdown["msg_id"]
        end_time = countdown["end_time"]
        event_text = countdown["event_text"]

        if time.time() < end_time:
            asyncio.create_task(countdown_task(chat_id, msg_id, end_time, event_text))
        else:
            await countdowns.delete_one({"chat_id": chat_id, "msg_id": msg_id})

print("Countdown Timer is alive!")

async def main():
    await bot.start()
    await resume_countdowns()
    await bot.idle()

if __name__ == "__main__":
    asyncio.run(main())

