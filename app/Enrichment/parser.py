from typing import Dict, Any, List, Optional
import datetime

def parse_dexscreener_token(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single Dexscreener token JSON response.
    """
    # Base / Quote
    base = raw.get("baseToken", {})
    quote = raw.get("quoteToken", {})

    # Socials & websites cleanup
    socials = {
        s.get("type"): s.get("url")
        for s in raw.get("info", {}).get("socials", [])
        if s.get("type") and s.get("url")
    }
    websites = [w.get("url") for w in raw.get("info", {}).get("websites", [])]

    return {
        "chain_id": raw.get("chainId"),
        "dex_id": raw.get("dexId"),
        "pair_address": raw.get("pairAddress"),
        "url": raw.get("url"),

        # Token info
        "base_token": {
            "address": base.get("address"),
            "name": base.get("name"),
            "symbol": base.get("symbol"),
        },
        "quote_token": {
            "address": quote.get("address"),
            "name": quote.get("name"),
            "symbol": quote.get("symbol"),
        },

        # Prices & market data
        "price_native": float(raw.get("priceNative") or 0),
        "price_usd": float(raw.get("priceUsd") or 0),
        "fdv": float(raw.get("fdv") or 0),
        "market_cap": float(raw.get("marketCap") or 0),

        # Activity metrics
        "txns": raw.get("txns", {}),
        "volume": raw.get("volume", {}),
        "price_change": raw.get("priceChange", {}),

        # Pair age
        "pair_created_at": (
            datetime.datetime.fromtimestamp(raw["pairCreatedAt"] / 1000)
            if raw.get("pairCreatedAt") is not None
            else None
        ),

        # Metadata
        "info": {
            "image": raw.get("info", {}).get("imageUrl"),
            "header": raw.get("info", {}).get("header"),
            "open_graph": raw.get("info", {}).get("openGraph"),
            "websites": websites,
            "socials": socials,
        },
    }

def parse_dexscreener_batch(raw_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize a batch of Dexscreener tokens.
    """
    return [parse_dexscreener_token(r) for r in raw_list if r]
