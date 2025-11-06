# app/Database/repository.py

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from datetime import datetime, timedelta, timezone

from app.Database.database import SessionLocal
from app.Database.models import TokenData, TokenHistory, TokenSchedule

logger = logging.getLogger(__name__)


def map_token_digest_to_token_data(token_dict: Dict[str, Any]) -> TokenData:
    """
    Map a TokenDigest dictionary (with score) to TokenData model.
    
    Args:
        token_dict: Dictionary containing token digest data with score
        
    Returns:
        TokenData instance ready for database insertion
    """
    digest = token_dict.get("digest", {})
    meta = digest.get("meta", {})
    market = digest.get("market", {})
    holders = digest.get("holders", {})
    liquidity = digest.get("liquidity", {})
    socials = digest.get("socials", {})
    flags = digest.get("flags", {})
    derived = digest.get("derived", {})
    score = token_dict.get("score", {})
    
    # Handle creation_time - convert to string if needed
    creation_time = meta.get("creation_time")
    if creation_time is not None and not isinstance(creation_time, str):
        creation_time = str(creation_time)
    
    # Handle website - convert to JSON if it's a list
    website = socials.get("website")
    if website is not None and not isinstance(website, (list, dict)):
        website = [website] if website else None
    
    token_data = TokenData(
        # Basic identification
        address=token_dict.get("address") or meta.get("address"),
        symbol=token_dict.get("symbol") or meta.get("symbol"),
        chain=token_dict.get("chain", "solana"),
        name=meta.get("name"),
        creator=meta.get("creator"),
        creation_time=creation_time,
        token_age_days=meta.get("token_age_days"),
        token_age_hours=meta.get("token_age_hours"),
        decimals=meta.get("decimals"),
        
        # URLs and misc
        image_url=meta.get("image_url"),
        dexscreener_url=meta.get("dexscreener_url"),
        metadata_uri=meta.get("metadata_uri"),
        
        # Market metrics
        price_usd=market.get("price_usd"),
        fdv=market.get("fdv"),
        market_cap=market.get("market_cap"),
        tx_24h=market.get("tx_24h", 0),
        volume_24h=market.get("volume_24h", 0.0),
        price_change_1h=market.get("price_change_1h", 0.0),
        price_change_6h=market.get("price_change_6h", 0.0),
        price_change_24h=market.get("price_change_24h", 0.0),
        buys_m5=int(market.get("buys_m5", 0.0)),
        sells_m5=int(market.get("sells_m5", 0.0)),
        buys_1h=int(market.get("buys_1h", 0.0)),
        sells_1h=int(market.get("sells_1h", 0.0)),
        buys_6h=int(market.get("buys_6h", 0.0)),
        sells_6h=int(market.get("sells_6h", 0.0)),
        buys_24h=int(market.get("buys_24h", 0.0)),
        sells_24h=int(market.get("sells_24h", 0.0)),
        buy_sell_ratio=market.get("buy_sell_ratio", 0.0),
        velocity_score=market.get("velocity_score", 0.0),
        momentum_index=market.get("momentum_index", 0.0),
        volatility_score=market.get("volatility_score", 0.0),
        buy_pressure_ratio=market.get("buy_pressure_ratio", 0.0),
        
        # Holder metrics
        total_holders=holders.get("total_holders", 0),
        top10_share=holders.get("top10_share", 0.0),
        top5_share=holders.get("top5_share", 0.0),
        creator_share=holders.get("creator_share", 0.0),
        insider_count=holders.get("insider_count", 0),
        insider_network_score=holders.get("insider_network_score", 0.0),
        gini_coefficient=holders.get("gini_coefficient", 0.0),
        holder_concentration_score=holders.get("holder_concentration_score", 0.0),
        is_risky_holder_distribution=holders.get("is_risky_holder_distribution", False),
        
        # Liquidity
        total_liquidity_usd=liquidity.get("total_liquidity_usd", 0.0),
        stable_liquidity_usd=liquidity.get("stable_liquidity_usd", 0.0),
        lp_locked_usd=liquidity.get("lp_locked_usd", 0.0),
        lp_locked_pct=liquidity.get("lp_locked_pct", 0.0),
        liquidity_ratio=liquidity.get("liquidity_ratio", 0.0),
        locked_liquidity_ratio=liquidity.get("locked_liquidity_ratio", 0.0),
        pool_count=liquidity.get("pool_count", 0),
        multi_pool_presence=liquidity.get("multi_pool_presence", False),
        
        # Socials
        has_twitter=socials.get("has_twitter", False),
        twitter_url=socials.get("twitter_url"),
        website=website,
        has_discord=socials.get("has_discord", False),
        has_telegram=socials.get("has_telegram", False),
        has_website=socials.get("has_website", False),
        has_header_image=socials.get("has_header_image", False),
        social_presence_score=float(socials.get("social_presence_score", 0)),
        
        # Flags
        rugged=flags.get("rugged", False),
        has_freeze_authority=flags.get("has_freeze_authority", False),
        has_mint_authority=flags.get("has_mint_authority", False),
        risk_flags=flags.get("risk_flags", []),
        verified_on_chain=flags.get("verified_on_chain", False),
        revocation_risk_score=flags.get("revocation_risk_score", 0.0),
        rug_likelihood_flag=flags.get("rug_likelihood_flag", False),
        trust_score=flags.get("trust_score", 0.0),
        has_verified_creator=flags.get("has_verified_creator", False),
        has_kyc=flags.get("has_kyc", False),
        
        # Derived
        liquidity_to_fdv_ratio=derived.get("liquidity_to_fdv_ratio", 0.0),
        holder_to_liquidity_ratio=derived.get("holder_to_liquidity_ratio", 0.0),
        activity_to_fdv_ratio=derived.get("activity_to_fdv_ratio", 0.0),
        stability_index=derived.get("stability_index", 0.0),
        decentralization_score=derived.get("decentralization_score", 0.0),
        survivability_score=derived.get("survivability_score", 0.0),
        pump_probability=derived.get("pump_probability", 0.0),
        liquidity_retention=derived.get("liquidity_retention", 0.0),
        insider_manipulation_risk=derived.get("insider_manipulation_risk", 0.0),
        
        # Score
        final_score=score.get("final_score", 0.0),
        classification=score.get("classification", "low potential"),
        component_scores=score.get("component_scores", {}),
    )
    
    return token_data


