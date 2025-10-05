# app/DataModels/flag.py

from typing import Optional, List
from pydantic import BaseModel, Field


class FlagDigest(BaseModel):
    """Flag digest model for security and risk indicators."""
    
    # Rug status
    rugged: bool = Field(False, description="Whether token is rugged")
    
    # Authority flags
    has_freeze_authority: bool = Field(False, description="Whether token has freeze authority")
    has_mint_authority: bool = Field(False, description="Whether token has mint authority")
    
    # Risk assessment
    risk_flags: List[str] = Field(default_factory=list, description="List of identified risk flags")
    verified_on_chain: bool = Field(False, description="Whether token is verified on-chain")
    
    # Risk scores
    revocation_risk_score: float = Field(0.0, description="Token revocation risk score (0-1)")
    rug_likelihood_flag: bool = Field(False, description="Whether rug pull is likely")
    trust_score: float = Field(0.0, description="Overall trust score (0-1)")
    
    # Verification status
    has_verified_creator: bool = Field(False, description="Whether creator is verified")
    has_kyc: bool = Field(False, description="Whether project has KYC verification")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True
