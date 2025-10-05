# app/DataModels/liquidity.py

from typing import Optional
from pydantic import BaseModel, Field


class LiquidityDigest(BaseModel):
    """Liquidity digest model for pool and LP-related data."""
    
    # Liquidity amounts
    total_liquidity_usd: float = Field(0.0, description="Total liquidity in USD")
    stable_liquidity_usd: float = Field(0.0, description="Stable coin liquidity in USD")
    lp_locked_usd: float = Field(0.0, description="Locked LP tokens value in USD")
    
    # Liquidity ratios
    lp_locked_pct: float = Field(0.0, description="Percentage of LP tokens locked")
    liquidity_ratio: float = Field(0.0, description="Stable to total liquidity ratio")
    locked_liquidity_ratio: float = Field(0.0, description="Locked liquidity ratio")
    
    # Pool information
    pool_count: int = Field(0, description="Number of liquidity pools")
    multi_pool_presence: bool = Field(False, description="Whether token exists in multiple pools")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True
