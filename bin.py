# -*- coding: utf-8 -*-
import telebot
import requests
import random
import threading
import time

# -------------------- CONFIG --------------------
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
API_URL = "https://lookup.binlist.net/{}"
CHECK_INTERVAL = 1  # seconds between random BIN generation
TELEGRAM_DELAY = 1.5  # seconds between sending messages to avoid Telegram limits

bot = telebot.TeleBot(BOT_TOKEN)
running = False
total_attempts = 0
valid_bins = 0

# -------------------- FUNCTIONS --------------------
def send_to_telegram(message: str):
    """Send professional formatted message to Telegram with delay"""
    try:
        bot.send_message(CHAT_ID, message, parse_mode='HTML', disable_web_page_preview=True)
        time.sleep(TELEGRAM_DELAY)
    except Exception as e:
        print(f"⚠️ Telegram send error: {e}")

def check_bin(bin_number: str) -> bool:
    """Check BIN via Binlist API"""
    global valid_bins
    try:
        response = requests.get(API_URL.format(bin_number), headers={"Accept-Version": "3"}, timeout=8)
        if response.status_code == 200:
            data = response.json()
            bank = data.get("bank", {})
            country = data.get("country", {})

            # HTML emoji codes used for professional display
            message = (
                "&#127974; <b>BIN Lookup Result</b>\n\n"
                f"&#128179; <b>BIN:</b> <code>{bin_number}</code>\n"
                f"&#128179; <b>Scheme:</b> {data.get('scheme','N/A').title()}\n"
                f"&#128221; <b>Type:</b> {data.get('type','N/A').title()}\n"
                f"&#127991; <b>Brand:</b> {data.get('brand','N/A')}\n"
                f"&#127981; <b>Bank:</b> {bank.get('name','N/A')}\n"
                f"&#127760; <b>Country:</b> {country.get('name','N/A')} {country.get('emoji','')}\n"
                "─────────────────────────\n"
                "<i>Generated & Verified by BIN Checker Bot</i>"
            )

            send_to_telegram(message)
            valid_bins += 1
            print(f"✅ Valid BIN: {bin_number} | Bank: {bank.get('name','N/A')}")
            return True
        else:
            print(f"❌ Invalid BIN: {bin_number}")
            return False
    except Exception as e:
        print(f"⚠️ Error checking BIN {bin_number}: {e}")
        return False

def generate_bin() -> str:
    """Generate a random 6-digit BIN"""
    return "".join([str(random.randint(0, 9)) for _ in range(6)])

def bin_worker():
    """Background worker for random BIN generation/checking"""
    global running, total_attempts
    while running:
        bin_number = generate_bin()
        total_attempts += 1
        check_bin(bin_number)
        time.sleep(CHECK_INTERVAL)

# -------------------- TELEGRAM COMMANDS --------------------
@bot.message_handler(commands=['bin'])
def start_bin(message):
    global running
    if not running:
        running = True
        send_to_telegram("▶️ <b>Random BIN checking started!</b>")
        threading.Thread(target=bin_worker).start()
    else:
        send_to_telegram("⚠️ Random BIN checking is already running.")

@bot.message_handler(commands=['stop'])
def stop_bin(message):
    global running
    if running:
        running = False
        send_to_telegram(
            f"⏹️ <b>Random BIN checking stopped.</b>\n"
            f"📊 Total Attempts: {total_attempts}\n"
            f"✅ Valid BINs: {valid_bins}"
        )
    else:
        send_to_telegram("⚠️ Random BIN checking is not running.")

@bot.message_handler(commands=['chk'])
def check_single_bin(message):
    """Check a single BIN provided by user"""
    try:
        parts = message.text.split()
        if len(parts) != 2:
            send_to_telegram("⚠️ Usage: /chk <6-digit BIN>\nExample: /chk 457173")
            return
        bin_number = parts[1]
        if not bin_number.isdigit() or len(bin_number) != 6:
            send_to_telegram("⚠️ BIN must be exactly 6 digits.")
            return
        send_to_telegram(f"🔎 Checking BIN: <code>{bin_number}</code> ...")
        check_bin(bin_number)
    except Exception as e:
        send_to_telegram(f"⚠️ Error: {e}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    """Show current bot statistics"""
    status = "✅ Running" if running else "⏹️ Stopped"
    stats_message = (
        f"📊 <b>BIN Checker Stats</b>\n\n"
        f"⚡ Status: {status}\n"
        f"🔢 Total Attempts: {total_attempts}\n"
        f"✅ Valid BINs: {valid_bins}\n"
        "─────────────────────────\n"
        "<i>Professional BIN Checker Bot</i>"
    )
    send_to_telegram(stats_message)

# -------------------- MAIN --------------------
print("🤖 Bot is running... Waiting for /bin, /stop, /chk, or /stats commands.")
bot.infinity_polling()