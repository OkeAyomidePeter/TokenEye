# 🚀 Quick Start Guide - RPC Enrichment

## 🎯 What Does It Do?

The RPC Enrichment Module adds **on-chain verification and detailed holder analysis** to your token sniper bot by:

1. ✅ Verifying tokens actually exist on Solana blockchain
2. 📊 Fetching real holder data (supply, largest holders)
3. 🎲 Calculating concentration & distribution metrics  
4. ⚠️ Assessing token risk automatically
5. 💡 Providing comprehensive token analysis

## 🏃 Quick Test

### 1. Start the Server
```bash
python run.py
```

### 2. Test RPC Health
```bash
curl http://127.0.0.1:8000/sniper/health
```

Expected response:
```json
{
  "status": "healthy",
  "rpc_health": "ok",
  "rpc_version": {...},
  "current_slot": 123456789
}
```

### 3. Run Enhanced Pipeline
```bash
curl http://127.0.0.1:8000/sniper/start
```

Look for these new fields in the response:
- `rpc_enriched_count`: How many tokens were verified on-chain
- `statistics.on_chain_verified`: Number of verified tokens
- `statistics.verification_rate`: Percentage of successful verifications
- `tokens[].rpc_data`: On-chain account information
- `tokens[].on_chain_verified`: Boolean verification flag

### 4. Analyze Specific Token
```bash
curl http://127.0.0.1:8000/sniper/analyze/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
```

## 📊 Understanding the Response

### Pipeline Response (`/sniper/start`)

```json
{
  "status": "success",
  "raw_count": 68,                    // Tokens from Dexscreener
  "dex_enriched_count": 67,          // Enriched with market data
  "parsed_count": 67,                 // Parsed & normalized
  "rpc_enriched_count": 67,          // ✨ NEW: Enriched with RPC data
  
  "statistics": {
    "total_tokens": 67,
    "on_chain_verified": 45,         // ✨ NEW: Verified on blockchain
    "verification_rate": 67.16,       // ✨ NEW: Success rate
    "tokens_with_holder_info": 10,   // ✨ NEW: With detailed holder data
    "avg_market_cap": 779067.03,
    "price_range": {...}
  },
  
  "tokens": [
    {
      // Original Dexscreener data
      "base_token": {...},
      "price_usd": 0.000031,
      "market_cap": 31004.83,
      
      // ✨ NEW: RPC enrichment data
      "rpc_data": {
        "account_info": {...},       // Raw account data
        "lamports": 2039280,         // SOL balance in lamports
        "owner": "TokenkegQ...",     // Token program owner
        "executable": false,
        "rent_epoch": 361,
        
        // Optional: For high-value tokens
        "holder_info": {
          "supply": {...},
          "largest_holders": [...],
          "mint_account": {...}
        }
      },
      "on_chain_verified": true      // ✨ NEW: Verification flag
    }
  ]
}
```

### Analysis Response (`/sniper/analyze/{address}`)

```json
{
  "token_address": "...",
  
  "market_data": {
    // Dexscreener data
    "price_usd": 1.0,
    "market_cap": 1000000000,
    "volume": {...}
  },
  
  "supply": {
    "total": "1000000000000000",
    "ui_amount": "1000000000",
    "decimals": 6
  },
  
  "concentration": {                // ✨ Holder concentration
    "top_1_percent": 15.5,         // Top holder owns 15.5%
    "top_5_percent": 45.2,         // Top 5 own 45.2%
    "top_10_percent": 67.8         // Top 10 own 67.8%
  },
  
  "gini_coefficient": 0.72,        // ✨ Inequality measure (0-1)
  
  "top_holders": [                 // ✨ Top 10 holders
    {
      "address": "...",
      "amount": "100000000",
      "uiAmountString": "100"
    }
  ],
  
  "risk_assessment": {              // ✨ Automated risk scoring
    "risk_level": "MEDIUM",         // MINIMAL/LOW/MEDIUM/HIGH/CRITICAL
    "risk_score": 4,                // Out of 10
    "flags": [
      "CENTRALIZED: Top 10 holders own >75%"
    ],
    "recommendation": "MODERATE: Some risk factors present..."
  }
}
```

## 🎯 Key Metrics Explained

### Verification Rate
```
verification_rate = (on_chain_verified / total_tokens) * 100
```
- **High (>80%)**: Most tokens exist on-chain ✅
- **Medium (50-80%)**: Some tokens may be invalid ⚠️
- **Low (<50%)**: Many invalid addresses ❌

### Concentration Metrics
Percentage of supply held by top holders:
- **Top 1%**: Single largest holder
- **Top 5%**: Five largest holders combined
- **Top 10%**: Ten largest holders combined

