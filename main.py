"""
╔══════════════════════════════════════════════════════╗
║   🔐 Crunchyroll Login Automation Bot                ║
║   Educational Project - Cyber Security Class         ║
╚══════════════════════════════════════════════════════╝

COMMANDS:
  /start  - Welcome message
  /help   - How to use
  /chk email password - Login to Crunchyroll & send screenshot
"""

import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# ════════════════════════════════════════════════════════
# 🔧 CONFIGURATION
# ════════════════════════════════════════════════════════
TOKEN = "8702671509:AAFWwAG3AQe0jfLRZmtONybs4Y-PH1AMaqo"
CHAT_ID = 7728424218
# ════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            
            # 3. Find email field - use name='login' based on your debug output!
            email_field = None
            
            # Try the exact selector from your debug
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
            
            # 4. Fill email and wait for password field to appear
            await email_field.fill(email)
            await asyncio.sleep(1)
            
            # 5. Press Tab or Enter to trigger password field
            await email_field.press("Tab")
            await asyncio.sleep(1)
            
            # Take screenshot after email
            result["screenshot"] = await page.screenshot()
            
            # 6. Find password field (may be dynamically generated)
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
                # Try pressing Enter on email field to reveal password
                await email_field.press("Enter")
                await asyncio.sleep(2)
                
                for sel in password_selectors:
                    try:
                        password_field = await page.wait_for_selector(sel, timeout=3000)
                        break
                    except:
                        pass
            
            if not password_field:
                # Check current page for any new inputs
                inputs = await page.query_selector_all("input")
                for inp in inputs:
                    t = await inp.get_attribute("type")
                    n = await inp.get_attribute("name")
                    if t == "password" or "password" in str(n).lower():
                        password_field = inp
                        break
            
            if not password_field:
                result["message"] = "❌ Password field not found - may need captcha or different flow"
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
            
            # Check for error messages
            page_content = await page.content()
            if "incorrect" in page_content.lower() or "wrong" in page_content.lower():
                result["message"] = "❌ Wrong email or password"
            elif "sso.crunchyroll.com/login" in final_url:
                result["message"] = "❌ Login not successful - check credentials"
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


# ════════════════════════════════════════════════════════
# 📱 Telegram Commands
# ════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != str(CHAT_ID):
        await update.message.reply_text("❌ Unauthorized")
        return
    
    await update.message.reply_text("""
🔐 *Crunchyroll Login Bot*
━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 *Welcome!*
`/chk email password` - Login & screenshot
`/help` - Instructions
━━━━━━━━━━━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != str(CHAT_ID):
        await update.message.reply_text("❌ Unauthorized")
        return
    
    await update.message.reply_text("""
📚 *How to Use*
━━━━━━━━━━━━━━━━━━━━━━━━━━
`/chk email password`
Example: `/chk my@email.com MyPass`
━━━━━━━━━━━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')


async def cmd_chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.message.chat_id) != str(CHAT_ID):
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("🔐 *Usage:* `/chk email password`", parse_mode='Markdown')
        return
    
    email = context.args[0]
    password = " ".join(context.args[1:])
    
    if "@" not in email:
        await update.message.reply_text("❌ Invalid email")
        return
    
    msg = await update.message.reply_text("🔄 *Processing...* Please wait 15-20 seconds...", parse_mode='Markdown')
    
    logger.info(f"Login attempt: {email}")
    result = await login_crunchyroll(email, password)
    
    if result["success"]:
        await msg.edit_text("✅ " + result["message"])
    else:
        await msg.edit_text(result["message"])
    
    if result["screenshot"]:
        masked = f"{email[:3]}***@{email.split('@')[1]}"
        await update.message.reply_photo(photo=result["screenshot"], caption=f"📸 Result: {masked}")


def main():
    print("""
╔════════════════════════════════════════╗
║   🔐 Crunchyroll Login Bot             ║
╚════════════════════════════════════════╝
    """)
    
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Edit main.py - Set TOKEN and CHAT_ID")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chk", cmd_chk))
    
    print("✅ Bot running!")
    app.run_polling()


if __name__ == "__main__":
    main()
