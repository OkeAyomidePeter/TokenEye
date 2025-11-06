# app/Scoring/liquidity_scorer.py

from typing import Optional, Dict, Any
import logging
import math

logger = logging.getLogger(__name__)


def normalize_liquidity(value: float, min_val: float = 1000, max_val: float = 500000) -> float:
    """
    Normalize liquidity amount to 0-1 range using log scale.
    
    Args:
        value: Total liquidity in USD
        min_val: Minimum expected value
        max_val: Maximum expected value
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None or value <= 0:
        return 0.0
    
    # Use log scale for liquidity
    if value < min_val:
        return 0.0
    if value > max_val:
        return 1.0
    
    log_val = math.log10(value)
    log_min = math.log10(min_val)
    log_max = math.log10(max_val)
    
    normalized = (log_val - log_min) / (log_max - log_min)
    return max(0.0, min(1.0, normalized))


def normalize_locked_liquidity_ratio(value: float) -> float:
    """
    Normalize locked liquidity ratio to 0-1 range.
    Already 0-1, just ensure it's valid.
    
    Args:
        value: Locked liquidity ratio (0-1)
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    return max(0.0, min(1.0, value))


def normalize_liquidity_to_fdv_ratio(value: float, min_val: float = 0.1, max_val: float = 1.0) -> float:
    """
    Normalize liquidity to FDV ratio to 0-1 range.
    Higher ratio = more liquidity relative to market cap = better.
    
    Args:
        value: Liquidity to FDV ratio
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


class LiquidityScorer:
    """Scores liquidity strength based on total liquidity, locked ratio, and FDV ratio."""
    
    def __init__(self):
        """Initialize liquidity scorer."""
        pass
    
    def score(self, liquidity_data: Dict[str, Any], derived_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Score liquidity strength from liquidity digest data.
        
        Args:
            liquidity_data: LiquidityDigest data dictionary
            derived_data: Optional DerivedDigest data for liquidity_to_fdv_ratio
            
        Returns:
            Normalized liquidity strength score (0-1)
        """
        if not liquidity_data or liquidity_data.get("error"):
            logger.warning("Liquidity data missing or has error")
            return 0.0
        
        try:
            # Extract key features
            total_liquidity_usd = liquidity_data.get("total_liquidity_usd", 0.0) or 0.0
            locked_liquidity_ratio = liquidity_data.get("locked_liquidity_ratio", 0.0) or 0.0
            
            # Get liquidity_to_fdv_ratio from derived data if available
            liquidity_to_fdv_ratio = None
            if derived_data and not derived_data.get("error"):
                liquidity_to_fdv_ratio = derived_data.get("liquidity_to_fdv_ratio")
            
            if liquidity_to_fdv_ratio is None:
                liquidity_to_fdv_ratio = 0.0
            
            # Normalize features
            liquidity_norm = normalize_liquidity(total_liquidity_usd)
            locked_ratio_norm = normalize_locked_liquidity_ratio(locked_liquidity_ratio)
            fdv_ratio_norm = normalize_liquidity_to_fdv_ratio(liquidity_to_fdv_ratio)
            
            # Weighted combination (favor locked liquidity and FDV ratio)
            liquidity_score = (
                liquidity_norm * 0.30 +
                locked_ratio_norm * 0.40 +
                fdv_ratio_norm * 0.30
            )
            
            return max(0.0, min(1.0, liquidity_score))
            
        except Exception as e:
            logger.error(f"Error scoring liquidity data: {e}", exc_info=True)
            return 0.0
    
    def get_feature_breakdown(self, liquidity_data: Dict[str, Any], derived_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Get normalized feature breakdown for debugging.
        
        Args:
            liquidity_data: LiquidityDigest data dictionary
            derived_data: Optional DerivedDigest data for liquidity_to_fdv_ratio
            
        Returns:
            Dictionary of normalized feature scores
        """
        if not liquidity_data or liquidity_data.get("error"):
            return {}
        
        try:
            total_liquidity_usd = liquidity_data.get("total_liquidity_usd", 0.0) or 0.0
            locked_liquidity_ratio = liquidity_data.get("locked_liquidity_ratio", 0.0) or 0.0
            
            liquidity_to_fdv_ratio = None
            if derived_data and not derived_data.get("error"):
                liquidity_to_fdv_ratio = derived_data.get("liquidity_to_fdv_ratio")
            
            if liquidity_to_fdv_ratio is None:
                liquidity_to_fdv_ratio = 0.0
            
            return {
                "total_liquidity_usd": normalize_liquidity(total_liquidity_usd),
                "locked_liquidity_ratio": normalize_locked_liquidity_ratio(locked_liquidity_ratio),
                "liquidity_to_fdv_ratio": normalize_liquidity_to_fdv_ratio(liquidity_to_fdv_ratio),
            }
        except Exception as e:
            logger.error(f"Error getting feature breakdown: {e}", exc_info=True)
            return {}

