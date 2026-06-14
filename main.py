"""
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   🔐 Crunchyroll Login Automation Bot                ║
║   Educational Project - Cyber Security Class         ║
║                                                      ║
╚══════════════════════════════════════════════════════╝

COMMANDS:
  /start  - Welcome message
  /help   - How to use
  /chk email password - Login to Crunchyroll & send screenshot

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEFORE RUNNING:
1. Edit TOKEN and CHAT_ID below (lines 15-16)
2. Run: pip install -r user_requirements.txt
3. Run: python -m playwright install chromium && python -m playwright install-deps
4. Run: python main.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# ════════════════════════════════════════════════════════
# 🔧 CONFIGURATION - SET THESE VALUES
# ════════════════════════════════════════════════════════
TOKEN = "8702671509:AAH_W8e6MebctQtbzoV1sbV1gdJOaIEY77Q"           # Get from @BotFather
CHAT_ID = 7728424218                    # Get from @userinfobot
# ════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────
# 🤖 Crunchyroll Login Function
# ────────────────────────────────────────────────────────

async def login_crunchyroll(email: str, password: str) -> dict:
    """Login to Crunchyroll and return result with screenshot"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        result = {"success": False, "screenshot": None, "message": ""}
        
        try:
            # 1. Open Crunchyroll login page
            await page.goto("https://www.crunchyroll.com/login", timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            # 2. Find email field - try multiple selectors
            email_field = None
            selectors = [
                "input[type='email']", "input[name='email']", "input[id*='email']",
                "input[placeholder*='email' i]", "input[autocomplete='email']",
                "input[id='email-input']", "input[name='signin-email']"
            ]
            for sel in selectors:
                try:
                    email_field = await page.wait_for_selector(sel, timeout=2000)
                    break
                except:
                    continue
            
            if not email_field:
                result["message"] = "❌ Email field not found on page"
                result["screenshot"] = await page.screenshot()
                return result
            
            # 3. Find password field
            password_field = None
            p_selectors = [
                "input[type='password']", "input[name='password']",
                "input[id*='password']", "input[id='password-input']"
            ]
            for sel in p_selectors:
                try:
                    password_field = await page.wait_for_selector(sel, timeout=2000)
                    break
                except:
                    continue
            
            if not password_field:
                result["message"] = "❌ Password field not found on page"
                result["screenshot"] = await page.screenshot()
                return result
            
            # 4. Fill the form
            await email_field.fill(email)
            await asyncio.sleep(0.3)
            await password_field.fill(password)
            await asyncio.sleep(0.3)
            
            # Take screenshot of filled form
            result["screenshot"] = await page.screenshot()
            
            # 5. Click submit - try multiple buttons
            submit = None
            submit_selectors = [
                "button[type='submit']", "input[type='submit']",
                "button:has-text('Sign In')", "button:has-text('Log In')",
                "button[class*='submit']", "button[class*='SignIn']"
            ]
            for sel in submit_selectors:
                try:
                    submit = await page.wait_for_selector(sel, timeout=2000)
                    break
                except:
                    continue
            
            if submit:
                await submit.click()
            else:
                await password_field.press("Enter")
            
            # 6. Wait for response
            await asyncio.sleep(5)
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            # 7. Take result screenshot
            final_screenshot = await page.screenshot()
            result["screenshot"] = final_screenshot
            
            # 8. Check if login worked
            current_url = page.url.lower()
            page_content = await page.content()
            
            if "login" not in current_url or "/login" not in current_url:
                # Check for error messages
                error_found = await page.query_selector(".form-error, .error-message, [class*='error']")
                if error_found:
                    error_text = await error_found.inner_text()
                    result["message"] = f"❌ Login Failed\n\n{error_text[:150]}"
                else:
                    result["success"] = True
                    result["message"] = "✅ Login Successful!\n\nRedirected to: " + page.url[:60]
            else:
                # Still on login page - check why
                if "incorrect" in page_content.lower() or "wrong" in page_content.lower():
                    result["message"] = "❌ Wrong email or password"
                else:
                    result["message"] = "❌ Login not successful - check credentials"
                    
        except Exception as e:
            logger.error(f"Login error: {e}")
            result["message"] = f"❌ Error: {str(e)[:100]}"
        
        finally:
            await browser.close()
        
        return result


# ────────────────────────────────────────────────────────
# 📱 Telegram Command Handlers
# ────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Professional welcome message"""
    if str(update.message.chat_id) != str(CHAT_ID):
        await update.message.reply_text("❌ Unauthorized")
        return
    
    welcome = """
🔐 *Crunchyroll Login Bot*
━━━━━━━━━━━━━━━━━━━━━━━━━━

👋 *Welcome!*

This bot demonstrates web login automation for your cybersecurity class project.

━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 *Commands:*

• `/chk email password` - Login & screenshot
• `/help` - Instructions

━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 *Example:*
`/chk myemail@gmail.com MyPass123`

━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(welcome, parse_mode='Markdown')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full instructions"""
    if str(update.message.chat_id) != str(CHAT_ID):
        await update.message.reply_text("❌ Unauthorized")
        return
    
    help_text = """
📚 *How to Use*
━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 *Main Command:*

`/chk email password`

Example:
```
/chk student@gmail.com SecretPass
```

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔄 *What it does:*

1. Opens Crunchyroll login page
2. Fills email & password
3. Clicks Sign In
4. Takes screenshot
5. Sends result to you

━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 *Results:*

✅ *Success* → Dashboard screenshot
❌ *Failed* → Error message screenshot

━━━━━━━━━━━━━━━━━━━━━━━━━━

🔒 *Security:*
• Uses YOUR credentials only
• Processed locally only
• No data stored anywhere

━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def cmd_chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main login check command"""
    if str(update.message.chat_id) != str(CHAT_ID):
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "🔐 *Usage:* `/chk email password`\n\n"
            "*Example:* `/chk my@email.com mypass`",
            parse_mode='Markdown'
        )
        return
    
    email = context.args[0]
    password = " ".join(context.args[1:])
    
    # Validate email
    if "@" not in email or "." not in email.split("@")[-1]:
        await update.message.reply_text("❌ Invalid email format")
        return
    
    # Show processing message
    msg = await update.message.reply_text(
        "🔄 *Processing...*\n\n"
        "⏳ Opening Crunchyroll\n"
        "⏳ Filling form\n"
        "⏳ Submitting\n"
        "⏳ Capturing screenshot\n\n"
        "Please wait...",
        parse_mode='Markdown'
    )
    
    logger.info(f"Login attempt: {email}")
    
    # Run login
    result = await login_crunchyroll(email, password)
    
    # Send result
    if result["success"]:
        await msg.edit_text("✅ " + result["message"])
    else:
        await msg.edit_text(result["message"])
    
    if result["screenshot"]:
        masked_email = f"{email[:3]}***@{email.split('@')[1]}"
        await update.message.reply_photo(
            photo=result["screenshot"],
            caption=f"📸 Result: {masked_email}"
        )


# ────────────────────────────────────────────────────────
# 🚀 Main
# ────────────────────────────────────────────────────────

def main():
    print("""
╔════════════════════════════════════════╗
║   🔐 Crunchyroll Login Bot             ║
║   Educational Project                  ║
╚════════════════════════════════════════╝
    """)
    
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ SETUP REQUIRED!")
        print("")
        print("1. Edit main.py → Set TOKEN (line 15)")
        print("2. Edit main.py → Set CHAT_ID (line 16)")
        print("")
        print("How to get TOKEN:")
        print("  Telegram → @BotFather → /newbot")
        print("")
        print("How to get CHAT_ID:")
        print("  Telegram → @userinfobot → send message")
        print("")
        print("First time setup:")
        print("  pip install -r user_requirements.txt")
        print("  python -m playwright install chromium")
        print("  python -m playwright install-deps")
        return
    
    print("✅ Bot starting...")
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chk", cmd_chk))
    
    print("✅ Running! Message /start to your bot")
    app.run_polling()


if __name__ == "__main__":
    main()