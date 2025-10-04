# app/Schemas/utils.py

from typing import Dict, Optional



def normalize_links(raw_links: list[dict]) -> Dict[str, Optional[str]]:
    """Convert Dexscreener's arbitrary links into a fixed dict structure."""
    normalized: Dict[str, Optional[str]] = {
        "website": None,
        "twitter": None,
        "telegram": None,
        "discord": None,
        "medium": None,
    }

    if not raw_links:
        return normalized

    for link in raw_links:
        label = (link.get("label") or link.get("type") or "").lower()
        url = link.get("url")

        if "twitter" in label:
            normalized["twitter"] = url
        elif "telegram" in label:
            normalized["telegram"] = url
        elif "discord" in label:
            normalized["discord"] = url
        elif "medium" in label:
            normalized["medium"] = url
        elif "website" in label or label == "":
            normalized["website"] = url

    return normalized
