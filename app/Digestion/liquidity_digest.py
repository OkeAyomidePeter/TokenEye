# app/Digestion/liquidity_digest.py

from typing import Any, Dict


class LiquidityDigest:
    """Extract liquidity pool & LP-related data safely and consistently."""

    @staticmethod
    def _to_float(v: Any, default: float = 0.0) -> float:
        try:
            if v is None:
                return default
            if isinstance(v, (int, float)):
                return float(v)
            if isinstance(v, str):
                return float(v.replace(",", "").strip()) if v.strip() != "" else default
            if isinstance(v, dict):
                for key in ("lpLockedUSD", "lpLockedUsd", "lpLocked", "lp_locked_usd", "lpLockedUSD"):
                    if key in v:
                        try:
                            return float(v[key])
                        except Exception:
                            continue
            return default
        except Exception:
            return default

    @staticmethod
    def digest(enriched_token: Dict[str, Any]) -> Dict[str, Any]:
        try:
            rugcheck = enriched_token.get("rugcheck") or {}

            total_liquidity_usd = LiquidityDigest._to_float(rugcheck.get("totalMarketLiquidity") or rugcheck.get("total_market_liquidity") or 0)
            stable_liquidity_usd = LiquidityDigest._to_float(rugcheck.get("totalStableLiquidity") or rugcheck.get("total_stable_liquidity") or 0)

            markets = rugcheck.get("markets") or []
            pool_count = len(markets) if isinstance(markets, list) else 0

            lp_locked_usd = 0.0
            lp_locked_pct = 0.0

            if isinstance(markets, list) and markets:
                total_locked_usd = 0.0
                total_locked_pct = 0.0
                counted = 0
                for market in markets:
                    if not isinstance(market, dict):
                        continue
                    lp = market.get("lp") or {}
                    # many upstreams use 'lpLockedUSD' and 'lpLockedPct' casing
                    locked_usd = LiquidityDigest._to_float(lp.get("lpLockedUSD") or lp.get("lpLockedUsd") or lp.get("lpLocked") or lp.get("lp_locked_usd") or lp.get("lpLockedUSD"))
                    locked_pct = LiquidityDigest._to_float(lp.get("lpLockedPct") or lp.get("lpLockedPct") or lp.get("lp_locked_pct") or lp.get("lpLockedPct"))
                    if locked_usd > 0 or locked_pct > 0:
                        total_locked_usd += locked_usd
                        total_locked_pct += locked_pct
                        counted += 1

                lp_locked_usd = total_locked_usd
                if counted > 0:
                    # average percentage where available
                    lp_locked_pct = (total_locked_pct / float(counted))

            liquidity_ratio = (stable_liquidity_usd / (total_liquidity_usd + 1e-9)) if total_liquidity_usd > 0 else 0.0
            locked_liquidity_ratio = (lp_locked_usd / (total_liquidity_usd + 1e-9)) if total_liquidity_usd > 0 else 0.0
            multi_pool_presence = pool_count > 1

            return {
                "total_liquidity_usd": total_liquidity_usd,
                "stable_liquidity_usd": stable_liquidity_usd,
                "lp_locked_pct": lp_locked_pct,
                "lp_locked_usd": lp_locked_usd,
                "pool_count": pool_count,
                "liquidity_ratio": liquidity_ratio,
                "locked_liquidity_ratio": locked_liquidity_ratio,
                "multi_pool_presence": multi_pool_presence
            }

        except Exception as e:
            return {
                "total_liquidity_usd": 0,
                "stable_liquidity_usd": 0,
                "lp_locked_pct": 0,
                "lp_locked_usd": 0,
                "pool_count": 0,
                "liquidity_ratio": 0,
                "locked_liquidity_ratio": 0,
                "multi_pool_presence": False,
                "_error": str(e)
            }
