# app/Scoring/holder_scorer.py

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def normalize_gini_coefficient(value: float) -> float:
    """
    Normalize Gini coefficient to 0-1 range.
    Lower Gini = more equal distribution = better (inverted).
    
    Args:
        value: Gini coefficient (0-1)
        
    Returns:
        Normalized value between 0 and 1 (inverted: higher = lower inequality)
    """
    if value is None:
        return 0.5  # Default to moderate
    
    # Invert: lower Gini = higher score
    return max(0.0, min(1.0, 1.0 - value))


def normalize_holder_concentration_score(value: float) -> float:
    """
    Normalize holder concentration score to 0-1 range.
    Lower concentration = more decentralized = better (inverted).
    
    Args:
        value: Holder concentration score (0-1)
        
    Returns:
        Normalized value between 0 and 1 (inverted: higher = lower concentration)
    """
    if value is None:
        return 0.5  # Default to moderate
    
    # Invert: lower concentration = higher score
    return max(0.0, min(1.0, 1.0 - value))


def normalize_decentralization_score(value: float) -> float:
    """
    Normalize decentralization score to 0-1 range.
    Already 0-1, just ensure it's valid.
    
    Args:
        value: Decentralization score (0-1)
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    return max(0.0, min(1.0, value))


class HolderScorer:
    """Scores holder distribution based on Gini coefficient, concentration, and decentralization."""
    
    def __init__(self):
        """Initialize holder scorer."""
        pass
    
    def score(self, holder_data: Dict[str, Any], derived_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Score holder distribution from holder digest data.
        
        Args:
            holder_data: HolderDigest data dictionary
            derived_data: Optional DerivedDigest data for decentralization_score
            
        Returns:
            Normalized holder distribution score (0-1)
        """
        if not holder_data or holder_data.get("error"):
            logger.warning("Holder data missing or has error")
            return 0.0
        
        try:
            # Extract key features from holder data
            gini_coefficient = holder_data.get("gini_coefficient", 0.0) or 0.0
            holder_concentration_score = holder_data.get("holder_concentration_score", 0.0) or 0.0
            
            # Try to get decentralization_score from derived data if available
            decentralization_score = None
            if derived_data and not derived_data.get("error"):
                decentralization_score = derived_data.get("decentralization_score")
            
            # Normalize features
            gini_norm = normalize_gini_coefficient(gini_coefficient)
            concentration_norm = normalize_holder_concentration_score(holder_concentration_score)
            
            # Use decentralization_score if available, otherwise use average of gini and concentration
            if decentralization_score is not None:
                decentralization_norm = normalize_decentralization_score(decentralization_score)
            else:
                # Fallback: average of inverted gini and concentration
                decentralization_norm = (gini_norm + concentration_norm) / 2.0
            
            # Weighted combination (favor decentralization)
            holder_score = (
                gini_norm * 0.30 +
                concentration_norm * 0.30 +
                decentralization_norm * 0.40
            )
            
            return max(0.0, min(1.0, holder_score))
            
        except Exception as e:
            logger.error(f"Error scoring holder data: {e}", exc_info=True)
            return 0.0
    
    def get_feature_breakdown(self, holder_data: Dict[str, Any], derived_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
        """
        Get normalized feature breakdown for debugging.
        
        Args:
            holder_data: HolderDigest data dictionary
            derived_data: Optional DerivedDigest data for decentralization_score
            
        Returns:
            Dictionary of normalized feature scores
        """
        if not holder_data or holder_data.get("error"):
            return {}
        
        try:
            gini_coefficient = holder_data.get("gini_coefficient", 0.0) or 0.0
            holder_concentration_score = holder_data.get("holder_concentration_score", 0.0) or 0.0
            
            decentralization_score = None
            if derived_data and not derived_data.get("error"):
                decentralization_score = derived_data.get("decentralization_score")
            
            breakdown = {
                "gini_coefficient": normalize_gini_coefficient(gini_coefficient),
                "holder_concentration_score": normalize_holder_concentration_score(holder_concentration_score),
            }
            
            if decentralization_score is not None:
                breakdown["decentralization_score"] = normalize_decentralization_score(decentralization_score)
            
            return breakdown
        except Exception as e:
            logger.error(f"Error getting feature breakdown: {e}", exc_info=True)
            return {}

