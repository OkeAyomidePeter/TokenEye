# app/Digestion/meta_digest.py

from typing import Any, Dict
from datetime import datetime, timezone


class MetaDigest:
    """Extract basic token information and creation metadata."""

    @staticmethod
    def digest(enriched_token: Dict[str, Any]) -> Dict[str, Any]:
        try:
            base = enriched_token.get("base_token", {}) or {}
            rugcheck = enriched_token.get("rugcheck", {}) or {}
            rpc_data = enriched_token.get("rpc_data", {}) or {}
            token_info = rugcheck.get("token", {}) or {}
            token_meta = rugcheck.get("tokenMeta", {}) or {}
            markets = rugcheck.get("markets", []) or []

            # --- Basic metadata ---
            address = base.get("address")
            name = base.get("name")
            symbol = base.get("symbol")
            chain = enriched_token.get("chain_id", "solana")

            # --- Authorities & creator ---
            creator = rugcheck.get("creator")
            mint_authority = token_info.get("mintAuthority")
            freeze_authority = token_info.get("freezeAuthority")

            # --- Creation time ---
            creation_time_str = enriched_token.get("pair_created_at")
            creation_time = None
            token_age_days = None
            token_age_hours = None

            if creation_time_str:
                try:
                    # Handle both string and datetime inputs
                    if isinstance(creation_time_str, datetime):
                        creation_time = creation_time_str
                        # Handle timezone - if naive (no timezone), assume it's local time and convert to UTC
                        if creation_time.tzinfo is None:
                            # Assume naive datetime is in local timezone, convert to UTC
                            import datetime as dt
                            local_tz = dt.datetime.now().astimezone().tzinfo
                            creation_time = creation_time.replace(tzinfo=local_tz).astimezone(timezone.utc)
                        else:
                            # Convert to UTC for consistent calculation
                            creation_time = creation_time.astimezone(timezone.utc)
                    else:
                        # Handle string input
                        parsed_str = str(creation_time_str).strip()
                        
                        # Handle different time formats
                        if parsed_str.endswith("Z"):
                            # ISO format with Z suffix
                            parsed_str = parsed_str.replace("Z", "+00:00")
                            creation_time = datetime.fromisoformat(parsed_str)
                        elif "+" in parsed_str or (parsed_str.count("-") > 2 and "T" in parsed_str):
                            # ISO format with timezone offset
                            creation_time = datetime.fromisoformat(parsed_str)
                        else:
                            # Format like "2025-10-05T18:10:11" - no timezone
                            creation_time = datetime.fromisoformat(parsed_str)
                            # Assume UTC if no timezone specified
                            creation_time = creation_time.replace(tzinfo=timezone.utc)

                    # Calculate age
                    now = datetime.now(timezone.utc)
                    delta = now - creation_time

                    token_age_days = round(delta.total_seconds() / 86400, 3)
                    token_age_hours = round(delta.total_seconds() / 3600, 3)
                    

                except Exception as e:
                    # If parsing fails, set age to None but keep original string
                    token_age_days = None
                    token_age_hours = None

            # --- Launchpad info (if any) ---
            launchpad = rugcheck.get("launchpad", {}) or {}
            launchpad_name = launchpad.get("name")
            launchpad_url = launchpad.get("url")

            # --- Image and metadata URIs ---
            image_url = (
                token_meta.get("image")
                or rugcheck.get("fileMeta", {}).get("image")
                or enriched_token.get("info", {}).get("image")
            )
            metadata_uri = token_meta.get("uri")

            # --- Decimals ---
            decimals = (
                token_info.get("decimals")
                or rpc_data.get("data", {}).get("parsed", {}).get("info", {}).get("decimals")
            )

            return {
                "address": address,
                "name": name,
                "symbol": symbol,
                "chain": chain,
                "creator": creator,
                "mint_authority": mint_authority,
                "freeze_authority": freeze_authority,
                "creation_time": creation_time_str,
                "token_age_days": token_age_days,
                "token_age_hours": token_age_hours,
                "decimals": decimals,
                "launchpad": {
                    "name": launchpad_name,
                    "url": launchpad_url,
                },
                "image_url": image_url,
                "metadata_uri": metadata_uri,
            }

        except Exception as e:
            return {
                "address": None,
                "name": None,
                "symbol": None,
                "chain": "solana",
                "creator": None,
                "mint_authority": None,
                "freeze_authority": None,
                "creation_time": None,
                "token_age_days": None,
                "token_age_hours": None,
                "decimals": None,
                "launchpad": {"name": None, "url": None},
                "image_url": None,
                "metadata_uri": None,
                "_error": str(e),
            }