**Interpretation:**
- **< 30%**: Well distributed ✅
- **30-60%**: Moderate concentration ⚠️
- **> 60%**: Highly concentrated ❌

### Gini Coefficient
Measure of inequality (0 = perfect equality, 1 = perfect inequality):
- **0.0 - 0.4**: Low inequality ✅
- **0.4 - 0.6**: Moderate inequality ⚠️
- **0.6 - 1.0**: High inequality ❌

### Risk Score (0-10)
Calculated based on:
- Holder concentration (+0-3 points)
- Distribution inequality (+0-2 points)
- Market metrics (+0-3 points)
- Liquidity factors (+0-2 points)

## 🔧 Configuration Check

### 1. Check if RPC keys are configured
```bash
# Check if .env file exists
cat .env | grep HELIUS

# Should see:
# HELIUS_API_KEY_10M=your-key
# HELIUS_BUFFER_1=your-key
# etc.
```

### 2. Check if config.yaml is set up
```bash
# Note: config.yaml is secured, check via health endpoint instead
curl http://127.0.0.1:8000/sniper/health
```

### 3. Check logs for errors
```bash
# In the terminal running the server, look for:
✅ "✓ RPC enriched X tokens"
❌ "No available endpoints after retries"
```

## ⚡ Performance Tuning

### For Faster Processing (More RPC Calls)
Edit `app/Routes/trigger.py`:
```python
# Line ~24
batch_processor = BatchProcessor(
    rpc_client=rpc_client,
    batch_size=100,      # Keep at 100 (RPC limit)
    max_concurrent=20    # ⬆️ Increase from 10 to 20
)
```

### For Rate Limit Issues (Fewer RPC Calls)
```python
batch_processor = BatchProcessor(
    rpc_client=rpc_client,
    batch_size=50,       # ⬇️ Reduce from 100
    max_concurrent=5     // ⬇️ Reduce from 10
)
```

### Selective Enrichment (Only High-Value Tokens)
Edit the `should_fetch_detailed_data()` function in `trigger.py`:
```python
def should_fetch_detailed_data(token: Dict[str, Any]) -> bool:
    market_cap = token.get("market_cap", 0) or 0
    volume_24h = token.get("volume", {}).get("h24", 0) or 0
    
    return (
        market_cap > 500_000 or   # ⬆️ Increase threshold
        volume_24h > 100_000      # ⬆️ Increase threshold
    )
```

## 🐛 Common Issues

### Issue: "No available endpoints after retries"
**Cause**: Invalid or missing Helius API keys

**Fix**:
1. Check `.env` file has valid keys
2. Test keys at https://dashboard.helius.dev
3. Verify `config.yaml` structure matches docs

### Issue: "verification_rate": 0
**Cause**: RPC calls failing or invalid token addresses

**Fix**:
1. Check `/sniper/health` endpoint
2. Look for errors in server logs
3. Verify token addresses are valid Solana pubkeys

### Issue: All tokens show "on_chain_verified": false
**Cause**: RPC enrichment step is failing silently

**Fix**:
1. Check server logs for error messages
2. Test individual token: `/sniper/analyze/{address}`
3. Verify RPC endpoint is responding

### Issue: Slow response times
**Cause**: Too many concurrent RPC calls or rate limiting

**Fix**:
1. Reduce `max_concurrent` to 5
2. Reduce `batch_size` to 50
3. Add more buffer keys to config

## 📈 Monitoring

### Watch for These Log Messages

✅ **Success:**
```
🚀 Starting sniper bot pipeline...
📡 Step 1: Fetching raw tokens...
✓ Fetched 68 raw tokens
💎 Step 2: Enriching with Dexscreener data...
✓ Dexscreener enriched: 67 tokens
📊 Step 3: Parsing Dexscreener data...
✓ Parsed 67 tokens
⛓️  Step 4: Enriching with on-chain RPC data...
  Fetching on-chain data for 67 tokens...
  Successfully fetched 45 on-chain accounts
✓ RPC enriched 67 tokens
✅ Pipeline complete!
```

❌ **Errors to Watch:**
```
❌ Error in RPC enrichment: ...
Unexpected error for getHealth: ...
Failed to fetch holder info for ...
```

## 🎓 Learning More

- **Full Documentation**: `app/Enrichment/README.md`
- **Code Examples**: `app/Enrichment/examples.py`
- **Implementation Details**: `RPC_ENRICHMENT_SUMMARY.md`

## 🤝 Support

If you encounter issues:
1. Check logs in terminal
2. Test `/sniper/health` endpoint
3. Review configuration files
4. Check Helius dashboard for API limits
5. Read error messages carefully - they're descriptive!

---

**That's it!** Your sniper bot now has on-chain verification and comprehensive token analysis. 🎉
