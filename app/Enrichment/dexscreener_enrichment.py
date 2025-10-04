import httpx
from app.config import PROXY_URL,DEX_TIMEOUT
import asyncio
from typing import List, Dict, Any




async def fetch_dexscreener_data(chain_id: str, token_addresses: List[str]) -> List[Dict]:
    """
    Fetch full Dexscreener token/pair objects for up to 30 addresses at a time,
    but go through the Cloudflare Worker proxy to avoid Render IP ban.
    """
    target_url = f"https://api.dexscreener.com/tokens/v1/{chain_id}/{','.join(token_addresses)}"
    proxy_url = f"{PROXY_URL}?url={target_url}"

    async with httpx.AsyncClient(timeout=DEX_TIMEOUT) as client:
        r = await client.get(proxy_url, headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else []
    

