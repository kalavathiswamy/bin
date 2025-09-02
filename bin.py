# -*- coding: utf-8 -*-
import psutil
import requests
import random
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
BOT_TOKEN = '8329472164:AAHg69_QmSwfelkoYhoaNbdRtmv7vMfxTuQ'
CHAT_ID = 1822845513
CHECK_INTERVAL = 1
STATS_INTERVAL = 10

running = False
total_attempts = 0
valid_bins = 0
invalid_bins = 0
stats_message_id = None

# ---------------- FUNCTIONS ----------------
def get_system_status():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    storage = f"Total: {disk.total // (2**30)} GB, Used: {disk.used // (2**30)} GB, Free: {disk.free // (2**30)} GB"
    return f"CPU: {cpu}%\nMemory: {mem.percent}%\nDisk: {disk.percent}%\nStorage: {storage}"

async def send_to_telegram(context, message: str, edit_id=None):
    global stats_message_id
    try:
        if edit_id and stats_message_id:
            await context.bot.edit_message_text(
                chat_id=CHAT_ID,
                message_id=edit_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        else:
            msg = await context.bot.send_message(
                chat_id=CHAT_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            return msg.message_id
    except Exception as e:
        print(f"⚠️ Telegram error: {e}")
        return None

def generate_smart_bin():
    prefixes = ['40', '41', '42', '51', '52', '53', '54', '34', '37']
    prefix = random.choice(prefixes)
    while True:
        remaining = ''.join([str(random.randint(0, 9)) for _ in range(6 - len(prefix))])
        bin_number = prefix + remaining
        if luhn_check(bin_number):
            return bin_number

def luhn_check(bin_number):
    sum_ = 0
    for i, digit in enumerate(bin_number):
        n = int(digit)
        if i % 2 == 0:
            n *= 2
            if n > 9:
                n -= 9
        sum_ += n
    return sum_ % 10 == 0

def check_bin(bin_number):
    global valid_bins, invalid_bins
    try:
        url = f"https://data.handyapi.com/bin/{bin_number}"
        response = requests.get(url, timeout=8)
        if response.status_code != 200:
            invalid_bins += 1
            return None
        data = response.json()
        if data.get("Status", "").upper() == "SUCCESS":
            valid_bins += 1
            return data
        else:
            invalid_bins += 1
            return None
    except:
        invalid_bins += 1
        return None

# ---------------- ASYNC WORKERS ----------------
async def bin_worker(context):
    global running, total_attempts
    while running:
        bin_number = generate_smart_bin()
        total_attempts += 1
        data = check_bin(bin_number)
        if data:
            message = (
                "🏦 <b>VALID BIN FOUND!</b>\n\n"
                f"💳 <b>BIN:</b> <code>{bin_number}</code>\n"
                f"💳 <b>Scheme:</b> {data.get('Scheme','N/A').title()}\n"
                f"📝 <b>Type:</b> {data.get('Type','N/A').title()}\n"
                f"🏷 <b>Brand:</b> {data.get('CardTier','N/A')}\n"
                f"🏭 <b>Issuer:</b> {data.get('Issuer','N/A')}\n"
                f"🌐 <b>Country:</b> {data.get('Country',{}).get('Name','N/A')}\n"
                "─────────────────────────\n"
                "<i>Generated & Verified by BIN Checker Bot</i>"
            )
            await send_to_telegram(context, message)
        await asyncio.sleep(CHECK_INTERVAL)

async def stats_worker(context):
    global running, total_attempts, valid_bins, invalid_bins, stats_message_id
    if stats_message_id is None:
        message = (
            f"📊 <b>Live BIN Checking Stats</b>\n\n"
            f"⚡ Status: ✅ Running\n"
            f"🔢 Total Attempts: {total_attempts}\n"
            f"✅ Valid BINs: {valid_bins}\n"
            f"❌ Invalid BINs: {invalid_bins}\n"
            "─────────────────────────\n"
            "<i>Professional BIN Checker Bot</i>"
        )
        stats_message_id = await send_to_telegram(context, message)
    while running:
        message = (
            f"📊 <b>Live BIN Checking Stats</b>\n\n"
            f"⚡ Status: ✅ Running\n"
            f"🔢 Total Attempts: {total_attempts}\n"
            f"✅ Valid BINs: {valid_bins}\n"
            f"❌ Invalid BINs: {invalid_bins}\n"
            "─────────────────────────\n"
            "<i>Professional BIN Checker Bot</i>"
        )
        await send_to_telegram(context, message, edit_id=stats_message_id)
        await asyncio.sleep(STATS_INTERVAL)

# ---------------- TELEGRAM COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = get_system_status()
    await update.message.reply_text(
        f"🤖 Bot is running!\n\nSystem Status:\n{status}\n\nUse /chk <BIN> to check a BIN or /bin to start random checking."
    )

async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        bin_number = context.args[0]
        if not bin_number.isdigit() or len(bin_number) != 6:
            await update.message.reply_text("⚠️ BIN must be exactly 6 digits.")
            return
        await update.message.reply_text(f"🔎 Checking BIN: <code>{bin_number}</code>")
        data = check_bin(bin_number)
        if data:
            message = (
                "🏦 <b>VALID BIN FOUND!</b>\n\n"
                f"💳 <b>BIN:</b> <code>{bin_number}</code>\n"
                f"💳 <b>Scheme:</b> {data.get('Scheme','N/A').title()}\n"
                f"📝 <b>Type:</b> {data.get('Type','N/A').title()}\n"
                f"🏷 <b>Brand:</b> {data.get('CardTier','N/A')}\n"
                f"🏭 <b>Issuer:</b> {data.get('Issuer','N/A')}\n"
                f"🌐 <b>Country:</b> {data.get('Country',{}).get('Name','N/A')}\n"
                "─────────────────────────\n"
                "<i>Generated & Verified by BIN Checker Bot</i>"
            )
            await send_to_telegram(context, message)
        else:
            await update.message.reply_text(f"❌ BIN <code>{bin_number}</code> not found or invalid.")
    else:
        await update.message.reply_text("⚠️ Please check the command. Usage: /chk <BIN>")

async def start_bin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    if not running:
        running = True
        await send_to_telegram(context, "▶️ <b>Random BIN checking started!</b>")
        asyncio.create_task(bin_worker(context))
        asyncio.create_task(stats_worker(context))
    else:
        await update.message.reply_text("⚠️ Random BIN checking is already running.")

async def stop_bin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    if running:
        running = False
        message = (
            f"⏹️ <b>Random BIN checking stopped.</b>\n"
            f"🔢 Total Attempts: {total_attempts}\n"
            f"✅ Valid BINs: {valid_bins}\n"
            f"❌ Invalid BINs: {invalid_bins}"
        )
        await send_to_telegram(context, message)
    else:
        await update.message.reply_text("⚠️ Random BIN checking is not running.")

# ---------------- MAIN ----------------
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chk", chk))
    app.add_handler(CommandHandler("bin", start_bin_cmd))
    app.add_handler(CommandHandler("stop", stop_bin_cmd))
    print("🤖 Bot is running...")
    app.run_polling()
