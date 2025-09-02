# -*- coding: utf-8 -*-
import os
import psutil
import requests
import random
import threading
import time
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
BOT_TOKEN = '8329472164:AAHg69_QmSwfelkoYhoaNbdRtmv7vMfxTuQ'
CHAT_ID = 1822845513
CHECK_INTERVAL = 1
STATS_INTERVAL = 10
TELEGRAM_DELAY = 1.5

bot = Bot(BOT_TOKEN)
running = False
total_attempts = 0
valid_bins = 0
invalid_bins = 0
stats_message_id = None

# ---------------- FUNCTIONS ----------------
def get_system_status():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    mem_percent = mem.percent
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    storage = f"Total: {disk.total // (2**30)} GB, Used: {disk.used // (2**30)} GB, Free: {disk.free // (2**30)} GB"
    return f"CPU: {cpu}%\nMemory: {mem_percent}%\nDisk: {disk_percent}%\nStorage: {storage}"

def send_to_telegram(message: str, edit_id=None):
    global stats_message_id
    try:
        if edit_id and stats_message_id:
            bot.edit_message_text(chat_id=CHAT_ID, message_id=edit_id,
                                  text=message, parse_mode='HTML', disable_web_page_preview=True)
        else:
            msg = bot.send_message(CHAT_ID, text=message, parse_mode='HTML', disable_web_page_preview=True)
            time.sleep(TELEGRAM_DELAY)
            return msg.message_id
    except Exception as e:
        print(f"⚠️ Telegram send/edit error: {e}")
        return None

def check_bin(bin_number: str) -> bool:
    global valid_bins, invalid_bins
    try:
        url = f"https://data.handyapi.com/bin/{bin_number}"
        response = requests.get(url, timeout=8)  # No API key needed

        if response.status_code != 200:
            invalid_bins += 1
            return False

        data = response.json()
        if data.get("Status", "").upper() == "SUCCESS":
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
            send_to_telegram(message)
            valid_bins += 1
            return True
        else:
            invalid_bins += 1
            return False
    except Exception as e:
        invalid_bins += 1
        print(f"⚠️ Error checking BIN {bin_number}: {e}")
        return False

# ---------------- SMART BIN GENERATOR ----------------
def generate_smart_bin():
    prefixes = ['40', '41', '42', '51', '52', '53', '54', '34', '37']  # common BIN prefixes
    prefix = random.choice(prefixes)
    
    # Fill remaining digits randomly and try Luhn
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

# ---------------- WORKERS ----------------
def bin_worker():
    global running, total_attempts
    while running:
        bin_number = generate_smart_bin()
        total_attempts += 1
        check_bin(bin_number)
        time.sleep(CHECK_INTERVAL)

def stats_worker():
    global running, total_attempts, valid_bins, invalid_bins, stats_message_id
    if stats_message_id is None:
        stats_message = (
            f"📊 <b>Live BIN Checking Stats</b>\n\n"
            f"⚡ Status: ✅ Running\n"
            f"🔢 Total Attempts: {total_attempts}\n"
            f"✅ Valid BINs: {valid_bins}\n"
            f"❌ Invalid BINs: {invalid_bins}\n"
            "─────────────────────────\n"
            "<i>Professional BIN Checker Bot</i>"
        )
        stats_message_id = send_to_telegram(stats_message)
    while running:
        if stats_message_id:
            stats_message = (
                f"📊 <b>Live BIN Checking Stats</b>\n\n"
                f"⚡ Status: ✅ Running\n"
                f"🔢 Total Attempts: {total_attempts}\n"
                f"✅ Valid BINs: {valid_bins}\n"
                f"❌ Invalid BINs: {invalid_bins}\n"
                "─────────────────────────\n"
                "<i>Professional BIN Checker Bot</i>"
            )
            send_to_telegram(stats_message, edit_id=stats_message_id)
        time.sleep(STATS_INTERVAL)

# ---------------- TELEGRAM COMMANDS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = get_system_status()
    await update.message.reply_text(f"🤖 Bot is running!\n\nSystem Status:\n{status}\n\nUse /chk <BIN> to check a BIN or /bin to start random checking.")

async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        bin_number = context.args[0]
        if not bin_number.isdigit() or len(bin_number) != 6:
            await update.message.reply_text("⚠️ BIN must be exactly 6 digits.")
            return
        await update.message.reply_text(f"🔎 Checking BIN: <code>{bin_number}</code>")
        result = check_bin(bin_number)
        if not result:
            await update.message.reply_text(f"❌ BIN <code>{bin_number}</code> not found or invalid.")
    else:
        await update.message.reply_text("⚠️ Please check the command. Usage: /chk <BIN>")

async def start_bin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    if not running:
        running = True
        send_to_telegram("▶️ <b>Random BIN checking started!</b>")
        threading.Thread(target=bin_worker).start()
        threading.Thread(target=stats_worker).start()
    else:
        await update.message.reply_text("⚠️ Random BIN checking is already running.")

async def stop_bin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running
    if running:
        running = False
        final_stats = (
            f"⏹️ <b>Random BIN checking stopped.</b>\n"
            f"🔢 Total Attempts: {total_attempts}\n"
            f"✅ Valid BINs: {valid_bins}\n"
            f"❌ Invalid BINs: {invalid_bins}"
        )
        send_to_telegram(final_stats)
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
