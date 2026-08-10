import os
import requests
import logging

logger = logging.getLogger(__name__)

class TelegramAlerter:
    """Sends trade alerts to a configured Telegram chat."""
    
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        
    def send_alert(self, text: str) -> bool:
        """Send a plain text alert."""
        if not self.bot_token or not self.chat_id:
            logger.debug("Telegram credentials not configured, skipping alert.")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=5)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
            
    def format_trade_plan(self, symbol: str, tp) -> str:
        """Format a TradePlan for Telegram."""
        return (
            f"🔥 *New Setup: {symbol}*\n\n"
            f"🎯 *Entry:* ₹{tp.entry:.2f} ({tp.entry_type})\n"
            f"🛑 *Stop Loss:* ₹{tp.stop_loss:.2f} ({tp.trailing_stop_type})\n"
            f"🏁 *Target 1:* ₹{tp.target_1:.2f}\n"
            f"🏁 *Target 2:* ₹{tp.target_2:.2f}\n"
            f"⚖️ *Risk/Reward:* {tp.risk_reward:.2f}\n"
            f"⏱️ *Time Stop:* {tp.decay_note}"
        )
