# app/Digestion/derived_digest.py

from typing import Any, Dict


class DerivedDigest:
    """Compute cross-domain synthetic features for AI training."""

    @staticmethod
    def digest(enriched_token: Dict[str, Any], digest_parts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute cross-domain synthetic features from all digest modules.
        """
        try:
            meta = digest_parts.get("meta", {})
            market = digest_parts.get("market", {})
            holders = digest_parts.get("holders", {})
            liquidity = digest_parts.get("liquidity", {})
            socials = digest_parts.get("socials", {})
            flags = digest_parts.get("flags", {})

            fdv = market.get("fdv", 0) or 0
            total_liquidity = liquidity.get("total_liquidity_usd", 0) or 0
            total_holders = holders.get("total_holders", 0) or 0
            tx_24h = market.get("tx_24h", 0) or 0

            liquidity_ratio = liquidity.get("liquidity_ratio", 0) or 0
            volatility_score = market.get("volatility_score", 0) or 0
            top10_share = holders.get("top10_share", 0) or 0
            has_mint_authority = bool(flags.get("has_mint_authority", False))

            # Derived cross-domain ratios
            liquidity_to_fdv_ratio = total_liquidity / (fdv + 1e-9)
            holder_to_liquidity_ratio = total_holders / (total_liquidity + 1e-9)
            activity_to_fdv_ratio = tx_24h / (fdv + 1e-9)
            stability_index = liquidity_ratio * (1 - volatility_score)
            decentralization_score = (1 - top10_share / 100) * (1 - float(has_mint_authority))

            # Composite synthetic scores
            survivability_score = DerivedDigest._calculate_survivability_score(
                meta, market, holders, liquidity, socials, flags
            )
            pump_probability = DerivedDigest._calculate_pump_probability(
                meta, market, holders, liquidity, socials, flags
            )
            liquidity_retention = DerivedDigest._calculate_liquidity_retention(
                market, liquidity, flags
            )
            insider_manipulation_risk = DerivedDigest._calculate_insider_risk(
                holders, flags
            )

            return {
                "liquidity_to_fdv_ratio": liquidity_to_fdv_ratio,
                "holder_to_liquidity_ratio": holder_to_liquidity_ratio,
                "activity_to_fdv_ratio": activity_to_fdv_ratio,
                "stability_index": stability_index,
                "decentralization_score": decentralization_score,
                "survivability_score": survivability_score,
                "pump_probability": pump_probability,
                "liquidity_retention": liquidity_retention,
                "insider_manipulation_risk": insider_manipulation_risk
            }

        except Exception as e:
            return {
                "liquidity_to_fdv_ratio": 0,
                "holder_to_liquidity_ratio": 0,
                "activity_to_fdv_ratio": 0,
                "stability_index": 0,
                "decentralization_score": 0,
                "survivability_score": 0,
                "pump_probability": 0,
                "liquidity_retention": 0,
                "insider_manipulation_risk": 0,
                "_error": str(e)
            }

    # ---------- PRIVATE COMPUTATIONS ---------- #

    @staticmethod
    def _calculate_survivability_score(meta, market, holders, liquidity, socials, flags):
        """Composite survivability likelihood based on multiple signals."""
        try:
            base_score = flags.get("trust_score", 0) or 0
            token_age = meta.get("token_age_days", 0) or 0
            holder_concentration = holders.get("holder_concentration_score", 0) or 0
            liquidity_ratio = liquidity.get("liquidity_ratio", 0) or 0
            social_score = socials.get("social_presence_score", 0) or 0

            age_factor = min(1.0, token_age / 30.0)
            distribution_factor = 1 - holder_concentration
            social_factor = min(1.0, social_score / 5.0)

            survivability = (
                base_score * 0.3 +
                age_factor * 0.2 +
                distribution_factor * 0.2 +
                liquidity_ratio * 0.2 +
                social_factor * 0.1
            )

            return max(0, min(1, survivability))
        except Exception:
            return 0.0

    @staticmethod
    def _calculate_pump_probability(meta, market, holders, liquidity, socials, flags):
        """Estimate pump potential using market and social momentum."""
        try:
            momentum = market.get("momentum_index", 0) or 0
            volume = market.get("volume_24h", 0) or 0
            buy_pressure = market.get("buy_pressure_ratio", 0) or 0
            social_score = socials.get("social_presence_score", 0) or 0
            liquidity_depth = liquidity.get("total_liquidity_usd", 0) or 0

            momentum_factor = min(1.0, max(0, momentum) / 100.0)
            volume_factor = min(1.0, volume / 100000.0)
            social_factor = min(1.0, social_score / 5.0)
            depth_factor = min(1.0, liquidity_depth / 50000.0)

            pump_prob = (
                momentum_factor * 0.3 +
                volume_factor * 0.2 +
                buy_pressure * 0.2 +
                social_factor * 0.2 +
                depth_factor * 0.1
            )

            return max(0, min(1, pump_prob))
        except Exception:
            return 0.0

    @staticmethod
    def _calculate_liquidity_retention(market, liquidity, flags):
        """Estimate how much liquidity is likely to remain stable."""
        try:
            locked_ratio = liquidity.get("locked_liquidity_ratio", 0) or 0
            volatility = market.get("volatility_score", 0) or 0
            trust = flags.get("trust_score", 0) or 0
            multi_pool = bool(liquidity.get("multi_pool_presence", False))

            volatility_factor = max(0, 1 - volatility)
            pool_factor = 1.0 if multi_pool else 0.5

            retention = (
                locked_ratio * 0.4 +
                volatility_factor * 0.3 +
                trust * 0.2 +
                pool_factor * 0.1
            )

            return max(0, min(1, retention))
        except Exception:
            return 0.0

    @staticmethod
    def _calculate_insider_risk(holders, flags):
        """Quantify insider manipulation risk."""
        try:
            top5_share = holders.get("top5_share", 0) or 0
            insider_score = holders.get("insider_network_score", 0) or 0
            creator_share = holders.get("creator_share", 0) or 0

            has_mint_auth = bool(flags.get("has_mint_authority", False))
            has_freeze_auth = bool(flags.get("has_freeze_authority", False))

            concentration_risk = min(1.0, top5_share / 100.0)
            authority_risk = float(has_mint_auth) + (float(has_freeze_auth) * 0.5)
            creator_risk = min(1.0, creator_share / 50.0)

            insider_risk = (
                concentration_risk * 0.4 +
                insider_score * 0.3 +
                authority_risk * 0.2 +
                creator_risk * 0.1
            )

            return max(0, min(1, insider_risk))
        except Exception:
            return 0.0
