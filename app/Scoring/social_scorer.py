# app/Scoring/social_scorer.py

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def normalize_social_presence_score(value: int, max_val: int = 5) -> float:
    """
    Normalize social presence score to 0-1 range.
    
    Args:
        value: Social presence score (0-5)
        max_val: Maximum expected value
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    normalized = float(value) / float(max_val)
    return max(0.0, min(1.0, normalized))


class SocialScorer:
    """Scores social signal based on social presence and community engagement."""
    
    def __init__(self):
        """Initialize social scorer."""
        pass
    
    def score(self, social_data: Dict[str, Any]) -> float:
        """
        Score social signal from social digest data.
        
        Args:
            social_data: SocialDigest data dictionary
            
        Returns:
            Normalized social signal score (0-1)
        """
        if not social_data or social_data.get("error"):
            logger.warning("Social data missing or has error")
            return 0.0
        
        try:
            # Extract key features
            social_presence_score = social_data.get("social_presence_score", 0) or 0
            
            # Normalize features
            presence_norm = normalize_social_presence_score(social_presence_score)
            
            # Social score is primarily based on presence
            # Could add more features like follower count, engagement rate, etc.
            social_score = presence_norm
            
            return max(0.0, min(1.0, social_score))
            
        except Exception as e:
            logger.error(f"Error scoring social data: {e}", exc_info=True)
            return 0.0
    
    def get_feature_breakdown(self, social_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Get normalized feature breakdown for debugging.
        
        Args:
            social_data: SocialDigest data dictionary
            
        Returns:
            Dictionary of normalized feature scores
        """
        if not social_data or social_data.get("error"):
            return {}
        
        try:
            social_presence_score = social_data.get("social_presence_score", 0) or 0
            
            return {
                "social_presence_score": normalize_social_presence_score(social_presence_score),
            }
        except Exception as e:
            logger.error(f"Error getting feature breakdown: {e}", exc_info=True)
            return {}

