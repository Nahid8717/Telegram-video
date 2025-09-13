from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import logging
import os
import pymongo
import datetime
import requests

# ==== Environment Variables ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
GPLINKS_API = os.getenv("GPLINKS_API")
MONGO_URI = os.getenv("MONGO_URI")
BASE_URL = os.getenv("BASE_URL")   # Render এর URL
PORT = int(os.getenv("PORT", 10000))

# ==== Flask App ====
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

# ==== MongoDB Connect ====
mongo = pymongo.MongoClient(MONGO_URI)
db = mongo["telegram_bot"]
users = db["users"]

# ==== Logging ====
logging.basicConfig(level=logging.INFO)

# ==== Verify Check ====
def is_verified(user_id):
    user = users.find_one({"userId": user_id})
    if not user:
        return False
    last = user.get("lastVerified")
    if not last:
        return False
    return (datetime.datetime.now() - last).total_seconds() < 3 * 60 * 60  # 3 hours

# ==== GPLinks Shortener ====
def shorten_link(url):
    try:
        r = requests.get(f"https://gplinks.in/api?api={GPLINKS_API}&url={url}")
        data = r.json()
        return data.get("shortenedUrl", url)
    except:
        return url

# ==== Commands ====
def start(update: Update, context):
    update.message.reply_text("👋 স্বাগতম! ভিডিও দেখতে চাইলে আগে ভেরিফাই করুন। /verify")

def verify(update: Update, context):
    user_id = update.message.from_user.id
    callback_url = f"{BASE_URL}/verify/{user_id}"
    short_link = shorten_link(callback_url)
    update.message.reply_text(f"✅ ভেরিফাই করতে এখানে ক্লিক করুন:\n{short_link}")

def video(update: Update, context):
    user_id = update.message.from_user.id
    if not is_verified(user_id):
        update.message.reply_text("⚠️ প্রথমে ভেরিফাই করুন! /verify ব্যবহার করুন।")
        return
    update.message.reply_video(
        "https://file-examples.com/storage/fe5e1a2b3b9/video.mp4",
        caption="🎬 এখানে আপনার ভিডিও"
    )

def delete_videos(update: Update, context):
    if str(update.message.from_user.id) != str(ADMIN_ID):
        return
    users.update_many({}, {"$set": {"lastVerified": None}})
    update.message.reply_text("🗑️ সব ইউজারের ভেরিফাই ডিলিট করা হয়েছে।")

# ==== Dispatcher ====
from telegram.ext import Dispatcher
dispatcher = Dispatcher(bot, None, workers=0)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("verify", verify))
dispatcher.add_handler(CommandHandler("video", video))
dispatcher.add_handler(CommandHandler("deletevideos", delete_videos))

# ==== Flask Routes ====
@app.route("/verify/<int:user_id>")
def verify_user(user_id):
    users.update_one(
        {"userId": user_id},
        {"$set": {"lastVerified": datetime.datetime.now()}},
        upsert=True
    )
    return "✅ ভেরিফিকেশন সম্পন্ন! এখন বটে গিয়ে /video লিখুন।"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "🤖 Bot is running..."

# ==== Run ====
if __name__ == "__main__":
    bot.set_webhook(f"{BASE_URL}/{BOT_TOKEN}")
    app.run(host="0.0.0.0", port=PORT)
