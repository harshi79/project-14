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

import os
import logging
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# ════════════════════════════════════════════════════════
# 🔧 CONFIGURATION
# ════════════════════════════════════════════════════════
# Using the token from your logs. It will also check for an environment variable.
TOKEN = os.environ.get("BOT_TOKEN") or "8702671509:AAHdAPEjW1AuZ2LSYpmM6eq9e7xJ7IDsRPI"

# 🌐 RENDER KEEP-ALIVE SERVER
# This ensures Render sees an active port and keeps the bot "Live" (Green status).
def run_dummy_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is Running!")
        def log_message(self, format, *args):
            return # Silence logs

    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"✅ Dummy server started on port {port}")
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()
# ════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def login_crunchyroll(email: str, password: str) -> dict:
    """Login to Crunchyroll using SSO page"""
    
    async with async_playwright() as p:
        # Added --no-sandbox and --disable-setuid-sandbox for Render compatibility
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
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
            
            # 2. Handle cookie consent
            logger.info("Handling cookie consent...")
            cookie_selectors = [
                "button:has-text('Accept All')",
                "button:has-text('Accept all')",
                "button:has-text('ACCEPT ALL')",
                "button[data-testid='accept-button']",
                "#onetrust-accept-btn-handler"
            ]
            
            for sel in cookie_selectors:
                try:
                    btn = await page.wait_for_selector(sel, timeout=2000)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(1)
                        break
                except:
                    pass
            
            result["screenshot"] = await page.screenshot()
            
            # 3. Find email field
            email_field = None
            try:
                email_field = await page.wait_for_selector("input[name='login']", timeout=3000)
            except:
                pass
            
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
            result["screenshot"] = await page.screenshot()
            
            # 6. Find password field
            password_field = None
            password_selectors = [
                "input[name='password']",
                "input[type='password']",
                "input[id='password']"
            ]
            
            for sel in password_selectors:
                try:
                    password_field = await page.wait_for_selector(sel, timeout=3000)
                    break
                except:
                    pass
            
            if not password_field:
                await email_field.press("Enter")
                await asyncio.sleep(2)
                password_field = await page.query_selector("input[type='password']")
            
            if not password_field:
                result["message"] = "❌ Password field not found"
                return result
            
            # 7. Fill password
            await password_field.fill(password)
            await asyncio.sleep(0.5)
            result["screenshot"] = await page.screenshot()
            
            # 8. Submit
            submit_button = await page.query_selector("button[type='submit']")
            if submit_button:
                await submit_button.click()
            else:
                await password_field.press("Enter")
            
            # 9. Wait for response
            await asyncio.sleep(8)
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            result["screenshot"] = await page.screenshot()
            
            # 10. Check result
            final_url = page.url.lower()
            page_content = await page.content()
            
            if "incorrect" in page_content.lower() or "wrong" in page_content.lower():
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

# ════════════════════════════════════════════════════════
# 📱 Telegram Commands (PUBLIC ACCESS)
# ════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # CHAT_ID restriction removed to allow anyone to use the bot
    await update.message.reply_text("""
🔐 *Crunchyroll Login Bot*
━━━━━━━━━━━━━━━━━━━━━━━━━━
👋 *Welcome!*
This bot is available for public use.

`/chk email password` - Login & screenshot
`/help` - Instructions
━━━━━━━━━━━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
📚 *How to Use*
━━━━━━━━━━━━━━━━━━━━━━━━━━
`/chk email password`
Example: `/chk my@email.com MyPass123`

The bot will check the account and provide a screenshot of the result page.
━━━━━━━━━━━━━━━━━━━━━━━━━━
    """, parse_mode='Markdown')

async def cmd_chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("🔐 *Usage:* `/chk email password`", parse_mode='Markdown')
        return
    
    email = context.args[0]
    password = " ".join(context.args[1:])
    
    if "@" not in email:
        await update.message.reply_text("❌ Invalid email format")
        return
    
    msg = await update.message.reply_text("🔄 *Processing...* Please wait 15-20 seconds...", parse_mode='Markdown')
    
    logger.info(f"Login attempt by {update.effective_user.id}: {email}")
    result = await login_crunchyroll(email, password)
    
    if result["success"]:
        await msg.edit_text("✅ " + result["message"])
    else:
        await msg.edit_text(result["message"])
    
    if result["screenshot"]:
        masked = f"{email[:3]}***@{email.split('@')[1]}" if "@" in email else email
        await update.message.reply_photo(photo=result["screenshot"], caption=f"📸 Result: {masked}")

def main():
    print("""
╔════════════════════════════════════════╗
║   🔐 Crunchyroll Login Bot             ║
║   (Public Version - No ID Lock)        ║
╚════════════════════════════════════════╝
    """)
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("chk", cmd_chk))
    
    print("✅ Bot is running and open to all users!")
    app.run_polling()

if __name__ == "__main__":
    main()
