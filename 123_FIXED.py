import logging
import asyncio
import json
import os
from datetime import datetime

from telegram import (
    Update,
    InputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)
from playwright.async_api import async_playwright


SUPPORTED_DOMAINS = [
    "link4m.com", "link1s.com", "yeumony.xyz",
    "yeumony.com", "yeumoney.com", "link4sub.com"
]
# ======== Cấu hình ========
TOKEN = "7441292874:AAEZBck1OTom82vHwx_0dCweW9mDRqcUUnY"  # <-- Thay bằng token bot của bạn
ALLOWED_USERS = [5976243149]  # <-- Thay bằng Telegram ID admin của bạn
GROUP_FILE = "allowed_groups.json"
ADMIN_CONTACT = "@qkdzvcl206"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ======== Group quản lý quyền ========

def load_allowed_groups():
    if not os.path.exists(GROUP_FILE):
        return []
    with open(GROUP_FILE, "r") as f:
        return json.load(f)

def save_allowed_groups(groups):
    with open(GROUP_FILE, "w") as f:
        json.dump(groups, f)

def is_authorized(update: Update) -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    allowed_groups = load_allowed_groups()

    if update.effective_chat.type == "private":
        return user_id in ALLOWED_USERS

    if update.effective_chat.type in ["group", "supergroup"]:
        return chat_id in allowed_groups or user_id in ALLOWED_USERS

    return False

# ======== Vượt Link ========

async def bypass_link(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        })

        try:
            await page.goto(url, timeout=60000)
            domain = url.split("/")[2]
            original_url = page.url

            click_selectors = [
                "#linkBtn", "#btn-main", ".get-link", ".button", "a[href*='redirect']",
                "button[class*='btn']", "a[class*='btn']", "a[class*='continue']"
            ]

            for _ in range(10):
                for selector in click_selectors:
                    try:
                        await page.click(selector, timeout=1000)
                    except:
                        continue
                await page.wait_for_timeout(3000)

            for i in range(120):
                if page.url != original_url and domain not in page.url:
                    break
                await page.wait_for_timeout(1000)

            result = page.url

            if result == url or domain in result:
                await page.screenshot(path="debug.png")
                return json.dumps({
                    "status": "error",
                    "message": "Không thể vượt link hoặc vẫn chưa redirect xong sau 2 phút."
                }, ensure_ascii=False)

            with open("log.txt", "a") as log:
                log.write(f"[{datetime.now()}] {url} -> {result}\n")

            return json.dumps({
                "status": "success",
                "domain": domain,
                "result": result
            }, ensure_ascii=False)

        except Exception as e:
            await page.screenshot(path="debug.png")
            return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

        finally:
            await browser.close()

# ======== Command Handlers & Menu ========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text(json.dumps({
            "status": "unauthorized",
            "message": f"Nhóm này chưa được duyệt để sử dụng bot. Vui lòng liên hệ admin {ADMIN_CONTACT} để yêu cầu truy cập."
        }, ensure_ascii=False))
        return

    keyboard = [
        [InlineKeyboardButton("🚀 Gửi link rút gọn", callback_data='bypass_help')],
        [
            InlineKeyboardButton("👥 Thêm nhóm", callback_data='add_group'),
            InlineKeyboardButton("❌ Xoá nhóm", callback_data='del_group'),
        ],
        [InlineKeyboardButton("📞 Liên hệ Admin", url=f"https://t.me/{ADMIN_CONTACT.strip('@')}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🤖 Chào bạn! Mình là bot hỗ trợ vượt link rút gọn của admin @qkdzvcl206.\n\n"
        "Hãy chọn một chức năng bên dưới:",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "bypass_help":
        context.user_data["allow_link"] = True
        await query.edit_message_text("📤 Gửi cho mình link rút gọn (link4m, link1s, yeumony, v.v.) trong đoạn chat này nhé!")
    elif data == "add_group":
        await query.edit_message_text("🧩 Để thêm nhóm, dùng lệnh /addgr trong nhóm mà bạn là admin.")
    elif data == "del_group":
        await query.edit_message_text("🧹 Để xoá nhóm, dùng lệnh /delgr trong nhóm đó.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("allow_link"):
        return
if not is_authorized(update):
        await update.message.reply_text(json.dumps({
            "status": "unauthorized",
            "message": f"Nhóm này chưa được duyệt để sử dụng bot. Vui lòng liên hệ admin {ADMIN_CONTACT} để yêu cầu truy cập."
        }, ensure_ascii=False))
        return

    message = update.message.text.strip()
    if any(domain in message for domain in SUPPORTED_DOMAINS):
        await update.message.reply_text(json.dumps({
            "status": "processing",
            "message": "Đang xử lý link, vui lòng chờ tối đa 2 phút..."
        }, ensure_ascii=False))

        result = await bypass_link(message)
        await update.message.reply_text(f"```json
{result}
```", parse_mode="Markdown")

        if json.loads(result).get("status") == "error":
            try:
                await update.message.reply_photo(InputFile("debug.png"))
            except:
                pass
    else:
        await update.message.reply_text(json.dumps({
            "status": "invalid",
            "message": "Link không được hỗ trợ hoặc không hợp lệ."
        }, ensure_ascii=False))

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(json.dumps({
            "status": "unauthorized",
            "message": "Bạn không có quyền dùng lệnh này."
        }, ensure_ascii=False))
        return

    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text(json.dumps({
            "status": "error",
            "message": "Lệnh này chỉ dùng trong nhóm."
        }, ensure_ascii=False))
        return

    allowed = load_allowed_groups()
    if chat_id in allowed:
        await update.message.reply_text(json.dumps({
            "status": "exists",
            "message": "Nhóm này đã có trong danh sách cho phép."
        }, ensure_ascii=False))
    else:
        allowed.append(chat_id)
        save_allowed_groups(allowed)
        await update.message.reply_text(json.dumps({
            "status": "success",
            "message": "Đã thêm nhóm vào danh sách cho phép."
        }, ensure_ascii=False))

async def del_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(json.dumps({
            "status": "unauthorized",
            "message": "Bạn không có quyền dùng lệnh này."
        }, ensure_ascii=False))
        return

    allowed = load_allowed_groups()
    if chat_id in allowed:
        allowed.remove(chat_id)
        save_allowed_groups(allowed)
        await update.message.reply_text(json.dumps({
            "status": "success",
            "message": "Đã xoá nhóm khỏi danh sách cho phép."
        }, ensure_ascii=False))
    else:
        await update.message.reply_text(json.dumps({
            "status": "not_found",
            "message": "Nhóm này chưa có trong danh sách."
        }, ensure_ascii=False))

# ======== Run Bot ========

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addgr", add_group))
    app.add_handler(CommandHandler("delgr", del_group))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("✅ Bot đã chạy...")
    app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())