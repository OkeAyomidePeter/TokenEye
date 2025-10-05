# app/DataModels/meta.py

from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class LaunchpadInfo(BaseModel):
    """Launchpad information model."""
    name: Optional[str] = Field(None, description="Launchpad name")
    url: Optional[str] = Field(None, description="Launchpad URL")


class MetaDigest(BaseModel):
    """Metadata digest model for basic token information and creation data."""
    
    # Basic metadata
    address: Optional[str] = Field(None, description="Token contract address")
    name: Optional[str] = Field(None, description="Token name")
    symbol: Optional[str] = Field(None, description="Token symbol")
    chain: str = Field("solana", description="Blockchain network")
    
    # Authorities & creator
    creator: Optional[str] = Field(None, description="Token creator address")
    mint_authority: Optional[str] = Field(None, description="Mint authority address")
    freeze_authority: Optional[str] = Field(None, description="Freeze authority address")
    
    # Creation time
    creation_time: Optional[Any] = Field(None, description="Token creation timestamp")
    token_age_days: Optional[float] = Field(None, description="Token age in days")
    token_age_hours: Optional[float] = Field(None, description="Token age in hours")
    
    # Technical details
    decimals: Optional[int] = Field(None, description="Token decimals")
    
    # Launchpad info
    launchpad: LaunchpadInfo = Field(default_factory=LaunchpadInfo, description="Launchpad information")
    
    # Media & metadata
    image_url: Optional[str] = Field(None, description="Token image URL")
    metadata_uri: Optional[str] = Field(None, description="Token metadata URI")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"  # Allow additional fields for flexibility
        validate_assignment = True
