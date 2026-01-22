# TokenEye: Technical Architecture & System Breakdown

## Core Architecture

TokenEye is built as a modular, asynchronous data pipeline using **Python (FastAPI)** and **PostgreSQL**. It is designed for high throughput, handling complex on-chain queries and multi-source API enrichment in real-time.

## 1. The Data Pipeline (ETL Flow)

The system follows a 10-step execution cycle triggered via REST endpoints:

- **Ingestion (DataStream):** Fetches raw Solana token profiles and "boosted" assets from Dexscreener via a Cloudflare Worker proxy to bypass rate limits.
- **Enrichment Layer:**
  - **On-Chain Data:** Uses **Helius RPC** for high-speed batched requests to fetch mint data, holder counts, and account authorities.
  - **Security Audit:** Integrates with the **RugCheck API** to retrieve safety reports and identify risk flags (e.g., mint/freeze authority).
- **Digestion Layer:** A transformation engine that organizes over 70 raw data points into structured Pydantic models across 7 categories: Meta, Market, Holders, Liquidity, Socials, Flags, and Derived metrics.

## 2. Multi-Dimensional Scoring Engine

The heart of the project is a weighted ranking algorithm that computes a final score (0-100) based on six key dimensions:

- **Market Dynamics (35%):** Analysis of volume, price momentum, and volatility.
- **Liquidity Strength (20%):** Evaluation of pool depth, FDV ratios, and locked liquidity percentages.
- **Holder Distribution (15%):** Calculates the Gini coefficient and Top 10 holder concentration to detect "whale" manipulation.
- **Social Signal (10%):** Aggregates presence across Twitter, Telegram, and Discord.
- **Trust & Safety (10%):** Deducts points for technical "red flags" and increases weight for verified status.
- **Pump Probability (10%):** A derived predictive metric based on short-term momentum and liquidity ratios.

## 3. ChronoSniper: Historical Tracking System

Unlike most bots that forget a token after discovery, TokenEye implements a **ChronoSniper** module:

- **Snapshots:** Automatically re-evaluates high-scoring tokens at set intervals (1h, 3h, 6h, 1d, 1w, 1m).
- **Performance Validation:** Stores historical "snapshots" in PostgreSQL to track how the system's "High Potential" calls performed over time.
- **AI Readiness:** This historical dataset is specifically structured to eventually train Machine Learning models for predictive price action.

## 4. API & Integration Layer

- **FastAPI Backend:** Provides a RESTful interface for manual triggers (`/sniper/start`) and specific token analysis (`/sniper/analyze/{address}`).
- **Telegram Notifier:** An async notification service with:
  - **Smart Deduplication:** Prevents spamming multiple alerts for the same token.
  - **Intelligent Routing:** Segregates "Pro" (High Potential) and "Standard" alerts based on score thresholds.
  - **Rate Limiting:** Managed at both global and per-chat levels to comply with Telegram API constraints.

## Technical Stack

- **Language:** Python 3.11+ (Asynchronous using `asyncio`)
- **Web Framework:** FastAPI (Uvicorn)
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Data Validation:** Pydantic V2
- **External APIs:** Helius (Solana RPC), Dexscreener, RugCheck, Telegram Bot API