def save_token(db: Session, token_dict: Dict[str, Any]) -> Optional[TokenData]:
    """
    Save or update a token in the database.
    
    Args:
        db: Database session
        token_dict: Token digest dictionary with score
        
    Returns:
        TokenData instance if successful, None otherwise
    """
    try:
        token_data = map_token_digest_to_token_data(token_dict)
        address = token_data.address
        
        if not address:
            logger.warning("Cannot save token: missing address")
            return None
        
        # Check if token exists
        existing_token = db.query(TokenData).filter(TokenData.address == address).first()
        
        if existing_token:
            # Update existing token
            for key, value in token_data.__dict__.items():
                if key not in ("id", "address", "first_seen", "_sa_instance_state"):
                    setattr(existing_token, key, value)
            token_to_save = existing_token
        else:
            # Insert new token
            token_to_save = token_data
            db.add(token_to_save)
            # Create initial schedule entries for a newly discovered token
            try:
                _create_initial_schedule(db, address)
            except Exception as e:
                logger.error(f"Failed creating initial schedule for {address}: {e}", exc_info=True)
        
        db.commit()
        db.refresh(token_to_save)
        logger.debug(f"Saved token {address} to database")
        return token_to_save
        
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error saving token {token_dict.get('address')}: {e}")
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving token {token_dict.get('address')}: {e}", exc_info=True)
        return None


