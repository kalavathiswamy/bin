import logging
import requests
import psutil
import asyncio
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# =========================
# CONFIG
# =========================
BOT_TOKEN = "8329472164:AAHg69_QmSwfelkoYhoaNbdRtmv7vMfxTuQ"
ADMIN_ID = 1822845513  # your Telegram user ID (owner)
USERS_FILE = "users.txt"

# =========================
# LOGGING
# =========================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# =========================
# LOAD & SAVE USERS
# =========================
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(str(ADMIN_ID) + "\n")  # admin is always approved
        return {ADMIN_ID}

    with open(USERS_FILE, "r") as f:
        return {int(line.strip()) for line in f if line.strip().isdigit()}

def save_user(user_id: int):
    with open(USERS_FILE, "a") as f:
        f.write(str(user_id) + "\n")

approved_users = load_users()

def is_approved(user_id: int) -> bool:
    return user_id in approved_users

# =========================
# UTILS
# =========================
def get_server_status():
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    return f"""
🤖 Bot Status:
━━━━━━━━━━━━━━━━
🖥 CPU: {cpu}%
📦 RAM: {memory}%
💽 Disk: {disk}%
✅ Running smoothly!
"""

def fetch_bin_info(bin_number: str):
    try:
        url = f"https://data.handyapi.com/bin/{bin_number}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            scheme = data.get("Scheme", "N/A")
            card_type = data.get("Type", "N/A")
            brand = data.get("CardTier", "N/A")
            issuer = data.get("Issuer", "N/A")
            country = data.get("Country", {}).get("Name", "N/A")

            return f"""
🏦 VALID BIN FOUND!

💳 BIN: {bin_number}
💳 Scheme: {scheme}
📝 Type: {card_type}
🏷 Brand: {brand}
🏭 Issuer: {issuer}
🌐 Country: {country}
─────────────────────────
Generated & Verified by BIN Checker Bot
"""
        else:
            return f"❌ Failed to fetch BIN {bin_number} (Status {response.status_code})"
    except Exception as e:
        return f"⚠️ Error fetching BIN {bin_number}: {e}"

# =========================
# COMMANDS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return

    status = get_server_status()
    await update.message.reply_text(f"👋 Hello {update.effective_user.first_name}!\n{status}")

async def bin_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Usage: /bin <bin_number>")
        return

    bin_number = context.args[0]
    result = fetch_bin_info(bin_number)
    await update.message.reply_text(result)

async def batch_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Usage: /batch <bin1> <bin2> ... <bin10>")
        return

    bins = context.args[:10]
    results = []
    for b in bins:
        results.append(fetch_bin_info(b))
        await asyncio.sleep(1)  # avoid spamming API

    await update.message.reply_text("\n".join(results))

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Only the admin can approve new users.")
        return

    if len(context.args) == 0:
        await update.message.reply_text("⚠️ Usage: /add <user_id>")
        return

    try:
        new_user = int(context.args[0])
        if new_user in approved_users:
            await update.message.reply_text(f"⚠️ User {new_user} is already approved.")
            return
        approved_users.add(new_user)
        save_user(new_user)
        await update.message.reply_text(f"✅ User {new_user} has been approved and saved.")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_approved(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this bot.")
        return

    await update.message.reply_text("🛑 Bot stopped. Use /start to run again.")

# =========================
# MAIN
# =========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bin", bin_lookup))
    app.add_handler(CommandHandler("batch", batch_lookup))
    app.add_handler(CommandHandler("stop", stop_bot))
    app.add_handler(CommandHandler("add", add_user))

    logger.info("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
