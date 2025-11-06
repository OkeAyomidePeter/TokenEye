from sqlalchemy import Column, String, Float, Boolean, Integer, JSON , DateTime , func, ForeignKey
from app.Database.database import Base

class TokenData(Base):
    __tablename__ = "tokens_discovered"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    address = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String)
    chain = Column(String)
    name = Column(String)
    creator = Column(String, nullable=True)
    creation_time = Column(String)
    token_age_days = Column(Float)
    token_age_hours = Column(Float)
    decimals = Column(Integer, nullable=True)

    # URLs and misc
    image_url = Column(String)
    dexscreener_url = Column(String)
    metadata_uri = Column(String, nullable=True)

    # Market metrics
    price_usd = Column(Float)
    fdv = Column(Float)
    market_cap = Column(Float)
    tx_24h = Column(Integer)
    volume_24h = Column(Float)
    price_change_1h = Column(Float)
    price_change_6h = Column(Float)
    price_change_24h = Column(Float)
    buys_m5 = Column(Integer)
    sells_m5 = Column(Integer)
    buys_1h = Column(Integer)
    sells_1h = Column(Integer)
    buys_6h = Column(Integer)
    sells_6h = Column(Integer)
    buys_24h = Column(Integer)
    sells_24h = Column(Integer)
    buy_sell_ratio = Column(Float)
    velocity_score = Column(Float)
    momentum_index = Column(Float)
    volatility_score = Column(Float)
    buy_pressure_ratio = Column(Float)

    # Holder metrics
    total_holders = Column(Integer)
    top10_share = Column(Float)
    top5_share = Column(Float)
    creator_share = Column(Float)
    insider_count = Column(Integer)
    insider_network_score = Column(Float)
    gini_coefficient = Column(Float)
    holder_concentration_score = Column(Float)
    is_risky_holder_distribution = Column(Boolean)

    # Liquidity
    total_liquidity_usd = Column(Float)
    stable_liquidity_usd = Column(Float)
    lp_locked_usd = Column(Float)
    lp_locked_pct = Column(Float)
    liquidity_ratio = Column(Float)
    locked_liquidity_ratio = Column(Float)
    pool_count = Column(Integer)
    multi_pool_presence = Column(Boolean)

    # Socials
    has_twitter = Column(Boolean)
    twitter_url = Column(String)
    website = Column(JSON)
    has_discord = Column(Boolean)
    has_telegram = Column(Boolean)
    has_website = Column(Boolean)
    has_header_image = Column(Boolean)
    social_presence_score = Column(Float)

    # Flags
    rugged = Column(Boolean)
    has_freeze_authority = Column(Boolean)
    has_mint_authority = Column(Boolean)
    risk_flags = Column(JSON)
    verified_on_chain = Column(Boolean)
    revocation_risk_score = Column(Float)
    rug_likelihood_flag = Column(Boolean)
    trust_score = Column(Float)
    has_verified_creator = Column(Boolean)
    has_kyc = Column(Boolean)

    # Derived
    liquidity_to_fdv_ratio = Column(Float)
    holder_to_liquidity_ratio = Column(Float)
    activity_to_fdv_ratio = Column(Float)
    stability_index = Column(Float)
    decentralization_score = Column(Float)
    survivability_score = Column(Float)
    pump_probability = Column(Float)
    liquidity_retention = Column(Float)
    insider_manipulation_risk = Column(Float)

    # Score
    final_score = Column(Float)
    classification = Column(String)
    component_scores = Column(JSON)
    
    first_seen = Column(DateTime(timezone=True), server_default=func.now())


class TokenHistory(Base):
    __tablename__ = "token_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token_address = Column(String, ForeignKey("tokens_discovered.address"), index=True, nullable=False)
    check_type = Column(String, nullable=False)  # '1h', '3h', '6h', '1d', '1w', '1m', '3m'
    snapshot_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Snapshot of all TokenData (tokens_discovered) columns (excluding id/address/first_seen)
    # Basic identification
    symbol = Column(String)
    chain = Column(String)
    name = Column(String)
    creator = Column(String, nullable=True)
    creation_time = Column(String)
    token_age_days = Column(Float)
    token_age_hours = Column(Float)
    decimals = Column(Integer, nullable=True)

    # URLs and misc
    image_url = Column(String)
    dexscreener_url = Column(String)
    metadata_uri = Column(String, nullable=True)

    # Market metrics
    price_usd = Column(Float)
    fdv = Column(Float)
    market_cap = Column(Float)
    tx_24h = Column(Integer)
    volume_24h = Column(Float)
    price_change_1h = Column(Float)
    price_change_6h = Column(Float)
    price_change_24h = Column(Float)
    buys_m5 = Column(Integer)
    sells_m5 = Column(Integer)
    buys_1h = Column(Integer)
    sells_1h = Column(Integer)
    buys_6h = Column(Integer)
    sells_6h = Column(Integer)
    buys_24h = Column(Integer)
    sells_24h = Column(Integer)
    buy_sell_ratio = Column(Float)
    velocity_score = Column(Float)
    momentum_index = Column(Float)
    volatility_score = Column(Float)
    buy_pressure_ratio = Column(Float)

    # Holder metrics
    total_holders = Column(Integer)
    top10_share = Column(Float)
    top5_share = Column(Float)
    creator_share = Column(Float)
    insider_count = Column(Integer)
    insider_network_score = Column(Float)
    gini_coefficient = Column(Float)
    holder_concentration_score = Column(Float)
    is_risky_holder_distribution = Column(Boolean)

    # Liquidity
    total_liquidity_usd = Column(Float)
    stable_liquidity_usd = Column(Float)
    lp_locked_usd = Column(Float)
    lp_locked_pct = Column(Float)
    liquidity_ratio = Column(Float)
    locked_liquidity_ratio = Column(Float)
    pool_count = Column(Integer)
    multi_pool_presence = Column(Boolean)

    # Socials
    has_twitter = Column(Boolean)
    twitter_url = Column(String)
    website = Column(JSON)
    has_discord = Column(Boolean)
    has_telegram = Column(Boolean)
    has_website = Column(Boolean)
    has_header_image = Column(Boolean)
    social_presence_score = Column(Float)

    # Flags
    rugged = Column(Boolean)
    has_freeze_authority = Column(Boolean)
    has_mint_authority = Column(Boolean)
    risk_flags = Column(JSON)
    verified_on_chain = Column(Boolean)
    revocation_risk_score = Column(Float)
    rug_likelihood_flag = Column(Boolean)
    trust_score = Column(Float)
    has_verified_creator = Column(Boolean)
    has_kyc = Column(Boolean)

    # Derived
    liquidity_to_fdv_ratio = Column(Float)
    holder_to_liquidity_ratio = Column(Float)
    activity_to_fdv_ratio = Column(Float)
    stability_index = Column(Float)
    decentralization_score = Column(Float)
    survivability_score = Column(Float)
    pump_probability = Column(Float)
    liquidity_retention = Column(Float)
    insider_manipulation_risk = Column(Float)

    # Score
    final_score = Column(Float)
    classification = Column(String)
    component_scores = Column(JSON)


class TokenSchedule(Base):
    __tablename__ = "token_schedule"

    token_address = Column(String, ForeignKey("tokens_discovered.address"), primary_key=True)
    check_type = Column(String, primary_key=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    # Optional audit field
    # created_at = Column(DateTime(timezone=True), server_default=func.now())
