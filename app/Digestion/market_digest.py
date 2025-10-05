# app/Digestion/market_digest.py

from typing import Any, Dict
import statistics


class MarketDigest:
    """Capture all market-related performance metrics."""

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                v = value.strip().replace(",", "")
                return float(v) if v != "" else default
            if isinstance(value, dict):
                # try common keys
                for k in ("value", "amount", "price", "usd"):
                    if k in value:
                        try:
                            return float(value[k])
                        except Exception:
                            continue
                # fallback to any numeric value inside dict
                for v in value.values():
                    try:
                        return float(v)
                    except Exception:
                        continue
            return default
        except Exception:
            return default

    @staticmethod
    def digest(enriched_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract market metrics and compute derived fields for AI.
        """
        try:
            # Price fields (support multiple naming styles)
            price_usd = MarketDigest._to_float(
                enriched_token.get("price_usd")
                or enriched_token.get("priceUsd")
                or (enriched_token.get("rugcheck") or {}).get("price")
            )

            fdv = MarketDigest._to_float(enriched_token.get("fdv") or enriched_token.get("fdv_usd"))
            market_cap = MarketDigest._to_float(
                enriched_token.get("market_cap") or enriched_token.get("marketCap") or enriched_token.get("market_cap_usd")
            )

            # txns: compute 24h transactions as h24 or sum of h1/h6 heuristics if not present
            txns = enriched_token.get("txns") or {}
            tx_m5 = txns.get("m5") or {}
            tx_h1 = txns.get("h1") or {}
            tx_h6 = txns.get("h6") or {}
            tx_h24 = txns.get("h24") or {}

            buys_m5 = MarketDigest._to_float(tx_m5.get("buys"))
            sells_m5 = MarketDigest._to_float(tx_m5.get("sells"))
            buys_h1 = MarketDigest._to_float(tx_h1.get("buys"))
            sells_h1 = MarketDigest._to_float(tx_h1.get("sells"))
            buys_h6 = MarketDigest._to_float(tx_h6.get("buys"))
            sells_h6 = MarketDigest._to_float(tx_h6.get("sells"))
            buys_h24 = MarketDigest._to_float(tx_h24.get("buys"))
            sells_h24 = MarketDigest._to_float(tx_h24.get("sells"))

            # Prefer explicit h24 if available, else fallback to sum of recent windows
            if tx_h24:
                tx_24h = buys_h24 + sells_h24
            else:
                tx_24h = (buys_h6 + sells_h6) if (buys_h6 + sells_h6) > 0 else (buys_h1 + sells_h1)

            # Volume
            volume = enriched_token.get("volume") or {}
            volume_24h = MarketDigest._to_float(volume.get("h24"))

            # Price changes: sample uses price_change with keys m5/h1/h6/h24
            price_change = enriched_token.get("price_change") or enriched_token.get("priceChange") or {}
            price_change_1h = MarketDigest._to_float(price_change.get("h1") or price_change.get("1h"))
            price_change_6h = MarketDigest._to_float(price_change.get("h6") or price_change.get("6h"))
            price_change_24h = MarketDigest._to_float(price_change.get("h24") or price_change.get("24h"))

            # Compute buy/sell ratio using recent window (m5 preferred)
            buys_recent = buys_m5 or buys_h1 or buys_h6 or buys_h24
            sells_recent = sells_m5 or sells_h1 or sells_h6 or sells_h24

            buy_sell_ratio = float(buys_recent) / (float(sells_recent) + 1e-9) if sells_recent > 0 else float(buys_recent)

            # Holders for velocity
            rugcheck = enriched_token.get("rugcheck") or {}
            holders_total = MarketDigest._to_float(rugcheck.get("totalHolders"), default=0.0)

            velocity_score = (tx_24h / (holders_total + 1e-9)) if holders_total > 0 else 0.0

            # Momentum & volatility
            momentum_index = price_change_1h + price_change_6h + price_change_24h
            price_changes = [price_change_1h, price_change_6h, price_change_24h]
            volatility_score = 0.0
            try:
                if len([p for p in price_changes if p is not None]) > 1:
                    volatility_score = statistics.stdev(price_changes)
            except Exception:
                volatility_score = 0.0

            total_buys = buys_recent
            total_sells = sells_recent
            buy_pressure_ratio = float(total_buys) / (float(total_buys) + float(total_sells) + 1e-9) if (total_buys + total_sells) > 0 else 0.0

            return {
                "price_usd": price_usd,
                "fdv": fdv,
                "market_cap": market_cap,
                "tx_24h": tx_24h,
                "volume_24h": volume_24h,
                "price_change_1h": price_change_1h,
                "price_change_6h": price_change_6h,
                "price_change_24h": price_change_24h,
                "buys_1h":buys_h1,
                "sells_1h":sells_h1,
                "buys_6h":buys_h6,
                "sells_6h":sells_h6,
                "buys_24h":buys_h24,
                "sells_24h":sells_h24,
                "buy_sell_ratio": buy_sell_ratio,
                "velocity_score": velocity_score,
                "momentum_index": momentum_index,
                "volatility_score": volatility_score,
                "buy_pressure_ratio": buy_pressure_ratio
            }

        except Exception as e:
            return {
                "price_usd": None,
                "fdv": None,
                "market_cap": None,
                "tx_24h": 0,
                "volume_24h": 0,
                "price_change_1h": 0,
                "price_change_6h": 0,
                "price_change_24h": 0,
                "buy_sell_ratio": 0,
                "velocity_score": 0,
                "momentum_index": 0,
                "volatility_score": 0,
                "buy_pressure_ratio": 0,
                "_error": str(e)
            }
