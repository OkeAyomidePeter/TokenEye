# app/Digestion/digest.py

from typing import Any, Dict, List
import logging

from .meta_digest import MetaDigest
from .market_digest import MarketDigest
from .holder_digest import HolderDigest
from .liquidity_digest import LiquidityDigest
from .social_digest import SocialDigest
from .flag_digest import FlagDigest
from .derived_digest import DerivedDigest
from .utils import extract_token_address, validate_digest_structure

logger = logging.getLogger(__name__)


class TokenDigester:
    """
    Orchestrates all digest layers into a unified structure.
    Handles token-level and batch-level digestion safely.
    """

    def __init__(self):
        """Initialize all digest modules."""
        self.meta_digest = MetaDigest()
        self.market_digest = MarketDigest()
        self.holder_digest = HolderDigest()
        self.liquidity_digest = LiquidityDigest()
        self.social_digest = SocialDigest()
        self.flag_digest = FlagDigest()
        self.derived_digest = DerivedDigest()

    def digest_token(self, enriched_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single enriched token into a structured digest.

        Args:
            enriched_token: Complete enriched token data

        Returns:
            Structured digest dict ready for scoring or ML
        """
        address = extract_token_address(enriched_token)
        logger.debug(f"Digesting token {address}")

        try:
            # Run all digests individually
            meta = self.meta_digest.digest(enriched_token)
            market = self.market_digest.digest(enriched_token)
            holders = self.holder_digest.digest(enriched_token)
            liquidity = self.liquidity_digest.digest(enriched_token)
            socials = self.social_digest.digest(enriched_token)
            flags = self.flag_digest.digest(enriched_token)

            # Combine non-derived sections for derived calculations
            digest_parts = {
                "meta": meta,
                "market": market,
                "holders": holders,
                "liquidity": liquidity,
                "socials": socials,
                "flags": flags,
            }

            # Compute derived metrics
            derived = self.derived_digest.digest(enriched_token, digest_parts)

            # Final structure
            digest = {
                "address": address,
                "symbol": meta.get("symbol"),
                "chain": meta.get("chain", "solana"),
                "digest": {
                    "meta": meta,
                    "market": market,
                    "holders": holders,
                    "liquidity": liquidity,
                    "socials": socials,
                    "flags": flags,
                    "derived": derived,
                },
                # "raw": enriched_token, 
            }

            # Validate structure integrity
            if not validate_digest_structure(digest["digest"]):
                logger.warning(f"⚠️ Structure validation failed for token: {address}")

            logger.debug(f"✅ Successfully digested token {address}")
            return digest

        except Exception as e:
            logger.error(f"❌ Error digesting token {address}: {e}", exc_info=True)

            # Minimal fallback
            error_digest = {
                "address": address,
                "symbol": None,
                "chain": "solana",
                "digest": {
                    name: {"_error": str(e)}
                    for name in ["meta", "market", "holders", "liquidity", "socials", "flags", "derived"]
                },
                # "raw": enriched_token,
            }
            return error_digest

    def digest_batch(self, enriched_tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of enriched tokens sequentially.
        """
        if not enriched_tokens:
            return []

        logger.info(f"🚀 Starting digestion for {len(enriched_tokens)} tokens...")
        digested_tokens = []
        success_count = 0

        for i, token in enumerate(enriched_tokens):
            try:
                digested = self.digest_token(token)
                digested_tokens.append(digested)

                # Count successful tokens
                has_error = any(
                    "_error" in section
                    for section in digested.get("digest", {}).values()
                    if isinstance(section, dict)
                )

                if not has_error:
                    success_count += 1

            except Exception as e:
                address = extract_token_address(token)
                logger.error(f"Batch item {i} failed ({address}): {e}")
                digested_tokens.append({
                    "address": address,
                    "symbol": None,
                    "chain": "solana",
                    "digest": {
                        name: {"_error": f"Processing failed: {str(e)}"}
                        for name in ["meta", "market", "holders", "liquidity", "socials", "flags", "derived"]
                    },
                    # "raw": token,
                })

        logger.info(f"✅ Batch digestion done — {success_count}/{len(enriched_tokens)} succeeded")
        return digested_tokens

    def get_digest_summary(self, digest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract essential digest info for summaries, logs, or dashboards.
        """
        try:
            meta = digest.get("digest", {}).get("meta", {})
            market = digest.get("digest", {}).get("market", {})
            flags = digest.get("digest", {}).get("flags", {})
            holders = digest.get("digest", {}).get("holders", {})
            derived = digest.get("digest", {}).get("derived", {})

            return {
                "address": digest.get("address"),
                "symbol": meta.get("symbol"),
                "price_usd": market.get("price_usd"),
                "market_cap": market.get("market_cap"),
                "total_holders": holders.get("total_holders"),
                "trust_score": flags.get("trust_score"),
                "survivability_score": derived.get("survivability_score"),
                "pump_probability": derived.get("pump_probability"),
            }

        except Exception as e:
            logger.error(f"Summary extraction failed: {e}")
            return {"error": str(e)}
