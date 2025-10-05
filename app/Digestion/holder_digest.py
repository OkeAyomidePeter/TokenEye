# app/Digestion/holder_digest.py

from typing import Any, Dict, List


class HolderDigest:
    """Analyze token holder distribution and insider dominance."""

    @staticmethod
    def digest(enriched_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract holder distribution data and compute derived fields for AI.
        """
        try:
            rugcheck = enriched_token.get("rugcheck") or {}

            total_holders = int(rugcheck.get("totalHolders") or 0)

            top_holders = rugcheck.get("topHolders") or []
            if not isinstance(top_holders, list):
                top_holders = []

            creator_balance = float(rugcheck.get("creatorBalance") or 0.0)

            # insider detection values (note upstream keys)
            graph_insiders_detected = int(rugcheck.get("graphInsidersDetected") or 0)
            insider_networks = rugcheck.get("insiderNetworks") or []
            if not isinstance(insider_networks, list):
                insider_networks = []

            # Helper to read percentage (Dexscreener uses 'pct')
            def _holder_pct(h: Dict[str, Any]) -> float:
                if not isinstance(h, dict):
                    return 0.0
                for k in ("pct", "percentage", "pct_share"):
                    v = h.get(k)
                    if v is not None:
                        try:
                            return float(v)
                        except Exception:
                            continue
                return 0.0

            top10_share = 0.0
            top5_share = 0.0
            if top_holders:
                top10_share = sum(_holder_pct(h) for h in top_holders[:min(10, len(top_holders))])
                top5_share = sum(_holder_pct(h) for h in top_holders[:min(5, len(top_holders))])

            # Creator share: if token supply present, compute accurately
            token_info = rugcheck.get("token") or {}
            token_supply = None
            try:
                token_supply = float(token_info.get("supply") or token_info.get("totalSupply") or 0.0)
            except Exception:
                token_supply = 0.0

            creator_share = 0.0
            if token_supply and creator_balance:
                # If token units are in raw (not ui), but both are raw, this gives ratio
                try:
                    creator_share = (float(creator_balance) / (token_supply + 1e-9)) * 100.0
                except Exception:
                    creator_share = 0.0

            # Gini coefficient
            gini_coefficient = HolderDigest._calculate_gini_coefficient(top_holders)

            insider_count = len(insider_networks) if isinstance(insider_networks, list) else 0
            # incorporate graph_insiders_detected into an insider network score
            insider_network_score = 1.0 if (graph_insiders_detected or insider_count > 0) else 0.0

            holder_concentration_score = top10_share / 100.0 if top10_share > 0 else 0.0
            is_risky_holder_distribution = bool(top5_share > 70.0)

            return {
                "total_holders": total_holders,
                "top10_share": top10_share,
                "top5_share": top5_share,
                "creator_share": creator_share,
                "insider_count": insider_count,
                "gini_coefficient": gini_coefficient,
                "holder_concentration_score": holder_concentration_score,
                "is_risky_holder_distribution": is_risky_holder_distribution,
                "insider_network_score": insider_network_score
            }

        except Exception as e:
            return {
                "total_holders": 0,
                "top10_share": 0,
                "top5_share": 0,
                "creator_share": 0,
                "insider_count": 0,
                "gini_coefficient": 0,
                "holder_concentration_score": 0,
                "is_risky_holder_distribution": False,
                "insider_network_score": 0,
                "_error": str(e)
            }

    @staticmethod
    def _calculate_gini_coefficient(holders: List[Dict[str, Any]]) -> float:
        """
        Calculate Gini coefficient for holder distribution using 'pct' values.
        """
        if not holders or len(holders) < 2:
            return 0.0
        try:
            # extract percentages from holders (pct or percentage)
            percentages = []
            for h in holders:
                if isinstance(h, dict):
                    val = None
                    for k in ("pct", "percentage", "pct_share"):
                        if k in h and h.get(k) is not None:
                            try:
                                val = float(h.get(k))
                                break
                            except Exception:
                                val = None
                    if val is not None:
                        percentages.append(val)

            percentages = [p for p in percentages if p > 0]
            if len(percentages) < 2:
                return 0.0

            percentages.sort()
            n = len(percentages)
            total = sum(percentages)
            if total == 0:
                return 0.0

            cumulative = 0.0
            weighted_sum = 0.0
            for i, p in enumerate(percentages):
                cumulative += p
                weighted_sum += (i + 1) * p

            gini = (2 * weighted_sum) / (n * total) - (n + 1) / n
            return max(0.0, min(1.0, gini))
        except Exception:
            return 0.0
