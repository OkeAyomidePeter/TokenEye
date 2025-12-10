# app/config.py
from dotenv import load_dotenv, find_dotenv
import os

# Load .env from the project root (robust to different working directories)
load_dotenv(find_dotenv(), override=False)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/tokenscout"
)


PROXY_URL = "https://still-truth-bbe9.ayoo52294.workers.dev/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.68 Mobile Safari/537.36",
]


DEX_TIMEOUT = 15

RUGCHECK_BASE = "https://api.rugcheck.xyz/v1"


TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ALERT_CHANNEL = os.getenv("TELEGRAM_ALERT_CHANNEL")
TELEGRAM_PRO_ALERT_CHANNEL = os.getenv("TELEGRAM_PRO_ALERT_CHANNEL")


