# app/DataModels/market.py

from typing import Optional
from pydantic import BaseModel, Field


class MarketDigest(BaseModel):
    """Market digest model for price and trading metrics."""
    
    # Price data
    price_usd: Optional[float] = Field(None, description="Current price in USD")
    fdv: Optional[float] = Field(None, description="Fully diluted valuation in USD")
    market_cap: Optional[float] = Field(None, description="Market capitalization in USD")
    
    # Trading activity
    tx_24h: int = Field(0, description="24-hour transaction count")
    volume_24h: float = Field(0.0, description="24-hour trading volume in USD")
    
    # Price changes
    price_change_1h: float = Field(0.0, description="1-hour price change percentage")
    price_change_6h: float = Field(0.0, description="6-hour price change percentage")
    price_change_24h: float = Field(0.0, description="24-hour price change percentage")
    
    # Transaction breakdown
    buys_m5: float = Field(0.0, description="5 minutes buy transactions")
    sells_m5: float = Field(0.0, description="5 minutes sell transactions")
    buys_1h: float = Field(0.0, description="1-hour buy transactions")
    sells_1h: float = Field(0.0, description="1-hour sell transactions")
    buys_6h: float = Field(0.0, description="6-hour buy transactions")
    sells_6h: float = Field(0.0, description="6-hour sell transactions")
    buys_24h: float = Field(0.0, description="24-hour buy transactions")
    sells_24h: float = Field(0.0, description="24-hour sell transactions")
    
    # Market dynamics
    buy_sell_ratio: float = Field(0.0, description="Buy to sell ratio")
    velocity_score: float = Field(0.0, description="Transaction velocity score")
    momentum_index: float = Field(0.0, description="Price momentum index")
    volatility_score: float = Field(0.0, description="Price volatility score")
    buy_pressure_ratio: float = Field(0.0, description="Buy pressure ratio")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True
