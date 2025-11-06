from typing import Any, Dict, Optional


def _fmt_money(value: Optional[float]) -> str:
    if value is None:
        return "-"
    try:
        if value >= 1_000_000_000:
            return f"${value/1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        if value >= 1_000:
            return f"${value/1_000:.2f}K"
        return f"${value:.6f}" if value < 1 else f"${value:.2f}"
    except Exception:
        return str(value)


def _pct(value: Optional[float]) -> str:
    if value is None:
        return "-"
    try:
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:.2f}%"
    except Exception:
        return str(value)


def _link(url: Optional[str], text: str) -> str:
    return f"<a href=\"{url}\">{text}</a>" if url else text


def format_pro_message(token: Dict[str, Any]) -> str:
    digest = token.get("digest", {})
    meta = digest.get("meta", {})
    market = digest.get("market", {})
    liquidity = digest.get("liquidity", {})
    socials = digest.get("socials", {})
    flags = digest.get("flags", {})
    derived = digest.get("derived", {})
    score = token.get("score", {})

    name = meta.get("name") or token.get("name") or "Token"
    symbol = token.get("symbol") or meta.get("symbol") or "?"
    image_url = meta.get("image_url") or token.get("image_url")
    dexscreener_url = meta.get("dexscreener_url") or token.get("dexscreener_url")

    website = socials.get("website")
    website_url = None
    if isinstance(website, list) and website:
        website_url = website[0]
    elif isinstance(website, str):
        website_url = website

    lines = []
    # Image is sent via send_photo; caption below
    lines.append(f"<b>Token:</b> {_link(dexscreener_url, f'{name} ({symbol})')}\n")

    lines.append("<b>Market Data:</b>")
    lines.append(f"- Price: {_fmt_money(market.get('price_usd'))}")
    lines.append(f"- Market Cap: {_fmt_money(market.get('market_cap'))}")
    lines.append(f"- 24h Volume: {_fmt_money(market.get('volume_24h'))}")
    lines.append(f"- 1h Price Change: {_pct(market.get('price_change_1h'))}")
    lines.append(f"- 24h Price Change: {_pct(market.get('price_change_24h'))}\n")

    lines.append("<b>Liquidity & Activity:</b>")
    lines.append(f"- Total Liquidity: {_fmt_money(liquidity.get('total_liquidity_usd'))}")
    lines.append(f"- Liquidity Ratio: {liquidity.get('liquidity_ratio', '-')}")
    lines.append(
        f"- Buys (24h): {market.get('buys_24h', '-')}, Sells (24h): {market.get('sells_24h', '-')}\n"
    )

    lines.append("<b>Score:</b> " + str(score.get("final_score", "-")))
    lines.append("<b>Classification:</b> " + str(score.get("classification", "-")) + "\n")

    lines.append("<b>Additional Insights:</b>")
    lines.append(f"- Momentum Index: {market.get('momentum_index', '-')}")
    lines.append(f"- Volatility Score: {market.get('volatility_score', '-')}")
    lines.append(f"- Velocity Score: {market.get('velocity_score', '-')}")
    lines.append(f"- Derived Stability Index: {derived.get('stability_index', '-')}")
    lines.append(f"- Decentralization Score: {derived.get('decentralization_score', '-')}")
    lines.append(f"- Survivability Score: {derived.get('survivability_score', '-')}")
    lines.append(f"- Pump Probability: {derived.get('pump_probability', '-')}\n")

    lines.append(_link(dexscreener_url, "🔗 Visit Dexscreener"))
    lines.append("")
    lines.append("<code>")
    lines.append(f"Token Address: {token.get('address')}")
    if website_url:
        lines.append(f"Website: {website_url}")
    if socials.get("twitter_url"):
        lines.append(f"Twitter: {socials.get('twitter_url')}")
    lines.append("</code>")

    return "\n".join(lines)


def format_free_message(token: Dict[str, Any]) -> str:
    digest = token.get("digest", {})
    meta = digest.get("meta", {})
    market = digest.get("market", {})
    liquidity = digest.get("liquidity", {})
    socials = digest.get("socials", {})

    name = meta.get("name") or token.get("name") or "Token"
    symbol = token.get("symbol") or meta.get("symbol") or "?"
    image_url = meta.get("image_url") or token.get("image_url")
    dexscreener_url = meta.get("dexscreener_url") or token.get("dexscreener_url")

    website = socials.get("website")
    website_url = None
    if isinstance(website, list) and website:
        website_url = website[0]
    elif isinstance(website, str):
        website_url = website

    lines = []
    lines.append(f"<b>Token:</b> {_link(dexscreener_url, f'{name} ({symbol})')}\n")

    lines.append("<b>Market Data:</b>")
    lines.append(f"- Price: {_fmt_money(market.get('price_usd'))}")
    lines.append(f"- Market Cap: {_fmt_money(market.get('market_cap'))}")
    lines.append(f"- 24h Volume: {_fmt_money(market.get('volume_24h'))}")
    lines.append(f"- 1h Price Change: {_pct(market.get('price_change_1h'))}\n")

    lines.append("<b>Liquidity:</b>")
    lines.append(f"- Total Liquidity: {_fmt_money(liquidity.get('total_liquidity_usd'))}\n")

    lines.append("<b>Risk Flags:</b>")
    lines.append(f"- Rug Likelihood: {digest.get('flags', {}).get('rug_likelihood_flag', '-') }\n")

    lines.append(_link(dexscreener_url, "🔗 Visit Dexscreener"))
    lines.append("")
    lines.append("<code>")
    lines.append(f"Token Address: {token.get('address')}")
    if website_url:
        lines.append(f"Website: {website_url}")
    lines.append("</code>")

    return "\n".join(lines)

