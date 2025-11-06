# app/Scoring/derived_scorer.py

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def normalize_pump_probability(value: float) -> float:
    """
    Normalize pump probability to 0-1 range.
    Already 0-1, just ensure it's valid.
    
    Args:
        value: Pump probability score (0-1)
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    return max(0.0, min(1.0, value))


def normalize_survivability_score(value: float) -> float:
    """
    Normalize survivability score to 0-1 range.
    Already 0-1, just ensure it's valid.
    
    Args:
        value: Survivability score (0-1)
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    return max(0.0, min(1.0, value))


def normalize_insider_manipulation_risk(value: float) -> float:
    """
    Normalize insider manipulation risk to 0-1 range.
    Lower risk = better (inverted).
    
    Args:
        value: Insider manipulation risk (0-1)
        
    Returns:
        Normalized value between 0 and 1 (inverted: higher = lower risk)
    """
    if value is None:
        return 0.5  # Default to moderate
    
    # Invert: lower risk = higher score
    return max(0.0, min(1.0, 1.0 - value))


class DerivedScorer:
    """Scores derived metrics including pump probability, survivability, and insider risk."""
    
    def __init__(self):
        """Initialize derived scorer."""
        pass
    
    def score(self, derived_data: Dict[str, Any]) -> float:
        """
        Score derived metrics from derived digest data.
        
        Args:
            derived_data: DerivedDigest data dictionary
            
        Returns:
            Normalized derived metrics score (0-1)
        """
        if not derived_data or derived_data.get("error"):
            logger.warning("Derived data missing or has error")
            return 0.0
        
        try:
            # Extract key features
            pump_probability = derived_data.get("pump_probability", 0.0) or 0.0
            survivability_score = derived_data.get("survivability_score", 0.0) or 0.0
            insider_manipulation_risk = derived_data.get("insider_manipulation_risk", 0.0) or 0.0
            
            # Normalize features
            pump_prob_norm = normalize_pump_probability(pump_probability)
            survivability_norm = normalize_survivability_score(survivability_score)
            insider_risk_norm = normalize_insider_manipulation_risk(insider_manipulation_risk)
            
            # Weighted combination (favor pump probability and survivability)
            derived_score = (
                pump_prob_norm * 0.50 +
                survivability_norm * 0.30 +
                insider_risk_norm * 0.20
            )
            
            return max(0.0, min(1.0, derived_score))
            
        except Exception as e:
            logger.error(f"Error scoring derived data: {e}", exc_info=True)
            return 0.0
    
    def get_feature_breakdown(self, derived_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Get normalized feature breakdown for debugging.
        
        Args:
            derived_data: DerivedDigest data dictionary
            
        Returns:
            Dictionary of normalized feature scores
        """
        if not derived_data or derived_data.get("error"):
            return {}
        
        try:
            pump_probability = derived_data.get("pump_probability", 0.0) or 0.0
            survivability_score = derived_data.get("survivability_score", 0.0) or 0.0
            insider_manipulation_risk = derived_data.get("insider_manipulation_risk", 0.0) or 0.0
            
            return {
                "pump_probability": normalize_pump_probability(pump_probability),
                "survivability_score": normalize_survivability_score(survivability_score),
                "insider_manipulation_risk": normalize_insider_manipulation_risk(insider_manipulation_risk),
            }
        except Exception as e:
            logger.error(f"Error getting feature breakdown: {e}", exc_info=True)
            return {}

