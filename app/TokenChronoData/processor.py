import logging
from typing import Any, Dict, List

from app.Database import (
    SessionLocal,
    get_due_schedules,
    insert_token_history,
    mark_schedule_processed,
)
from app.Enrichment import (
    fetch_dexscreener_data,
    parse_dexscreener_batch,
    TokenEnricher,
    BatchProcessor,
    HeliusRpcClient,
    RugCheckClient,
)
from app.Digestion import TokenDigester
# from app.DataStream import fetch_solana_tokens  
from app.Scoring import TokenScorer

logger = logging.getLogger(__name__)


# Reuse long-lived components for performance
_rpc_client = HeliusRpcClient(pipeline="pipeline_10m")
_batch_processor = BatchProcessor(rpc_client=_rpc_client, batch_size=100, max_concurrent=10)
_token_enricher = TokenEnricher(batch_processor=_batch_processor)
_rugcheck_client = RugCheckClient()
_digester = TokenDigester()
_scorer = TokenScorer()


async def _enrich_addresses(addresses: List[str]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    if not addresses:
        return enriched

    # Dexscreener
    try:
        dex_data = await fetch_dexscreener_data("solana", addresses)
        parsed = parse_dexscreener_batch(dex_data) if dex_data else []
    except Exception as e:
        logger.error(f"Dexscreener enrichment failed: {e}")
        parsed = []

    # RPC
    try:
        account_result = await _batch_processor.enrich_token_accounts(addresses)
        account_map = {item["address"]: item["account_data"] for item in account_result.successful}
    except Exception as e:
        logger.error(f"RPC enrichment failed: {e}")
        account_map = {}

    # RugCheck
    try:
        reports = await _rugcheck_client.batch_fetch_reports(addresses, concurrency=1)
    except Exception as e:
        logger.error(f"RugCheck batch failed: {e}")
        reports = {}

    for token in parsed:
        addr = token.get("base_token", {}).get("address")
        token["rpc_data"] = account_map.get(addr)
        token["on_chain_verified"] = bool(addr and addr in account_map)
        token["rugcheck"] = reports.get(addr, {"status": "unavailable"})
        enriched.append(token)

    return enriched


async def process_due_schedules(limit: int = 50) -> Dict[str, Any]:
    """
    Process up to `limit` due schedules: re-enrich, digest, score, store snapshot, mark processed.
    """
    schedules = get_due_schedules(limit=limit)
    if not schedules:
        return {"processed": 0, "details": []}

    addresses = [s.token_address for s in schedules]
    enriched = await _enrich_addresses(addresses)

    # Digest, validate and score each token
    results: List[Dict[str, Any]] = []
    by_address = {t.get("base_token", {}).get("address"): t for t in enriched}

    for s in schedules:
        addr = s.token_address
        raw = by_address.get(addr)
        if not raw:
            results.append({"address": addr, "status": "skip", "reason": "no_enrichment"})
            continue

        digested = _digester.digest_token(raw)
        token_dict = digested  # Pydantic validation is not strictly required for history snapshot

        # Score
        try:
            score_result = _scorer.score_token(token_dict, include_breakdown=False)
        except Exception as e:
            logger.error(f"Scoring failed for {addr}: {e}")
            score_result = {"final_score": 0.0, "classification": "low potential", "component_scores": {}, "error": str(e)}

        token_dict = dict(token_dict)
        token_dict["address"] = addr
        token_dict["score"] = {
            "final_score": score_result.get("final_score", 0.0),
            "classification": score_result.get("classification", "low potential"),
            "component_scores": score_result.get("component_scores", {}),
        }

        db = SessionLocal()
        try:
            snap = insert_token_history(db, token_dict, s.check_type)
            ok = mark_schedule_processed(db, addr, s.check_type) if snap else False
            results.append({"address": addr, "check_type": s.check_type, "stored": bool(snap), "processed": ok})
        finally:
            db.close()

    return {"processed": len([r for r in results if r.get("processed")]), "details": results}


