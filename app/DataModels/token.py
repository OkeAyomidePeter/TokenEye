# app/DataModels/token.py

from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

from .meta import MetaDigest
from .market import MarketDigest
from .holder import HolderDigest
from .liquidity import LiquidityDigest
from .social import SocialDigest
from .flag import FlagDigest
from .derived import DerivedDigest


class DigestData(BaseModel):
    """Combined digest data structure."""
    
    meta: MetaDigest = Field(..., description="Metadata digest")
    market: MarketDigest = Field(..., description="Market digest")
    holders: HolderDigest = Field(..., description="Holder digest")
    liquidity: LiquidityDigest = Field(..., description="Liquidity digest")
    socials: SocialDigest = Field(..., description="Social digest")
    flags: FlagDigest = Field(..., description="Flag digest")
    derived: DerivedDigest = Field(..., description="Derived digest")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True


class TokenDigest(BaseModel):
    """Main token digest model that validates and unifies all digest data."""
    
    # Basic identification
    address: Optional[str] = Field(None, description="Token contract address")
    symbol: Optional[str] = Field(None, description="Token symbol")
    chain: str = Field("solana", description="Blockchain network")
    
    # Digest data structure
    digest: DigestData = Field(..., description="Complete digest data")
    
    # Raw data (optional, for debugging/retraining)
    raw: Optional[Dict[str, Any]] = Field(None, description="Raw enriched token data")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True
        
    @classmethod
    def from_digest_dict(cls, digest_dict: Dict[str, Any]) -> "TokenDigest":
        """
        Create TokenDigest from raw digest dictionary.
        
        Args:
            digest_dict: Raw digest dictionary from TokenDigester
            
        Returns:
            Validated TokenDigest instance
        """
        try:
            # Extract basic info
            address = digest_dict.get("address")
            symbol = digest_dict.get("symbol")
            chain = digest_dict.get("chain", "solana")
            raw = digest_dict.get("raw")
            
            # Extract digest sections
            digest_data = digest_dict.get("digest", {})
            
            return cls(
                address=address,
                symbol=symbol,
                chain=chain,
                digest=DigestData(**digest_data),
                raw=raw
            )
        except Exception as e:
            # If validation fails, create a minimal valid structure
            return cls(
                address=address,
                symbol=symbol,
                chain=chain,
                digest=DigestData(
                    meta=MetaDigest(error=f"Validation failed: {str(e)}"),
                    market=MarketDigest(error=f"Validation failed: {str(e)}"),
                    holders=HolderDigest(error=f"Validation failed: {str(e)}"),
                    liquidity=LiquidityDigest(error=f"Validation failed: {str(e)}"),
                    socials=SocialDigest(error=f"Validation failed: {str(e)}"),
                    flags=FlagDigest(error=f"Validation failed: {str(e)}"),
                    derived=DerivedDigest(error=f"Validation failed: {str(e)}")
                ),
                raw=raw
            )
