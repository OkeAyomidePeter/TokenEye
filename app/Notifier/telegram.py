from typing import Any, Dict, Optional, Tuple
import logging
import asyncio
import time

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError

from app.config import TELEGRAM_TOKEN, TELEGRAM_ALERT_CHANNEL, TELEGRAM_PRO_ALERT_CHANNEL
from app.Notifier.message_composer import format_pro_message, format_free_message, _links_buttons_from_token

logger = logging.getLogger(__name__)

_bot: Optional[Bot] = None

# -----------------------------
# Rate limiting & dedup settings
# -----------------------------
GLOBAL_MIN_INTERVAL_SEC = 1.5
PER_CHAT_MIN_INTERVAL_SEC = 1.5
DEDUP_WINDOW_SEC = 300  # 5 min

_last_global_sent: float = 0.0
_per_chat_last_sent: Dict[str, float] = {}
_dedup_cache: Dict[Tuple[str, str], float] = {}
_rate_lock = asyncio.Lock()


def _get_bot() -> Bot:
    global _bot
    if _bot is None:
        if not TELEGRAM_TOKEN:
            raise RuntimeError("TELEGRAM_TOKEN not configured")
        _bot = Bot(
            token=TELEGRAM_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    return _bot


def _resolve_channels() -> Tuple[Optional[str], Optional[str]]:
    return TELEGRAM_PRO_ALERT_CHANNEL, TELEGRAM_ALERT_CHANNEL


def _image_url(token: Dict[str, Any]) -> Optional[str]:
    digest = token.get("digest", {})
    meta = digest.get("meta", {})
    return meta.get("image_url") or token.get("image_url")


def _is_duplicate(chat_id: str, address: str) -> bool:
    now = time.monotonic()
    key = (chat_id, address)
    ts = _dedup_cache.get(key)
    if ts is None:
        return False
    if now - ts <= DEDUP_WINDOW_SEC:
        return True
    _dedup_cache.pop(key, None)
    return False


def _mark_sent(chat_id: str, address: str) -> None:
    _dedup_cache[(chat_id, address)] = time.monotonic()


async def _apply_rate_limits(chat_id: str) -> None:
    async with _rate_lock:
        now = time.monotonic()

        last_chat = _per_chat_last_sent.get(chat_id, 0.0)
        if now - last_chat < PER_CHAT_MIN_INTERVAL_SEC:
            await asyncio.sleep(PER_CHAT_MIN_INTERVAL_SEC - (now - last_chat))
            now = time.monotonic()

        global _last_global_sent
        if now - _last_global_sent < GLOBAL_MIN_INTERVAL_SEC:
            await asyncio.sleep(GLOBAL_MIN_INTERVAL_SEC - (now - _last_global_sent))
            now = time.monotonic()

        _last_global_sent = now
        _per_chat_last_sent[chat_id] = now


async def _safe_send(bot: Bot, method, chat_id: str, **kwargs):
    """
    Execute Telegram API call with retry after rate-limit (TelegramRetryAfter).
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await method(chat_id=chat_id, **kwargs)
        except TelegramRetryAfter as e:
            retry_after = getattr(e, "retry_after", 10)
            logger.warning(f"Rate limited: waiting {retry_after}s before retry (chat {chat_id})")
            await asyncio.sleep(retry_after + 1)
        except TelegramAPIError as e:
            logger.error(f"Telegram API error on {method.__name__}: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected Telegram send error: {e}", exc_info=True)
            break
    return None


async def send_token_notification(token: Dict[str, Any], pro_threshold: float = 75.0) -> Dict[str, Any]:
    """
    Send formatted message or photo with retry and dedup protection.
    """
    bot = _get_bot()
    pro_channel, free_channel = _resolve_channels()

    score = token.get("score", {})
    final_score = float(score.get("final_score", 0.0) or 0.0)
    is_pro = final_score >= pro_threshold and pro_channel

    caption = format_pro_message(token) if is_pro else format_free_message(token)
    channel_id = pro_channel if is_pro else free_channel

    if not channel_id:
        logger.warning("No Telegram channel configured")
        return {"sent": False, "reason": "no_channel"}

    if _is_duplicate(channel_id, str(token.get("address"))):
        return {"sent": False, "reason": "deduplicated"}

    await _apply_rate_limits(channel_id)
    photo = _image_url(token)
    kb, _ = _links_buttons_from_token(token)

    try:
        if photo:
            result = await _safe_send(bot, bot.send_photo, chat_id=channel_id, photo=photo, caption=caption, reply_markup=kb)
        else:
            result = await _safe_send(bot, bot.send_message, chat_id=channel_id, text=caption, reply_markup=kb)

        if result:
            _mark_sent(channel_id, str(token.get("address")))
            return {"sent": True, "channel": channel_id, "pro": is_pro}
        return {"sent": False, "reason": "failed"}
    except Exception as e:
        logger.error(f"Telegram send fatal error: {e}", exc_info=True)
        return {"sent": False, "error": str(e)}
