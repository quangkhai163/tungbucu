from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import asyncio

TOKEN = "8069437407:AAFqVxUgLemYg7_mr-OhSnmY89oThGCOc5k"

# Hàm bypass
async def bypass_yeumoney(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.binary_location = "/usr/bin/chromium"

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    await asyncio.sleep(15)  # đợi như trên trình duyệt

    result = driver.current_url
    driver.quit()
    return result

# Lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chào bạn! Gửi mình link yeumoney để bypass.")

# Xử lý tin nhắn chứa link
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if "yeumoney.com" not in url:
        await update.message.reply_text("Vui lòng gửi link hợp lệ từ yeumoney.com.")
        return

    await update.message.reply_text("Đang xử lý... đợi 15s.")

    try:
        result = await bypass_yeumoney(url)
        if "yeumoney.com" in result:
            await update.message.reply_text("Không bypass được hoặc link không đổi.")
        else:
            await update.message.reply_text(f"Bypass thành công:\n{result}")
    except Exception as e:
        await update.message.reply_text("Lỗi xảy ra khi xử lý link.")
        print(e)

# Chạy bot
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()