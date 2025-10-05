# app/DataModels/derived.py

from typing import Optional
from pydantic import BaseModel, Field


class DerivedDigest(BaseModel):
    """Derived digest model for cross-domain synthetic features and AI metrics."""
    
    # Cross-domain ratios
    liquidity_to_fdv_ratio: float = Field(0.0, description="Liquidity to FDV ratio")
    holder_to_liquidity_ratio: float = Field(0.0, description="Holder count to liquidity ratio")
    activity_to_fdv_ratio: float = Field(0.0, description="Activity to FDV ratio")
    
    # Stability and decentralization
    stability_index: float = Field(0.0, description="Token stability index (0-1)")
    decentralization_score: float = Field(0.0, description="Token decentralization score (0-1)")
    
    # AI prediction scores
    survivability_score: float = Field(0.0, description="Token survivability score (0-1)")
    pump_probability: float = Field(0.0, description="Pump probability score (0-1)")
    liquidity_retention: float = Field(0.0, description="Liquidity retention score (0-1)")
    insider_manipulation_risk: float = Field(0.0, description="Insider manipulation risk (0-1)")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True
