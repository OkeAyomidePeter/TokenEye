# app/Schemas/token.py

from typing import Optional, Dict
from pydantic import BaseModel, HttpUrl


class TokenData(BaseModel):
    url: str
    chainId: str
    tokenAddress: str

    # Optional metadata
    icon: Optional[str] = None
    header: Optional[str] = None
    openGraph: Optional[str] = None
    description: Optional[str] = None

    # Normalized links (always a dict, keys may be None if missing)
    links: Dict[str, Optional[str]] = {
        "website": None,
        "twitter": None,
        "telegram": None,
        "discord": None,
        "medium": None,
    }


class DexscreenerResponse(BaseModel):
    status: str
    count: int
    data: list[TokenData]
