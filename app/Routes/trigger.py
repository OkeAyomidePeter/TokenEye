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
from app.Digestion import TokenDigester
from app.DataModels import TokenDigest
from app.DataModels import DigestData, MetaDigest, MarketDigest, HolderDigest, LiquidityDigest, SocialDigest, FlagDigest, DerivedDigest
from app.Scoring import TokenScorer
from app.Database import save_tokens_batch, save_token, SessionLocal
from app.Notifier.telegram import send_token_notification
from app.config import MAX_TOKEN_AGE_HOURS
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize enrichment components
rpc_client = HeliusRpcClient(pipeline="pipeline_10m")
batch_processor = BatchProcessor(rpc_client=rpc_client, batch_size=100, max_concurrent=10)
token_enricher = TokenEnricher(batch_processor=batch_processor)
rugcheck_client = RugCheckClient()

# Initialize digestion layer
digester = TokenDigester()

# Initialize scoring layer
token_scorer = TokenScorer()


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

        # Step 3.5: Filter by age
        filtered_parsed = []
        skipped_count = 0
        now = datetime.now(timezone.utc)
        
        for token in parsed:
            created_at = token.get("pair_created_at")
            if not created_at:
                # If no creation time, we can't determine age. 
                # Decision: Keep it or drop it? Let's keep it to be safe, or drop if strict.
                # For now, let's keep it but log warning if needed.
                filtered_parsed.append(token)
                continue
            
            # Ensure created_at is timezone-aware if now is
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
                
            age = now - created_at
            if age <= timedelta(hours=MAX_TOKEN_AGE_HOURS):
                filtered_parsed.append(token)
            else:
                skipped_count += 1
        
        if skipped_count > 0:
            logger.info(f"⏳ Filtered {skipped_count} tokens older than {MAX_TOKEN_AGE_HOURS} hours")
            
        parsed = filtered_parsed

        # Step 4: RPC enrichment
        rpc_enriched = await enrich_with_rpc_data(parsed)

        # Step 5: RugCheck enrichment
        rugcheck_enriched = await enrich_with_rugcheck(rpc_enriched)

        # Step 6: Digest tokens through the digestion layer
        digested_raw = digester.digest_batch(rugcheck_enriched)
        
        # Step 7: Validate and convert to Pydantic models
        validated_tokens = []
        for digest_data in digested_raw:
            try:
                validated_token = TokenDigest.from_digest_dict(digest_data)
                validated_tokens.append(validated_token)
            except Exception as e:
                logger.error(f"Validation failed for token: {e}")
                # Create a minimal valid token for failed validations
                
                
                validated_token = TokenDigest(
                    address=digest_data.get("address"),
                    symbol=digest_data.get("symbol"),
                    chain="solana",
                    digest=DigestData(
                        meta=MetaDigest(error=f"Validation failed: {str(e)}"),
                        market=MarketDigest(error=f"Validation failed: {str(e)}"),
                        holders=HolderDigest(error=f"Validation failed: {str(e)}"),
                        liquidity=LiquidityDigest(error=f"Validation failed: {str(e)}"),
                        socials=SocialDigest(error=f"Validation failed: {str(e)}"),
                        flags=FlagDigest(error=f"Validation failed: {str(e)}"),
                        derived=DerivedDigest(error=f"Validation failed: {str(e)}")
                    ),
                    raw=digest_data.get("raw")
                )
                validated_tokens.append(validated_token)
        
        # Step 8: Score tokens and append scores to validated tokens
        scored_tokens = []
        for validated_token in validated_tokens:
            try:
                # Convert TokenDigest to dict for scoring
                token_dict = validated_token.model_dump()
                
                # Score the token
                score_result = token_scorer.score_token(token_dict, include_breakdown=False)
                
                # Append score data to token dict
                token_dict["score"] = {
                    "final_score": score_result.get("final_score", 0.0),
                    "classification": score_result.get("classification", "low potential"),
                    "component_scores": score_result.get("component_scores", {}),
                }
                
                scored_tokens.append(token_dict)
            except Exception as e:
                logger.error(f"Scoring failed for token {validated_token.address}: {e}")
                # Append token with zero score if scoring fails
                token_dict = validated_token.model_dump()
                token_dict["score"] = {
                    "final_score": 0.0,
                    "classification": "low potential",
                    "component_scores": {},
                    "error": str(e)
                }
                scored_tokens.append(token_dict)
        
        # Step 9: Save tokens to database
        db_result = None
        try:
            db_result = save_tokens_batch(scored_tokens)
            logger.info(f"Database save result: {db_result['success_count']}/{db_result['total']} tokens saved")
        except Exception as e:
            logger.error(f"Database save error: {e}", exc_info=True)
        
        # Step 10: Notify Telegram channels per token based on score
        notifications = []
        for t in scored_tokens:
            try:
                notif = await send_token_notification(t, pro_threshold=50.0)
                notifications.append({"address": t.get("address"), **notif})
            except Exception as e:
                logger.error(f"Notification failed for {t.get('address')}: {e}")
                notifications.append({"address": t.get("address"), "sent": False, "error": str(e)})

        return {
            "status": "success",
            "tokens": scored_tokens,
            "database": {
                "saved": db_result.get("success_count", 0) if db_result else 0,
                "failed": db_result.get("failure_count", 0) if db_result else 0,
                "total": db_result.get("total", len(scored_tokens)) if db_result else len(scored_tokens)
            } if db_result else None,
            "notifications": notifications,
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

        # Combine enriched data from all sources
        combined = {**market_data, "rpc_data": comp, "rugcheck": rug_report}
        
        # Digest the combined data
        digested_raw = digester.digest_token(combined)
        
        # Validate and convert to Pydantic model
        try:
            validated_token = TokenDigest.from_digest_dict(digested_raw)
            token_dict = validated_token.model_dump()
            
            # Score the token
            try:
                score_result = token_scorer.score_token(token_dict, include_breakdown=False)
                token_dict["score"] = {
                    "final_score": score_result.get("final_score", 0.0),
                    "classification": score_result.get("classification", "low potential"),
                    "component_scores": score_result.get("component_scores", {}),
                }
            except Exception as e:
                logger.error(f"Scoring failed for token {token_address}: {e}")
                token_dict["score"] = {
                    "final_score": 0.0,
                    "classification": "low potential",
                    "component_scores": {},
                    "error": str(e)
                }
            
            # Save token to database
            try:
                db = SessionLocal()
                save_token_result = save_token(db, token_dict)
                if save_token_result:
                    logger.info(f"Saved token {token_address} to database")
                else:
                    logger.warning(f"Failed to save token {token_address} to database")
                db.close()
            except Exception as e:
                logger.error(f"Database save error for token {token_address}: {e}", exc_info=True)
            
            return {"status": "success", "token": token_dict}
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            # Return raw data if validation fails
            return {"status": "success", "token": digested_raw, "validation_error": str(e)}

    except Exception as e:
        logger.error(f"Analyze error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analyze error: {str(e)}")