def save_tokens_batch(token_dicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Save multiple tokens to the database in batch.
    
    Args:
        token_dicts: List of token digest dictionaries with scores
        
    Returns:
        Dictionary with success count, failure count, and errors
    """
    db = SessionLocal()
    success_count = 0
    failure_count = 0
    errors = []
    
    try:
        for token_dict in token_dicts:
            result = save_token(db, token_dict)
            if result:
                success_count += 1
            else:
                failure_count += 1
                errors.append({
                    "address": token_dict.get("address", "unknown"),
                    "error": "Failed to save token"
                })
        
        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "total": len(token_dicts),
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Batch save error: {e}", exc_info=True)
        db.rollback()
        return {
            "success_count": success_count,
            "failure_count": failure_count + (len(token_dicts) - success_count - failure_count),
            "total": len(token_dicts),
            "errors": errors + [{"error": f"Batch save failed: {str(e)}"}]
        }
    finally:
        db.close()


def get_token_by_address(address: str) -> Optional[TokenData]:
    """
    Retrieve a token from the database by address.
    
    Args:
        address: Token address
        
    Returns:
        TokenData instance if found, None otherwise
    """
    db = SessionLocal()
    try:
        token = db.query(TokenData).filter(TokenData.address == address).first()
        return token
    except Exception as e:
        logger.error(f"Error retrieving token {address}: {e}", exc_info=True)
        return None
    finally:
        db.close()


# -----------------------------
# Scheduling utilities
# -----------------------------

SCHEDULE_PRESETS: Dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "3h": timedelta(hours=3),
    "6h": timedelta(hours=6),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
}


def _create_initial_schedule(db: Session, token_address: str) -> None:
    now = datetime.now(timezone.utc)
    for check_type, delta in SCHEDULE_PRESETS.items():
        scheduled_for = now + delta
        schedule = TokenSchedule(
            token_address=token_address,
            check_type=check_type,
            scheduled_for=scheduled_for,
            processed=False,
        )
        # Upsert-like safety: skip if exists
        exists = (
            db.query(TokenSchedule)
            .filter(
                TokenSchedule.token_address == token_address,
                TokenSchedule.check_type == check_type,
            )
            .first()
        )
        if not exists:
            db.add(schedule)


def mark_schedule_processed(db: Session, token_address: str, check_type: str) -> bool:
    try:
        schedule = (
            db.query(TokenSchedule)
            .filter(
                TokenSchedule.token_address == token_address,
                TokenSchedule.check_type == check_type,
            )
            .first()
        )
        if not schedule:
            return False
        schedule.processed = True
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error marking schedule processed for {token_address} {check_type}: {e}", exc_info=True)
        return False


def get_due_schedules(limit: int = 100) -> List[TokenSchedule]:
    """
    Fetch due schedule entries (scheduled_for <= now and not processed).
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        items = (
            db.query(TokenSchedule)
            .filter(
                TokenSchedule.scheduled_for <= now,
                TokenSchedule.processed == False,  # noqa: E712
            )
            .order_by(TokenSchedule.scheduled_for.asc())
            .limit(limit)
            .all()
        )
        return items
    except Exception as e:
        logger.error(f"Error fetching due schedules: {e}", exc_info=True)
        return []
    finally:
        db.close()


# -----------------------------
# History snapshot utilities
# -----------------------------

def insert_token_history(db: Session, token_dict: Dict[str, Any], check_type: str) -> Optional[TokenHistory]:
    try:
        digest = token_dict.get("digest", {})
        meta = digest.get("meta", {})
        market = digest.get("market", {})
        holders = digest.get("holders", {})
        liquidity = digest.get("liquidity", {})
        socials = digest.get("socials", {})
        flags = digest.get("flags", {})
        derived = digest.get("derived", {})
        score = token_dict.get("score", {})

        # Normalize fields similar to map_token_digest_to_token_data
        creation_time = meta.get("creation_time")
        if creation_time is not None and not isinstance(creation_time, str):
            creation_time = str(creation_time)

        website = socials.get("website")
        if website is not None and not isinstance(website, (list, dict)):
            website = [website] if website else None

        history = TokenHistory(
            token_address=token_dict.get("address") or meta.get("address"),
            check_type=check_type,

            # Basic identification
            symbol=token_dict.get("symbol") or meta.get("symbol"),
            chain=token_dict.get("chain", "solana"),
            name=meta.get("name"),
            creator=meta.get("creator"),
            creation_time=creation_time,
            token_age_days=meta.get("token_age_days"),
            token_age_hours=meta.get("token_age_hours"),
            decimals=meta.get("decimals"),

            # URLs and misc
            image_url=meta.get("image_url"),
            dexscreener_url=meta.get("dexscreener_url"),
            metadata_uri=meta.get("metadata_uri"),

            # Market metrics
            price_usd=market.get("price_usd"),
            fdv=market.get("fdv"),
            market_cap=market.get("market_cap"),
            tx_24h=market.get("tx_24h"),
            volume_24h=market.get("volume_24h"),
            price_change_1h=market.get("price_change_1h"),
            price_change_6h=market.get("price_change_6h"),
            price_change_24h=market.get("price_change_24h"),
            buys_m5=market.get("buys_m5"),
            sells_m5=market.get("sells_m5"),
            buys_1h=market.get("buys_1h"),
            sells_1h=market.get("sells_1h"),
            buys_6h=market.get("buys_6h"),
            sells_6h=market.get("sells_6h"),
            buys_24h=market.get("buys_24h"),
            sells_24h=market.get("sells_24h"),
            buy_sell_ratio=market.get("buy_sell_ratio"),
            velocity_score=market.get("velocity_score"),
            momentum_index=market.get("momentum_index"),
            volatility_score=market.get("volatility_score"),
            buy_pressure_ratio=market.get("buy_pressure_ratio"),

            # Holder metrics
            total_holders=holders.get("total_holders"),
            top10_share=holders.get("top10_share"),
            top5_share=holders.get("top5_share"),
            creator_share=holders.get("creator_share"),
            insider_count=holders.get("insider_count"),
            insider_network_score=holders.get("insider_network_score"),
            gini_coefficient=holders.get("gini_coefficient"),
            holder_concentration_score=holders.get("holder_concentration_score"),
            is_risky_holder_distribution=holders.get("is_risky_holder_distribution"),

            # Liquidity
            total_liquidity_usd=liquidity.get("total_liquidity_usd"),
            stable_liquidity_usd=liquidity.get("stable_liquidity_usd"),
            lp_locked_usd=liquidity.get("lp_locked_usd"),
            lp_locked_pct=liquidity.get("lp_locked_pct"),
            liquidity_ratio=liquidity.get("liquidity_ratio"),
            locked_liquidity_ratio=liquidity.get("locked_liquidity_ratio"),
            pool_count=liquidity.get("pool_count"),
            multi_pool_presence=liquidity.get("multi_pool_presence"),

            # Socials
            has_twitter=socials.get("has_twitter"),
            twitter_url=socials.get("twitter_url"),
            website=website,
            has_discord=socials.get("has_discord"),
            has_telegram=socials.get("has_telegram"),
            has_website=socials.get("has_website"),
            has_header_image=socials.get("has_header_image"),
            social_presence_score=float(socials.get("social_presence_score", 0) if socials.get("social_presence_score") is not None else 0.0),

            # Flags
            rugged=flags.get("rugged"),
            has_freeze_authority=flags.get("has_freeze_authority"),
            has_mint_authority=flags.get("has_mint_authority"),
            risk_flags=flags.get("risk_flags"),
            verified_on_chain=flags.get("verified_on_chain"),
            revocation_risk_score=flags.get("revocation_risk_score"),
            rug_likelihood_flag=flags.get("rug_likelihood_flag"),
            trust_score=flags.get("trust_score"),
            has_verified_creator=flags.get("has_verified_creator"),
            has_kyc=flags.get("has_kyc"),

            # Derived
            liquidity_to_fdv_ratio=derived.get("liquidity_to_fdv_ratio"),
            holder_to_liquidity_ratio=derived.get("holder_to_liquidity_ratio"),
            activity_to_fdv_ratio=derived.get("activity_to_fdv_ratio"),
            stability_index=derived.get("stability_index"),
            decentralization_score=derived.get("decentralization_score"),
            survivability_score=derived.get("survivability_score"),
            pump_probability=derived.get("pump_probability"),
            liquidity_retention=derived.get("liquidity_retention"),
            insider_manipulation_risk=derived.get("insider_manipulation_risk"),

            # Score
            final_score=score.get("final_score"),
            classification=score.get("classification"),
            component_scores=score.get("component_scores"),
        )

        if not history.token_address:
            logger.warning("insert_token_history skipped: missing token address")
            return None

        db.add(history)
        db.commit()
        db.refresh(history)
        return history
    except Exception as e:
        db.rollback()
        logger.error(f"Error inserting token history: {e}", exc_info=True)
        return None

