#!/usr/bin/env python3
"""
Script to clear any webhooks that might be interfering with polling mode
"""
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def clear_webhooks():
    """Clear any existing webhooks"""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment")
        return
    
    async with aiohttp.ClientSession() as session:
        # First check current webhook status
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data["ok"]:
                    webhook_info = data["result"]
                    print(f"Current webhook URL: {webhook_info.get('url', 'None')}")
                    print(f"Pending updates: {webhook_info.get('pending_update_count', 0)}")
                else:
                    print("❌ Failed to get webhook info")
                    return
            else:
                print(f"❌ HTTP {response.status} getting webhook info")
                return
        
        # Clear the webhook
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
        async with session.post(url, json={"drop_pending_updates": True}) as response:
            if response.status == 200:
                data = await response.json()
                if data["ok"]:
                    print("✅ Webhook cleared successfully")
                    print("✅ Pending updates dropped")
                else:
                    print(f"❌ Failed to clear webhook: {data}")
            else:
                print(f"❌ HTTP {response.status} clearing webhook")
        
        # Verify webhook is cleared
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if data["ok"]:
                    webhook_info = data["result"]
                    if not webhook_info.get('url'):
                        print("✅ Confirmed: No webhook set")
                    else:
                        print(f"⚠️  Webhook still set: {webhook_info.get('url')}")

if __name__ == "__main__":
    asyncio.run(clear_webhooks())