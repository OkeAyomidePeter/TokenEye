# app/Digestion/utils.py

from typing import Any, Dict, List, Optional


def safe_get_nested(data: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """
    Safely get nested dictionary values using a list of keys.
    """
    try:
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    except (TypeError, KeyError):
        return default


def normalize_percentage(value: Any, max_value: float = 100.0) -> float:
    """
    Normalize a percentage value to a 0–1 range.
    """
    try:
        if value is None:
            return 0.0
        num_value = float(value)
        normalized = num_value / max_value
        return max(0.0, min(1.0, normalized))
    except (ValueError, TypeError):
        return 0.0


def safe_divide(numerator: Any, denominator: Any, default: float = 0.0) -> float:
    """
    Safely divide two values with zero and error handling.
    """
    try:
        num = float(numerator) if numerator is not None else 0.0
        den = float(denominator) if denominator not in [None, 0] else 0.0
        if den == 0:
            return default
        return num / den
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def extract_token_address(enriched_token: Dict[str, Any]) -> Optional[str]:
    """
    Extract token address from enriched token data across possible locations.
    """
    locations = [
        ["base_token", "address"],
        ["rpc_data", "data", "parsed", "info", "mint"],
        ["address"],
        ["tokenAddress"]
    ]
    for location in locations:
        address = safe_get_nested(enriched_token, location)
        if address:
            return str(address)
    return None


def calculate_age_score(creation_time: Optional[str], max_age_days: int = 30) -> float:
    """
    Calculate normalized token age score (0–1) given creation time.
    """
    if not creation_time:
        return 0.0
    try:
        from datetime import datetime
        created_dt = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
        age_seconds = (datetime.utcnow() - created_dt.replace(tzinfo=None)).total_seconds()
        age_days = age_seconds / (24 * 3600)
        return min(1.0, age_days / max_age_days)
    except (ValueError, TypeError):
        return 0.0


def validate_digest_structure(digest: Dict[str, Any]) -> bool:
    """
    Validate that a digest result contains all expected sections.
    """
    required_sections = ["meta", "market", "holders", "liquidity", "socials", "flags", "derived"]
    for section in required_sections:
        if section not in digest or not isinstance(digest[section], dict):
            return False
    return True


def merge_digest_results(digest_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge multiple digest result dictionaries into a unified structure.
    """
    if not digest_results:
        return {}

    merged: Dict[str, Any] = {}
    for result in digest_results:
        if isinstance(result, dict):
            for key, value in result.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    merged[key].update(value)

    return merged
