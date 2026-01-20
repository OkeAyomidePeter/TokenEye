# TokenEye 🔭

**Early Microcap Token Discovery System for Solana**

TokenEye is an automated pipeline that discovers, enriches, scores, and alerts on promising Solana tokens. It fetches trending tokens from Dexscreener, enriches them with on-chain data via Helius RPC and RugCheck, scores them using a multi-dimensional algorithm, stores them in PostgreSQL, and sends Telegram notifications for high-scoring tokens.

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Pipeline Flow](#pipeline-flow)
- [Project Structure](#project-structure)
- [Module Descriptions](#module-descriptions)
- [API Endpoints](#api-endpoints)
- [Scoring System](#scoring-system)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [Database Schema](#database-schema)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TokenEye Pipeline                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│   │  DataStream │───▶│ Enrichment  │───▶│  Digestion  │───▶│   Scoring   │  │
│   │ (Dexscreener│    │ (RPC/Rug)   │    │ (7 modules) │    │(6 dimensions│  │
│   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│          │                                                         │         │
│          │                                                         ▼         │
│          │    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│          └───▶│  Database   │◀───│   Routes    │◀───│  Notifier   │        │
│               │ (PostgreSQL)│    │ (FastAPI)   │    │ (Telegram)  │        │
│               └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Pipeline Flow

The main sniper pipeline (`/sniper/start`) executes these 10 steps:

| Step | Description                                                      | Module                               |
| ---- | ---------------------------------------------------------------- | ------------------------------------ |
| 1    | Fetch raw Solana tokens from Dexscreener (profiles, boosts, top) | `DataStream`                         |
| 2    | Enrich with Dexscreener market data (price, volume, liquidity)   | `Enrichment.fetch_dexscreener_data`  |
| 3    | Parse Dexscreener response into structured format                | `Enrichment.parse_dexscreener_batch` |
| 4    | Enrich with on-chain RPC data via Helius (supply, holders)       | `Enrichment.BatchProcessor`          |
| 5    | Enrich with RugCheck safety reports                              | `Enrichment.RugCheckClient`          |
| 6    | Digest into structured categories (meta, market, holders, etc.)  | `Digestion.TokenDigester`            |
| 7    | Validate with Pydantic models                                    | `DataModels.TokenDigest`             |
| 8    | Score tokens (0-100) across 6 dimensions                         | `Scoring.TokenScorer`                |
| 9    | Save to PostgreSQL database                                      | `Database.save_tokens_batch`         |
| 10   | Send Telegram notifications (pro/free channels)                  | `Notifier.send_token_notification`   |

---

## 📁 Project Structure

```
TokenEye/
├── run.py                  # Entry point: uvicorn server
├── config.yaml             # RPC provider configuration
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (secrets)
│
└── app/
    ├── main.py             # FastAPI app initialization
    ├── config.py           # Configuration loader
    │
    ├── DataStream/         # Token source fetching
    │   └── tokenstream.py  # Dexscreener API fetcher
    │
    ├── Enrichment/         # Data enrichment layer
    │   ├── batch_processor.py    # High-performance RPC batching
    │   ├── rpc_client.py         # Helius RPC client
    │   ├── rpc_utils.py          # RPC utilities
    │   ├── rugcheck.py           # RugCheck API client
    │   ├── parser.py             # Dexscreener response parser
    │   └── dexscreener_enrichment.py
    │
    ├── Digestion/          # Data structuring layer
    │   ├── digest.py       # Main TokenDigester orchestrator
    │   ├── meta_digest.py      # Token metadata (name, symbol, age)
    │   ├── market_digest.py    # Price, volume, momentum
    │   ├── holder_digest.py    # Holder distribution metrics
    │   ├── liquidity_digest.py # Liquidity pool analysis
    │   ├── social_digest.py    # Social presence (Twitter, Telegram)
    │   ├── flag_digest.py      # Risk flags (mint/freeze authority)
    │   └── derived_digest.py   # Computed metrics (Gini, survivability)
    │
    ├── Scoring/            # Token ranking system
    │   ├── token_scorer.py     # Main scorer (combines 6 dimensions)
    │   ├── market_scorer.py    # Volume, momentum, volatility
    │   ├── liquidity_scorer.py # Liquidity depth and ratios
    │   ├── holder_scorer.py    # Distribution and concentration
    │   ├── social_scorer.py    # Social media presence
    │   ├── flag_scorer.py      # Trust and risk flags
    │   └── derived_scorer.py   # Pump probability, survivability
    │
    ├── DataModels/         # Pydantic validation models
    │   ├── token.py        # TokenDigest, DigestData
    │   ├── meta.py         # MetaDigest model
    │   ├── market.py       # MarketDigest model
    │   ├── holder.py       # HolderDigest model
    │   ├── liquidity.py    # LiquidityDigest model
    │   ├── social.py       # SocialDigest model
    │   ├── flag.py         # FlagDigest model
    │   └── derived.py      # DerivedDigest model
    │
    ├── Database/           # PostgreSQL persistence
    │   ├── database.py     # SQLAlchemy engine/session
    │   ├── models.py       # ORM models (TokenData, TokenHistory)
    │   └── repository.py   # CRUD operations
    │
    ├── Routes/             # FastAPI endpoints
    │   ├── trigger.py      # /sniper/start, /sniper/analyze/{address}
    │   └── chronotrigger.py # /chronosniper/start (scheduled re-checks)
    │
    ├── TokenChronoData/    # Scheduled re-enrichment
    │   └── processor.py    # Process due schedules, save history
    │
    ├── Notifier/           # Telegram alerts
    │   ├── telegram.py         # Bot client, rate limiting, dedup
    │   └── message_composer.py # Message formatting
    │
    ├── Services/           # Shared services
    │   └── rpc_manager.py  # RPC key rotation
    │
    └── Logging/            # Logging configuration
        └── (logging setup)
```

---

## 📦 Module Descriptions

### DataStream

Fetches trending Solana tokens from Dexscreener via a Cloudflare Worker proxy (to bypass rate limits):

- `fetch_token_profiles()` - Latest token profiles
- `fetch_token_boosts()` - Boosted tokens
- `fetch_top_tokens()` - Top performing tokens
- `fetch_solana_tokens()` - Combined, deduplicated Solana tokens

### Enrichment

Enriches raw token data with multiple sources:

| Component                | Source       | Data Provided                    |
| ------------------------ | ------------ | -------------------------------- |
| `HeliusRpcClient`        | Helius RPC   | Supply, holders, account data    |
| `BatchProcessor`         | Helius RPC   | Batched token account enrichment |
| `TokenEnricher`          | Combined     | Comprehensive token data         |
| `RugCheckClient`         | RugCheck API | Safety reports, risk flags       |
| `fetch_dexscreener_data` | Dexscreener  | Price, volume, liquidity         |

### Digestion

Transforms enriched data into 7 structured categories:

| Digest        | Key Metrics                                      |
| ------------- | ------------------------------------------------ |
| **Meta**      | Symbol, name, age, creator, decimals, image      |
| **Market**    | Price, FDV, volume, buy/sell ratios, momentum    |
| **Holders**   | Total holders, top10 share, Gini coefficient     |
| **Liquidity** | Total USD, locked %, pool count                  |
| **Socials**   | Twitter, Discord, Telegram, website              |
| **Flags**     | Freeze/mint authority, rug likelihood            |
| **Derived**   | Survivability, pump probability, stability index |

### Scoring

Multi-dimensional scoring with configurable weights:

| Dimension           | Weight | Factors Considered              |
| ------------------- | ------ | ------------------------------- |
| Market Dynamics     | 35%    | Volume, momentum, volatility    |
| Liquidity Strength  | 20%    | Depth, FDV ratio, lock %        |
| Holder Distribution | 15%    | Decentralization, concentration |
| Social Presence     | 10%    | Platform count, engagement      |
| Trust Score         | 10%    | Risk flags, verified status     |
| Pump Probability    | 10%    | Derived metrics                 |

**Classification:**

- 70+ → `high potential`
- 40-70 → `moderate`
- <40 → `low potential`

### TokenChronoData

Scheduled re-enrichment system for tracking token evolution:

- Processes due schedules (1h, 3h, 6h, 1d, 1w, 1m intervals)
- Re-enriches tokens and stores snapshots in `token_history`
- Enables performance tracking over time

### Notifier

Telegram notification system with:

- Rate limiting (1.5s global, 1.5s per-chat)
- Deduplication (5-minute window)
- Pro vs Free channel routing based on score threshold
- Photo attachments with token images

---

## 🌐 API Endpoints

### Sniper Routes (`/sniper`)

| Endpoint                          | Method | Description                 |
| --------------------------------- | ------ | --------------------------- |
| `/sniper/start`                   | GET    | Run full discovery pipeline |
| `/sniper/analyze/{token_address}` | GET    | Analyze a specific token    |

### ChronoSniper Routes (`/chronosniper`)

| Endpoint                       | Method | Description                     |
| ------------------------------ | ------ | ------------------------------- |
| `/chronosniper/start?limit=50` | GET    | Process due scheduled re-checks |

### Health

| Endpoint | Method | Description  |
| -------- | ------ | ------------ |
| `/`      | GET    | Health check |

---

## ⚙️ Configuration

### Environment Variables (`.env`)

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALERT_CHANNEL=-100xxxxxxxxxx      # Free tier channel
TELEGRAM_PRO_ALERT_CHANNEL=-100xxxxxxxxxx  # Pro channel

# Helius RPC Keys
HELIUS_API_KEY_1=your_key_1
HELIUS_API_KEY_2=your_key_2
HELIUS_API_KEY_3=your_key_3
HELIUS_API_KEY_4=your_key_4
```

### Database (`app/config.py`)

```python
DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/tokenscout"
```

### RPC Keys (`config.yaml`)

```yaml
rpc:
  helius:
    keys:
      - name: "pipeline_10m"
        key: "${HELIUS_API_KEY_1}"
      # ... more keys for different pipelines
```

## 🚀 Deployment

For production deployment on a single EC2 instance, refer to [DEPLOYMENT.md](DEPLOYMENT.md).

## 💻 Local Setup

```bash
# 1. Setup virtual environment with uv
uv venv
source .venv/bin/activate

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Set up PostgreSQL database
# Create database: tokenscout

# 4. Configure .env file
cp .env.example .env
# Edit .env with your credentials

# 5. Run the server
python run.py

# Server runs at http://127.0.0.1:8000
```

### Trigger Pipeline

```bash
# Run full sniper pipeline
curl http://localhost:8000/sniper/start

# Analyze specific token
curl http://localhost:8000/sniper/analyze/YOUR_TOKEN_ADDRESS

# Run scheduled re-checks
curl http://localhost:8000/chronosniper/start?limit=50
```

---

## 🗄️ Database Schema

### `tokens_discovered`

Main token table storing latest enriched data for each discovered token.

| Column           | Type     | Description                 |
| ---------------- | -------- | --------------------------- |
| `address`        | String   | Token mint address (unique) |
| `symbol`         | String   | Token symbol                |
| `price_usd`      | Float    | Current price               |
| `fdv`            | Float    | Fully diluted valuation     |
| `total_holders`  | Integer  | Holder count                |
| `final_score`    | Float    | Computed score (0-100)      |
| `classification` | String   | high/moderate/low potential |
| `first_seen`     | DateTime | Discovery timestamp         |
| ...              | ...      | 70+ metrics                 |

### `token_history`

Snapshots for tracking token evolution over time.

| Column          | Type     | Description             |
| --------------- | -------- | ----------------------- |
| `token_address` | String   | FK to tokens_discovered |
| `check_type`    | String   | 1h, 3h, 6h, 1d, 1w, 1m  |
| `snapshot_time` | DateTime | When snapshot was taken |
| ...             | ...      | All TokenData columns   |

### `token_schedule`

Scheduler for future re-checks.

| Column          | Type     | Description             |
| --------------- | -------- | ----------------------- |
| `token_address` | String   | FK to tokens_discovered |
| `check_type`    | String   | Check interval          |
| `scheduled_for` | DateTime | When to run             |
| `processed`     | Boolean  | Already processed?      |

---

## 📊 Key Metrics Explained

| Metric                | Calculation                 | Meaning                     |
| --------------------- | --------------------------- | --------------------------- |
| `buy_sell_ratio`      | buys / sells                | >1 = buying pressure        |
| `momentum_index`      | Price changes weighted      | Upward/downward momentum    |
| `gini_coefficient`    | Holder balance distribution | 0 = equal, 1 = concentrated |
| `survivability_score` | Liquidity + holders + age   | Long-term survival chance   |
| `pump_probability`    | Volume + momentum + whales  | Short-term pump chance      |
| `rug_likelihood_flag` | Risk flags + concentration  | Rug pull risk               |

---

## 🔧 External Dependencies

| Service         | Purpose        | Rate Limits                 |
| --------------- | -------------- | --------------------------- |
| **Dexscreener** | Market data    | Via Cloudflare Worker proxy |
| **Helius**      | On-chain RPC   | 10M credits/month (paid)    |
| **RugCheck**    | Safety reports | 1 req/sec recommended       |
| **Telegram**    | Notifications  | 30 msg/sec global           |

---

## 📝 License

Internal project - TokenScout Sniper Bot
