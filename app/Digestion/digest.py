# app/Enrichment/digest.py
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import math
import logging
import json

logger = logging.getLogger(__name__)




class TokenDigester:
    """
    Token digestion / normalizer.
    Methods:
      - digest_batch(tokens) -> list of normalized dicts
      - digest_token(token) -> normalized dict
    All derived fields are prefixed with `digest_` to make them explicit.
    """

    def __init__(self, now: Optional[datetime] = None):
        self.now = (now or datetime.now(timezone.utc)).replace(tzinfo=timezone.utc)

    # -------------------------
    # Utilities
    # -------------------------
    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """
        Accepts:
          - ISO-8601 strings ("2025-10-02T18:51:55")
          - integer/float milliseconds since epoch
          - None
        Returns datetime in UTC or None.
        """
        if value is None:
            return None
        # numeric timestamp (ms)
        if isinstance(value, (int, float)):
            # detect if value is in seconds not ms (naive heuristic)
            if value > 1e12:
                # already ms
                ts = value / 1000.0
            elif value > 1e9:
                # seconds
                ts = float(value)
            else:
                ts = float(value)
            try:
                return datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                return None
        if isinstance(value, str):
            try:
                # some strings may be numeric
                if value.isdigit():
                    return TokenDigester._parse_datetime(int(value))
                # attempt iso parse
                # Python's fromisoformat may not accept trailing Z, so handle variants
                s = value
                if s.endswith("Z"):
                    s = s[:-1]
                # fromisoformat supports YYYY-MM-DDTHH:MM:SS(.micro) optionally with offset
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt
            except Exception:
                # fallback: attempt parsing as milliseconds in string
                try:
                    return TokenDigester._parse_datetime(int(value))
                except Exception:
                    return None
        return None

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            if x is None:
                return default
            return float(x)
        except Exception:
            return default

    @staticmethod
    def _gini(values: List[float]) -> float:
        """Compute Gini coefficient. Returns 0..1."""
        vals = [v for v in values if v >= 0]
        if not vals:
            return 0.0
        vals = sorted(vals)
        n = len(vals)
        total = sum(vals)
        if total == 0:
            return 0.0
        cum = 0.0
        for i, v in enumerate(vals, start=1):
            cum += i * v
        gini = (2 * cum) / (n * total) - (n + 1) / n
        return max(0.0, min(1.0, gini))

    @staticmethod
    def _sum_pct_from_holders(holders: List[Dict[str, Any]], top_n: int) -> float:
        """Sum pct fields for top N holders; fallback to compute from amounts if pct absent."""
        if not holders:
            return 0.0
        # prefer 'pct' if present
        if all("pct" in h for h in holders[:top_n]):
            return sum((float(h.get("pct") or 0) for h in holders[:top_n]))
        # else, try to compute from amounts
        amounts = []
        for h in holders:
            amt = h.get("amount") or h.get("uiAmount") or 0
            try:
                amounts.append(float(amt))
            except Exception:
                try:
                    amounts.append(float(str(amt)))
                except Exception:
                    amounts.append(0.0)
        total = sum(amounts) or 0.0
        if total == 0:
            return 0.0
        top_sum = sum(amounts[:top_n])
        return (top_sum / total) * 100.0

    @staticmethod
    def _extract_holders(token: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Pull a canonical holder list from likely locations:
           - token['rugcheck']['topHolders'] (common)
           - token['rpc_data']['holder_info']['largest_holders']
           - token['rugcheck']['topHolders'] etc.
        Normalizes each holder to {address, amount, uiAmount, pct, insider}
        """
        holders = []
        # common keys we've seen in your sample
        paths = [
            ("rugcheck", "topHolders"),
            ("rugcheck", "topHolders"),  # duplicate but safe
            ("rpc_data", "holder_info", "largest_holders"),
            ("rugcheck", "topHolders"),  # redundancy to emphasize
            ("rpc_data", "holder_info", "top_holders"),
            ("rugcheck", "topHolders")
        ]
        for p in paths:
            cur = token
            for k in p:
                cur = cur.get(k) if isinstance(cur, dict) else None
                if cur is None:
                    break
            if cur and isinstance(cur, list):
                # found a candidate list
                for h in cur:
                    holder = {
                        "address": h.get("address") or h.get("owner") or h.get("ownerAddress"),
                        "amount": h.get("amount") or h.get("uiAmount") or h.get("value"),
                        "uiAmount": h.get("uiAmount") or h.get("uiAmountString"),
                        "pct": h.get("pct") or h.get("percentage") or None,
                        "insider": bool(h.get("insider", False))
                    }
                    holders.append(holder)
                if holders:
                    return holders
        # fallback: no holders found
        return []

    @staticmethod
    def _merge_lists_unique(a: Optional[List[Any]], b: Optional[List[Any]]) -> List[Any]:
        a = a or []
        b = b or []
        out = []
        seen = set()
        for item in a + b:
            key = json.dumps(item, sort_keys=True) if isinstance(item, dict) else str(item)
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    # -------------------------
    # Core digest functions
    # -------------------------
    def digest_token(self, token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a single parsed/enriched token dict to a normalized 'digested' form.
        Adds digest_ prefixed fields and stores original under 'raw'.
        """
        digest: Dict[str, Any] = {}
        raw = token.copy()  # shallow copy; keep original under raw
        digest["raw"] = raw

        # Basic identity
        chain_id = token.get("chain_id") or token.get("chainId") or token.get("chain") or "solana"
        digest["chain_id"] = chain_id
        base = token.get("base_token") or token.get("baseToken") or {}
        quote = token.get("quote_token") or token.get("quoteToken") or {}
        base_addr = base.get("address") if isinstance(base, dict) else None
        pair_addr = token.get("pair_address") or token.get("pairAddress") or token.get("pairAddress")
        digest["base_address"] = base_addr
        digest["pair_address"] = pair_addr
        digest["name"] = (base.get("name") if base else None) or token.get("name") or token.get("title")
        digest["symbol"] = (base.get("symbol") if base else None) or token.get("symbol")

        # Market / price fields
        digest["digest_price_usd"] = self._safe_float(token.get("price_usd") or token.get("priceUsd"))
        digest["digest_price_native"] = self._safe_float(token.get("price_native") or token.get("priceNative"))
        digest["digest_fdv"] = self._safe_float(token.get("fdv"))
        digest["digest_market_cap"] = self._safe_float(token.get("market_cap") or token.get("marketCap"))
        digest["digest_volume_h24"] = self._safe_float(token.get("volume", {}).get("h24") if token.get("volume") else token.get("volume_h24"))
        digest["digest_volume_h1"] = self._safe_float(token.get("volume", {}).get("h1") if token.get("volume") else token.get("volume_h1"))

        # Txn metrics
        txns = token.get("txns") or token.get("txns", {})
        digest["digest_txns_m5_buys"] = int(txns.get("m5", {}).get("buys", 0)) if txns else 0
        digest["digest_txns_m5_sells"] = int(txns.get("m5", {}).get("sells", 0)) if txns else 0
        digest["digest_txns_h1_buys"] = int(txns.get("h1", {}).get("buys", 0)) if txns else 0
        digest["digest_txns_h1_sells"] = int(txns.get("h1", {}).get("sells", 0)) if txns else 0

        # Price change windows
        pc = token.get("price_change") or token.get("priceChange") or {}
        digest["digest_price_change_m5"] = self._safe_float(pc.get("m5"))
        digest["digest_price_change_h1"] = self._safe_float(pc.get("h1"))
        digest["digest_price_change_h6"] = self._safe_float(pc.get("h6"))
        digest["digest_price_change_h24"] = self._safe_float(pc.get("h24"))

        # Pair creation & age (hours)
        pair_created_raw = token.get("pair_created_at") or token.get("pairCreatedAt") or token.get("pairCreatedAt")
        pair_dt = self._parse_datetime(pair_created_raw)
        digest["pair_created_at"] = pair_dt.isoformat() if pair_dt else None
        if pair_dt:
            delta = (self.now - pair_dt).total_seconds()
            digest["digest_age_hours"] = round(delta / 3600.0, 4)
        else:
            digest["digest_age_hours"] = None

        # Images / socials / websites (merge from dexscreener and rugcheck and rpc info)
        dex_info = token.get("info") or token.get("info", {})
        rug_info = (token.get("rugcheck") or {}).get("fileMeta", {}) if token.get("rugcheck") else {}
        rpc_info = (token.get("rpc_data") or {}).get("info") if token.get("rpc_data") else None

        images = []
        for candidate in (dex_info, rug_info, rpc_info):
            if not candidate:
                continue
            if isinstance(candidate, dict):
                for k in ("image", "imageUrl", "open_graph", "openGraph", "header"):
                    v = candidate.get(k)
                    if v:
                        images.append(v)
                # websites may be a list of {label,url} or list of strings
                ws = candidate.get("websites") or candidate.get("websites", [])
                if isinstance(ws, list):
                    for w in ws:
                        if isinstance(w, dict):
                            images.append(w.get("url"))  # sometimes website fields are URLs too
        digest["digest_images"] = [u for u in list(dict.fromkeys(images)) if u]

        # combine socials / websites
        socials = dex_info.get("socials") if isinstance(dex_info, dict) else None
        socials_rug = rug_info.get("socials") if isinstance(rug_info, dict) else None
        combined_socials = {}
        if isinstance(socials, dict):
            combined_socials.update(socials)
        if isinstance(socials_rug, dict):
            combined_socials.update(socials_rug)
        digest["digest_socials"] = combined_socials or {}

        websites = dex_info.get("websites") or rug_info.get("websites") or []
        if isinstance(websites, list):
            # websites could be list[str] or list[dict]
            normalized_sites = []
            for w in websites:
                if isinstance(w, dict):
                    normalized_sites.append(w.get("url") or w.get("label"))
                else:
                    normalized_sites.append(w)
            digest["digest_websites"] = list(dict.fromkeys([x for x in normalized_sites if x]))
        else:
            digest["digest_websites"] = []

        # RPC & Rugcheck raw enrollment
        digest["digest_on_chain_verified"] = bool(token.get("on_chain_verified"))
        digest["digest_has_rugcheck"] = bool(token.get("rugcheck"))

        # Holder extraction and concentration metrics
        holders = self._extract_holders(token)
        digest["digest_holder_count_estimate"] = token.get("holder_count") or token.get("holderCount") or len(holders)
        digest["digest_holders_sample"] = holders[:10]  # keep small sample for quick inspection

        # compute top1/top10/top20 ownership percentage
        digest["digest_top_1_pct"] = round(self._sum_pct_from_holders(holders, 1), 4)
        digest["digest_top_10_pct"] = round(self._sum_pct_from_holders(holders, 10), 4)
        digest["digest_top_20_pct"] = round(self._sum_pct_from_holders(holders, 20), 4)

        # insiders count
        digest["digest_insiders_count"] = sum(1 for h in holders if h.get("insider"))

        # Gini of top-holder amounts (if amounts exist)
        amounts = []
        for h in holders:
            v = h.get("uiAmount") or h.get("amount")
            try:
                amounts.append(float(v))
            except Exception:
                try:
                    amounts.append(float(str(v)))
                except Exception:
                    amounts.append(0.0)
        digest["digest_gini_top_holders"] = round(self._gini(amounts), 5) if amounts else 0.0

        # Liquidity and LP metrics
        liquidity = token.get("liquidity") or {}
        # Dexscreener sometimes keeps liquidity under token['liquidity']['usd']
        liquidity_usd = None
        if isinstance(liquidity, dict):
            liquidity_usd = self._safe_float(liquidity.get("usd") or liquidity.get("usd_liquidity") or liquidity.get("liquidity_usd"))
        # rugcheck may include lpLockedPct etc under nested markets
        lp_locked_pct = None
        if token.get("rugcheck"):
            try:
                lp_locked_pct = token["rugcheck"].get("lpLockedPct") or token["rugcheck"].get("lpLocked", {}).get("pct") or token["rugcheck"].get("lpLockedPct")
                if lp_locked_pct is not None:
                    lp_locked_pct = float(lp_locked_pct)
            except Exception:
                lp_locked_pct = None

        digest["digest_liquidity_usd"] = liquidity_usd
        digest["digest_lp_locked_pct"] = lp_locked_pct

        market_cap = digest["digest_market_cap"] or 0.0
        digest["digest_liquidity_to_mc_ratio"] = round((liquidity_usd / market_cap) if (liquidity_usd and market_cap) else 0.0, 6)

        # Rugcheck flags summary (flatten risk names & levels)
        rug = token.get("rugcheck") or {}
        risks = rug.get("risks") or token.get("risks") or []
        digest["digest_risks"] = [{"name": r.get("name"), "level": r.get("level"), "score": r.get("score")} for r in risks] if risks else []

        # derived quick flags
        digest["digest_flag_mint_authority_enabled"] = any((r.get("name") == "Mint Authority still enabled") for r in risks) if risks else False
        digest["digest_flag_lp_unlocked"] = any((("LP Unlocked" in (r.get("name") or "")) or ("LP Unlocked" in (r.get("description") or ""))) for r in risks) if risks else False

        # keep a minimal canonical summary for downstream usage
        digest["digest_summary"] = {
            "symbol": digest.get("symbol"),
            "name": digest.get("name"),
            "address": base_addr,
            "pair": pair_addr,
            "price_usd": digest["digest_price_usd"],
            "market_cap": digest["digest_market_cap"],
            "liquidity_usd": digest["digest_liquidity_usd"],
            "age_hours": digest["digest_age_hours"],
            "top_1_pct": digest["digest_top_1_pct"],
            "top_10_pct": digest["digest_top_10_pct"],
            "gini": digest["digest_gini_top_holders"],
            "risk_flags": [r.get("name") for r in digest["digest_risks"][:5]]
        }

        # Manifest list of digest fields for debugging/tracking
        digest["digest_features"] = sorted([k for k in digest.keys() if k.startswith("digest_")])

        return digest

    def digest_batch(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of parsed/enriched tokens:
         - dedupe by base_address (fallback pair_address)
         - merge partial info (socials, websites, images)
         - return list of digested tokens
        """
        merged: Dict[str, Dict[str, Any]] = {}

        def merge_two(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
            # shallow merging strategy: prefer non-empty fields, union lists
            out = existing.copy()
            for k, v in incoming.items():
                if v is None:
                    continue
                if k in ("info", "rpc_data", "rugcheck"):
                    # prefer richer dict (by length) and merge keys
                    ev = out.get(k) or {}
                    if isinstance(ev, dict) and isinstance(v, dict):
                        ev.update({kk: vv for kk, vv in v.items() if vv is not None})
                        out[k] = ev
                    else:
                        out[k] = v
                elif isinstance(v, list):
                    out[k] = self._merge_lists_unique(out.get(k, []), v)
                elif isinstance(v, (int, float)) and (out.get(k) is None or out.get(k) == 0):
                    out[k] = v
                else:
                    # default: keep existing unless missing
                    if out.get(k) is None:
                        out[k] = v
            return out

        for token in tokens:
            # choose key: base address > pair address > url tokenAddress
            base_addr = (token.get("base_token") or {}).get("address") if token.get("base_token") else token.get("baseToken", {}).get("address") if token.get("baseToken") else None
            pair_addr = token.get("pair_address") or token.get("pairAddress") or token.get("pairAddress")
            dedupe_key = base_addr or pair_addr or token.get("tokenAddress") or token.get("tokenAddress")
            if not dedupe_key:
                dedupe_key = token.get("url") or token.get("url")

            if dedupe_key in merged:
                merged[dedupe_key] = merge_two(merged[dedupe_key], token)
            else:
                merged[dedupe_key] = token.copy()

        # Now digest each merged token
        out = []
        for _, merged_token in merged.items():
            try:
                d = self.digest_token(merged_token)
                out.append(d)
            except Exception as e:
                logger.exception("digest_batch: failed to digest token: %s", str(e))
        return out




