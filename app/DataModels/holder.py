# app/DataModels/holder.py

from typing import Optional
from pydantic import BaseModel, Field


class HolderDigest(BaseModel):
    """Holder digest model for token distribution and holder analysis."""
    
    # Basic holder metrics
    total_holders: int = Field(0, description="Total number of token holders")
    
    # Holder concentration
    top10_share: float = Field(0.0, description="Top 10 holders share percentage")
    top5_share: float = Field(0.0, description="Top 5 holders share percentage")
    creator_share: float = Field(0.0, description="Creator's token share percentage")
    
    # Insider detection
    insider_count: int = Field(0, description="Number of detected insider networks")
    insider_network_score: float = Field(0.0, description="Insider network risk score")
    
    # Distribution analysis
    gini_coefficient: float = Field(0.0, description="Gini coefficient for holder distribution")
    holder_concentration_score: float = Field(0.0, description="Holder concentration risk score")
    is_risky_holder_distribution: bool = Field(False, description="Whether holder distribution is risky")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True
