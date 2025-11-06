# app/Scoring/market_scorer.py

from typing import Optional, Dict, Any
import logging
import math

logger = logging.getLogger(__name__)


def normalize_price_change(value: float, min_val: float = -100, max_val: float = 500) -> float:
    """
    Normalize price change percentage to 0-1 range.
    
    Args:
        value: Price change percentage
        min_val: Minimum expected value (default: -100%)
        max_val: Maximum expected value (default: 500%)
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    # Clamp value to expected range
    clamped = max(min_val, min(max_val, value))
    # Normalize: (value - min) / (max - min)
    normalized = (clamped - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def normalize_buy_sell_ratio(value: float, min_val: float = 0.1, max_val: float = 5.0) -> float:
    """
    Normalize buy/sell ratio to 0-1 range.
    Higher ratio = more buy pressure = better.
    
    Args:
        value: Buy/sell ratio
        min_val: Minimum expected value
        max_val: Maximum expected value
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None or value <= 0:
        return 0.0
    
    # Clamp and normalize
    clamped = max(min_val, min(max_val, value))
    normalized = (clamped - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def normalize_volume(value: float, min_val: float = 1000, max_val: float = 1000000) -> float:
    """
    Normalize volume to 0-1 range using log scale.
    
    Args:
        value: Volume in USD
        min_val: Minimum expected value
        max_val: Maximum expected value
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None or value <= 0:
        return 0.0
    
    # Use log scale for volume
    if value < min_val:
        return 0.0
    if value > max_val:
        return 1.0
    
    log_val = math.log10(value)
    log_min = math.log10(min_val)
    log_max = math.log10(max_val)
    
    normalized = (log_val - log_min) / (log_max - log_min)
    return max(0.0, min(1.0, normalized))


def normalize_momentum_index(value: float, min_val: float = 0, max_val: float = 1000) -> float:
    """
    Normalize momentum index to 0-1 range.
    
    Args:
        value: Momentum index
        min_val: Minimum expected value
        max_val: Maximum expected value
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    clamped = max(min_val, min(max_val, value))
    normalized = (clamped - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, normalized))


def normalize_volatility_score(value: float) -> float:
    """
    Normalize volatility score to 0-1 range.
    Lower volatility = more stable = better (inverted).
    
    Args:
        value: Volatility score
        
    Returns:
        Normalized value between 0 and 1 (inverted: higher = lower volatility)
    """
    if value is None:
        return 0.5  # Default to moderate
    
    # Assuming volatility_score is 0-1, invert it
    # Higher volatility score = lower normalized score
    return max(0.0, min(1.0, 1.0 - value))


def normalize_buy_pressure_ratio(value: float) -> float:
    """
    Normalize buy pressure ratio to 0-1 range.
    Already 0-1, just ensure it's valid.
    
    Args:
        value: Buy pressure ratio (0-1)
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    return max(0.0, min(1.0, value))


class MarketScorer:
    """Scores market dynamics based on price movement, volume, and trading activity."""
    
    def __init__(self):
        """Initialize market scorer."""
        pass
    
    def score(self, market_data: Dict[str, Any]) -> float:
        """
        Score market dynamics from market digest data.
        
        Args:
            market_data: MarketDigest data dictionary
            
        Returns:
            Normalized market dynamics score (0-1)
        """
        if not market_data or market_data.get("error"):
            logger.warning("Market data missing or has error")
            return 0.0
        
        try:
            # Extract key features
            price_change_1h = market_data.get("price_change_1h", 0.0) or 0.0
            price_change_6h = market_data.get("price_change_6h", 0.0) or 0.0
            price_change_24h = market_data.get("price_change_24h", 0.0) or 0.0
            buy_sell_ratio = market_data.get("buy_sell_ratio", 0.0) or 0.0
            volume_24h = market_data.get("volume_24h", 0.0) or 0.0
            momentum_index = market_data.get("momentum_index", 0.0) or 0.0
            volatility_score = market_data.get("volatility_score", 0.0) or 0.0
            buy_pressure_ratio = market_data.get("buy_pressure_ratio", 0.0) or 0.0
            
            # Normalize features
            price_change_1h_norm = normalize_price_change(price_change_1h)
            price_change_6h_norm = normalize_price_change(price_change_6h)
            price_change_24h_norm = normalize_price_change(price_change_24h)
            
            # Average price changes (weighted: recent changes matter more)
            avg_price_change = (
                price_change_1h_norm * 0.5 +
                price_change_6h_norm * 0.3 +
                price_change_24h_norm * 0.2
            )
            
            buy_sell_ratio_norm = normalize_buy_sell_ratio(buy_sell_ratio)
            volume_norm = normalize_volume(volume_24h)
            momentum_norm = normalize_momentum_index(momentum_index)
            volatility_norm = normalize_volatility_score(volatility_score)
            buy_pressure_norm = normalize_buy_pressure_ratio(buy_pressure_ratio)
            
            # Weighted combination (favor momentum and buy pressure)
            market_score = (
                avg_price_change * 0.25 +
                buy_sell_ratio_norm * 0.20 +
                volume_norm * 0.15 +
                momentum_norm * 0.20 +
                volatility_norm * 0.10 +
                buy_pressure_norm * 0.10
            )
            
            return max(0.0, min(1.0, market_score))
            
        except Exception as e:
            logger.error(f"Error scoring market data: {e}", exc_info=True)
            return 0.0
    
    def get_feature_breakdown(self, market_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Get normalized feature breakdown for debugging.
        
        Args:
            market_data: MarketDigest data dictionary
            
        Returns:
            Dictionary of normalized feature scores
        """
        if not market_data or market_data.get("error"):
            return {}
        
        try:
            price_change_1h = market_data.get("price_change_1h", 0.0) or 0.0
            price_change_6h = market_data.get("price_change_6h", 0.0) or 0.0
            price_change_24h = market_data.get("price_change_24h", 0.0) or 0.0
            buy_sell_ratio = market_data.get("buy_sell_ratio", 0.0) or 0.0
            volume_24h = market_data.get("volume_24h", 0.0) or 0.0
            momentum_index = market_data.get("momentum_index", 0.0) or 0.0
            volatility_score = market_data.get("volatility_score", 0.0) or 0.0
            buy_pressure_ratio = market_data.get("buy_pressure_ratio", 0.0) or 0.0
            
            return {
                "price_change_1h": normalize_price_change(price_change_1h),
                "price_change_6h": normalize_price_change(price_change_6h),
                "price_change_24h": normalize_price_change(price_change_24h),
                "buy_sell_ratio": normalize_buy_sell_ratio(buy_sell_ratio),
                "volume_24h": normalize_volume(volume_24h),
                "momentum_index": normalize_momentum_index(momentum_index),
                "volatility_score": normalize_volatility_score(volatility_score),
                "buy_pressure_ratio": normalize_buy_pressure_ratio(buy_pressure_ratio),
            }
        except Exception as e:
            logger.error(f"Error getting feature breakdown: {e}", exc_info=True)
            return {}

