# app/Routes/trigger.py

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
import logging

from app.DataStream import fetch_solana_tokens
from app.Enrichment import (
    fetch_dexscreener_data,
    parse_dexscreener_batch,
    TokenEnricher,
    BatchProcessor,
    HeliusRpcClient,
    RugCheckClient,
)
from app.Digestion.digest import TokenDigester

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize enrichment components
rpc_client = HeliusRpcClient(pipeline="pipeline_10m")
batch_processor = BatchProcessor(rpc_client=rpc_client, batch_size=100, max_concurrent=10)
token_enricher = TokenEnricher(batch_processor=batch_processor)
rugcheck_client = RugCheckClient()
digester = TokenDigester()


# -------------------------
# Helper Functions
# -------------------------

async def enrich_with_rpc_data(parsed_tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not parsed_tokens:
        return []

    try:
        token_addresses = [
            t.get("base_token", {}).get("address")
            for t in parsed_tokens
            if t.get("base_token", {}).get("address")
        ]
        if not token_addresses:
            return parsed_tokens

        account_result = await batch_processor.enrich_token_accounts(token_addresses)
        account_map = {item["address"]: item["account_data"] for item in account_result.successful}

        enriched = []
        for token in parsed_tokens:
            addr = token.get("base_token", {}).get("address")
            token["rpc_data"] = account_map.get(addr)
            token["on_chain_verified"] = bool(addr and addr in account_map)
            enriched.append(token)

        return enriched
    except Exception as e:
        logger.error(f"RPC enrichment error: {e}", exc_info=True)
        return parsed_tokens


async def enrich_with_rugcheck(parsed_tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        addresses = [
            t.get("base_token", {}).get("address")
            for t in parsed_tokens
            if t.get("base_token", {}).get("address")
        ]
        if not addresses:
            return parsed_tokens

        reports = await rugcheck_client.batch_fetch_reports(addresses, concurrency=1)
        enriched = []
        for token in parsed_tokens:
            addr = token.get("base_token", {}).get("address")
            token["rugcheck"] = reports.get(addr, {"status": "unavailable"})
            enriched.append(token)

        return enriched
    except Exception as e:
        logger.error(f"RugCheck enrichment error: {e}", exc_info=True)
        return parsed_tokens


# -------------------------
# Routes
# -------------------------

@router.get("/start", summary="Sniper pipeline → Digested Tokens")
async def run_sniper():
    try:
        logger.info("🚀 Starting sniper pipeline...")

        # Step 1: Fetch raw Solana tokens
        raw_tokens = await fetch_solana_tokens()
        if not raw_tokens:
            return {"status": "no_data", "tokens": []}

        # Step 2: Dexscreener enrichment
        enriched = []
        batch_size = 30
        for i in range(0, len(raw_tokens), batch_size):
            batch = raw_tokens[i:i+batch_size]
            addresses = [t["tokenAddress"] for t in batch if "tokenAddress" in t]
            if not addresses:
                continue
            try:
                data = await fetch_dexscreener_data("solana", addresses)
                enriched.extend(data)
            except Exception as e:
                logger.error(f"Dexscreener batch {i//batch_size+1} error: {e}")

        # Step 3: Parse Dexscreener
        parsed = parse_dexscreener_batch(enriched)

        # Step 4: RPC enrichment
        rpc_enriched = await enrich_with_rpc_data(parsed)

        # Step 5: RugCheck enrichment
        rugcheck_enriched = await enrich_with_rugcheck(rpc_enriched)

        # Step 6: Digest tokens
        digested = digester.digest_batch(rugcheck_enriched)

        return {
            "status": "success",
            "count": len(digested),
            "tokens": digested[:10],  # preview top 10
            "sample_token": digested[0] if digested else None,
        }

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@router.get("/analyze/{token_address}", summary="Get digested data for a specific token")
async def analyze_token(token_address: str):
    try:
        logger.info(f"🔎 Analyzing token {token_address}")

        # Comprehensive on-chain
        comp = await token_enricher.get_comprehensive_token_data(token_address)

        # Dexscreener
        dex_data = await fetch_dexscreener_data("solana", [token_address])
        parsed_dex = parse_dexscreener_batch(dex_data) if dex_data else []
        market_data = parsed_dex[0] if parsed_dex else {}

        # RugCheck
        try:
            rug_report = await rugcheck_client.fetch_report(token_address)
        except Exception as e:
            rug_report = {"status": "error", "error": str(e)}

        # Merge
        combined = {**market_data, "rpc_data": comp, "rugcheck": rug_report}
        digested = digester.digest_token(combined)

        return {"status": "success", "token": digested}

    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analyze error: {str(e)}")
