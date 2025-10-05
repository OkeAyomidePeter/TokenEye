# app/DataModels/social.py

from typing import Optional
from pydantic import BaseModel, Field


class SocialDigest(BaseModel):
    """Social digest model for community presence and social media metrics."""
    
    # Social media presence
    has_twitter: bool = Field(False, description="Whether token has Twitter/X presence")
    twitter_url: Optional[str] = Field(None, description="Twitter/X URL")
    has_discord: bool = Field(False, description="Whether token has Discord presence")
    has_telegram: bool = Field(False, description="Whether token has Telegram presence")
    
    # Website and branding
    has_website: bool = Field(False, description="Whether token has official website")
    has_header_image: bool = Field(False, description="Whether token has header/logo image")
    
    # Community metrics
    social_presence_score: int = Field(0, description="Overall social presence score (0-5)")
    verified_community: bool = Field(False, description="Whether community is verified")
    
    # Error handling
    error: Optional[str] = Field(None, description="Error message if processing failed")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"
        validate_assignment = True
