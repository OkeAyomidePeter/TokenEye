# app/Scoring/flag_scorer.py

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def normalize_trust_score(value: float) -> float:
    """
    Normalize trust score to 0-1 range.
    Already 0-1, just ensure it's valid.
    
    Args:
        value: Trust score (0-1)
        
    Returns:
        Normalized value between 0 and 1
    """
    if value is None:
        return 0.0
    
    return max(0.0, min(1.0, value))


class FlagScorer:
    """Scores trust and safety based on flags, trust score, and rug likelihood."""
    
    def __init__(self):
        """Initialize flag scorer."""
        pass
    
    def score(self, flag_data: Dict[str, Any]) -> float:
        """
        Score trust and safety from flag digest data.
        
        Args:
            flag_data: FlagDigest data dictionary
            
        Returns:
            Normalized trust and safety score (0-1)
        """
        if not flag_data or flag_data.get("error"):
            logger.warning("Flag data missing or has error")
            return 0.0
        
        try:
            # Extract key features
            rugged = flag_data.get("rugged", False)
            rug_likelihood_flag = flag_data.get("rug_likelihood_flag", False)
            trust_score = flag_data.get("trust_score", 0.0) or 0.0
            has_freeze_authority = flag_data.get("has_freeze_authority", False)
            has_mint_authority = flag_data.get("has_mint_authority", False)
            verified_on_chain = flag_data.get("verified_on_chain", False)
            
            # Immediate disqualifiers
            if rugged:
                return 0.0
            
            # Heavy penalty for rug likelihood
            if rug_likelihood_flag:
                return 0.1  # Very low score but not zero
            
            # Normalize trust score
            trust_norm = normalize_trust_score(trust_score)
            
            # Penalties for risky flags
            penalty = 0.0
            if has_freeze_authority:
                penalty += 0.2
            if has_mint_authority:
                penalty += 0.2
            
            # Bonus for verification
            bonus = 0.0
            if verified_on_chain:
                bonus += 0.1
            
            # Combine trust score with penalties and bonuses
            safety_score = trust_norm * (1.0 - penalty) + bonus
            
            return max(0.0, min(1.0, safety_score))
            
        except Exception as e:
            logger.error(f"Error scoring flag data: {e}", exc_info=True)
            return 0.0
    
    def get_feature_breakdown(self, flag_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Get normalized feature breakdown for debugging.
        
        Args:
            flag_data: FlagDigest data dictionary
            
        Returns:
            Dictionary of normalized feature scores
        """
        if not flag_data or flag_data.get("error"):
            return {}
        
        try:
            trust_score = flag_data.get("trust_score", 0.0) or 0.0
            
            return {
                "trust_score": normalize_trust_score(trust_score),
                "rugged": flag_data.get("rugged", False),
                "rug_likelihood_flag": flag_data.get("rug_likelihood_flag", False),
                "has_freeze_authority": flag_data.get("has_freeze_authority", False),
                "has_mint_authority": flag_data.get("has_mint_authority", False),
                "verified_on_chain": flag_data.get("verified_on_chain", False),
            }
        except Exception as e:
            logger.error(f"Error getting feature breakdown: {e}", exc_info=True)
            return {}

