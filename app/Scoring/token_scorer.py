# app/Scoring/token_scorer.py

from typing import Optional, Dict, Any, List
import json
import logging

from .market_scorer import MarketScorer
from .liquidity_scorer import LiquidityScorer
from .holder_scorer import HolderScorer
from .social_scorer import SocialScorer
from .flag_scorer import FlagScorer
from .derived_scorer import DerivedScorer

logger = logging.getLogger(__name__)


def classify_score(score: float) -> str:
    """
    Classify token score into category.
    
    Args:
        score: Final score (0-100)
        
    Returns:
        Classification string: "high potential", "moderate", or "low potential"
    """
    if score >= 80:
        return "high potential"
    elif score >= 50:
        return "moderate"
    else:
        return "low potential"


class TokenScorer:
    """
    Main token scoring engine that ranks tokens by profit potential.
    
    Combines multiple scoring dimensions with weighted averages:
    - market_dynamics: 0.35
    - liquidity_strength: 0.20
    - holder_distribution: 0.15
    - social_signal: 0.10
    - trust_and_safety: 0.10
    - pump_probability: 0.10
    """
    
    def __init__(
        self,
        market_weight: float = 0.35,
        liquidity_weight: float = 0.20,
        holder_weight: float = 0.15,
        social_weight: float = 0.10,
        trust_weight: float = 0.10,
        pump_weight: float = 0.10
    ):
        """
        Initialize token scorer with custom weights.
        
        Args:
            market_weight: Weight for market dynamics score (default: 0.35)
            liquidity_weight: Weight for liquidity strength score (default: 0.20)
            holder_weight: Weight for holder distribution score (default: 0.15)
            social_weight: Weight for social signal score (default: 0.10)
            trust_weight: Weight for trust and safety score (default: 0.10)
            pump_weight: Weight for pump probability score (default: 0.10)
        """
        # Normalize weights to sum to 1.0
        total_weight = (
            market_weight +
            liquidity_weight +
            holder_weight +
            social_weight +
            trust_weight +
            pump_weight
        )
        
        if total_weight > 0:
            self.market_weight = market_weight / total_weight
            self.liquidity_weight = liquidity_weight / total_weight
            self.holder_weight = holder_weight / total_weight
            self.social_weight = social_weight / total_weight
            self.trust_weight = trust_weight / total_weight
            self.pump_weight = pump_weight / total_weight
        else:
            # Default weights
            self.market_weight = 0.35
            self.liquidity_weight = 0.20
            self.holder_weight = 0.15
            self.social_weight = 0.10
            self.trust_weight = 0.10
            self.pump_weight = 0.10
        
        # Initialize individual scorers
        self.market_scorer = MarketScorer()
        self.liquidity_scorer = LiquidityScorer()
        self.holder_scorer = HolderScorer()
        self.social_scorer = SocialScorer()
        self.flag_scorer = FlagScorer()
        self.derived_scorer = DerivedScorer()
    
    def score_token(self, token_data: Dict[str, Any], include_breakdown: bool = False) -> Dict[str, Any]:
        """
        Score a single token from token data dictionary.
        
        Args:
            token_data: Token data dictionary (from TokenDigest or JSON)
            include_breakdown: Whether to include detailed feature breakdown
            
        Returns:
            Dictionary with:
                - address: Token address
                - symbol: Token symbol
                - final_score: Final score (0-100)
                - classification: "high potential", "moderate", or "low potential"
                - component_scores: Individual component scores (0-1)
                - feature_breakdown: (optional) Detailed feature breakdown
        """
        try:
            # Extract token info
            address = token_data.get("address")
            symbol = token_data.get("symbol")
            
            # Extract digest data
            digest = token_data.get("digest", {})
            if not digest:
                logger.warning(f"Token {address} has no digest data")
                return self._create_empty_result(address, symbol)
            
            # Extract individual sections
            market_data = digest.get("market", {})
            liquidity_data = digest.get("liquidity", {})
            holder_data = digest.get("holders", {})
            social_data = digest.get("socials", {})
            flag_data = digest.get("flags", {})
            derived_data = digest.get("derived", {})
            
            # Score each dimension
            market_score = self.market_scorer.score(market_data)
            liquidity_score = self.liquidity_scorer.score(liquidity_data, derived_data)
            holder_score = self.holder_scorer.score(holder_data, derived_data)
            social_score = self.social_scorer.score(social_data)
            trust_score = self.flag_scorer.score(flag_data)
            pump_score = self.derived_scorer.score(derived_data)
            
            # Calculate weighted final score
            final_score_raw = (
                market_score * self.market_weight +
                liquidity_score * self.liquidity_weight +
                holder_score * self.holder_weight +
                social_score * self.social_weight +
                trust_score * self.trust_weight +
                pump_score * self.pump_weight
            )
            
            # Convert to 0-100 scale
            final_score = final_score_raw * 100.0
            
            # Classify
            classification = classify_score(final_score)
            
            # Build result
            result = {
                "address": address,
                "symbol": symbol,
                "final_score": round(final_score, 2),
                "classification": classification,
                "component_scores": {
                    "market_dynamics": round(market_score * 100, 2),
                    "liquidity_strength": round(liquidity_score * 100, 2),
                    "holder_distribution": round(holder_score * 100, 2),
                    "social_signal": round(social_score * 100, 2),
                    "trust_and_safety": round(trust_score * 100, 2),
                    "pump_probability": round(pump_score * 100, 2),
                },
                "weights": {
                    "market_dynamics": self.market_weight,
                    "liquidity_strength": self.liquidity_weight,
                    "holder_distribution": self.holder_weight,
                    "social_signal": self.social_weight,
                    "trust_and_safety": self.trust_weight,
                    "pump_probability": self.pump_weight,
                }
            }
            
            # Add feature breakdown if requested
            if include_breakdown:
                result["feature_breakdown"] = {
                    "market": self.market_scorer.get_feature_breakdown(market_data),
                    "liquidity": self.liquidity_scorer.get_feature_breakdown(liquidity_data, derived_data),
                    "holder": self.holder_scorer.get_feature_breakdown(holder_data, derived_data),
                    "social": self.social_scorer.get_feature_breakdown(social_data),
                    "flag": self.flag_scorer.get_feature_breakdown(flag_data),
                    "derived": self.derived_scorer.get_feature_breakdown(derived_data),
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error scoring token {address}: {e}", exc_info=True)
            return self._create_empty_result(
                token_data.get("address"),
                token_data.get("symbol"),
                error=str(e)
            )
    
    def score_token_from_json(self, json_path: str, include_breakdown: bool = False) -> Dict[str, Any]:
        """
        Score a token from a JSON file.
        
        Args:
            json_path: Path to JSON file containing token data
            include_breakdown: Whether to include detailed feature breakdown
            
        Returns:
            Scoring result dictionary
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            # Handle nested structure (e.g., {"sample_token": {...}})
            if isinstance(data, dict) and len(data) == 1:
                token_key = list(data.keys())[0]
                token_data = data[token_key]
            else:
                token_data = data
            
            return self.score_token(token_data, include_breakdown)
            
        except Exception as e:
            logger.error(f"Error reading JSON file {json_path}: {e}", exc_info=True)
            return self._create_empty_result(None, None, error=str(e))
    
    def score_batch(self, tokens: List[Dict[str, Any]], include_breakdown: bool = False) -> List[Dict[str, Any]]:
        """
        Score multiple tokens and return sorted by final score.
        
        Args:
            tokens: List of token data dictionaries
            include_breakdown: Whether to include detailed feature breakdown
            
        Returns:
            List of scoring results, sorted by final_score (descending)
        """
        results = []
        
        for token in tokens:
            result = self.score_token(token, include_breakdown)
            results.append(result)
        
        # Sort by final score (descending)
        results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
        
        return results
    
    def _create_empty_result(self, address: Optional[str], symbol: Optional[str], error: Optional[str] = None) -> Dict[str, Any]:
        """Create an empty result dictionary for error cases."""
        return {
            "address": address,
            "symbol": symbol,
            "final_score": 0.0,
            "classification": "low potential",
            "component_scores": {
                "market_dynamics": 0.0,
                "liquidity_strength": 0.0,
                "holder_distribution": 0.0,
                "social_signal": 0.0,
                "trust_and_safety": 0.0,
                "pump_probability": 0.0,
            },
            "weights": {
                "market_dynamics": self.market_weight,
                "liquidity_strength": self.liquidity_weight,
                "holder_distribution": self.holder_weight,
                "social_signal": self.social_weight,
                "trust_and_safety": self.trust_weight,
                "pump_probability": self.pump_weight,
            },
            "error": error
        }

