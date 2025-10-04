# app/DataStream/datastream.py

import httpx
import random
import logging
from typing import List, Dict, Optional

from app.config import PROXY_URL, USER_AGENTS

logger = logging.getLogger(__name__)


def get_headers() -> Dict[str, str]:
    """Return randomized headers to mimic real browsers."""
    return {
        "Accept": "application/json",
        "User-Agent": random.choice(USER_AGENTS),
    }


async def _fetch(path: str) -> Optional[List[Dict]]:
    """
    Fetch data from Dexscreener via Cloudflare Worker proxy.
    
    Args:
        path: Dexscreener API path (e.g., "/token-profiles/latest/v1")
    
    Returns:
        JSON response as list of dicts, or None on failure
    """
    target_url = f"https://api.dexscreener.com{path}"
    proxy_url = f"{PROXY_URL}?url={target_url}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(proxy_url, headers=get_headers())
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"Fetched {len(data)} items from {path}")
            return data
    except Exception as e:
        logger.error(f"Failed to fetch {path}: {e}")
        return None


# ------------------------
# Public Functions
# ------------------------

async def fetch_token_profiles() -> Optional[List[Dict]]:
    return await _fetch("/token-profiles/latest/v1")


async def fetch_token_boosts() -> Optional[List[Dict]]:
    return await _fetch("/token-boosts/latest/v1")


async def fetch_top_tokens() -> Optional[List[Dict]]:
    return await _fetch("/token-boosts/top/v1")


# function that joins it all together

# app/DataStream/datastream.py
# ... (keep the rest of the file above unchanged) ...

async def fetch_solana_tokens() -> Optional[List[Dict]]:
    # 1) Gather candidates from your tokenstream sources
    token_profiles = await fetch_token_profiles()
    token_boosts = await fetch_token_boosts()
    top_tokens_list = await fetch_top_tokens()

    raw_tokens = []
    if token_profiles:
        raw_tokens.extend(token_profiles)
    if token_boosts:
        raw_tokens.extend(token_boosts)
    if top_tokens_list:
        raw_tokens.extend(top_tokens_list)

    logger.info(f"Fetched {len(raw_tokens)} raw tokens from tokenstream")

    # 2) dedupe Solana mints
    seen = set()
    unique_solana_tokens = []
    for token in raw_tokens:
        # Dexscreener returns chainId sometimes as int or str; normalize defensively
        chain = token.get("chainId") or token.get("chain")
        if chain and str(chain).lower() != "solana":
            continue
        key = token.get("tokenAddress") or token.get("tokenAddress")
        if key and key not in seen:
            seen.add(key)
            unique_solana_tokens.append(token)

    logger.info(f"Filtered {len(unique_solana_tokens)} unique Solana tokens")

    # Return the deduped list (could be empty)
    return unique_solana_tokens
