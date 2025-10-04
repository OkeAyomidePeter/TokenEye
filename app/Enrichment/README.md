# RPC Enrichment Module

Asynchronous, modular RPC enrichment system for Solana token data using Helius RPC endpoints.

## 📁 Module Structure

```
app/Enrichment/
├── __init__.py                     # Module exports
├── rpc_client.py                   # Core RPC client with retry logic
├── batch_processor.py              # Batch processing and token enrichment
├── rpc_utils.py                    # Utility functions for parsing/formatting
├── dexscreener_enrichment.py       # Dexscreener API integration
├── parser.py                       # Dexscreener data parser
├── examples.py                     # Usage examples
└── README.md                       # This file
```

## 🚀 Quick Start

### Basic RPC Client Usage

```python
from app.Enrichment import HeliusRpcClient, Encoding, Commitment

# Initialize client
client = HeliusRpcClient(pipeline="pipeline_10m")

# Get account information
response = await client.get_account_info(
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC mint
    encoding=Encoding.JSON_PARSED
)

if response.success:
    print(f"Account data: {response.data}")
else:
    print(f"Error: {response.error}")
```

### Batch Processing

```python
from app.Enrichment import BatchProcessor

# Initialize processor
processor = BatchProcessor(batch_size=100, max_concurrent=10)

# Enrich multiple token accounts
token_addresses = ["address1", "address2", "address3"]
result = await processor.enrich_token_accounts(token_addresses)

print(f"Success rate: {result.success_rate:.1%}")
print(f"Successful: {len(result.successful)}")
print(f"Failed: {len(result.failed)}")
```

### Token Enrichment

```python
from app.Enrichment import TokenEnricher

# Initialize enricher
enricher = TokenEnricher()

# Enrich Dexscreener tokens with on-chain data
dex_tokens = [...]  # Parsed Dexscreener tokens
enriched = await enricher.enrich_dexscreener_tokens(dex_tokens)

# Get comprehensive token data
comprehensive = await enricher.get_comprehensive_token_data(mint_address)
```

## 🔌 Available RPC Methods

### Account Methods
- `get_account_info(pubkey)` - Get account information
- `get_multiple_accounts(pubkeys)` - Batch get account info
- `get_program_accounts(program_id)` - Get all program accounts

### Token Methods
- `get_token_supply(mint)` - Get token supply
- `get_token_largest_accounts(mint)` - Get largest holders
- `get_token_accounts_by_owner(owner)` - Get token accounts by owner

### Transaction Methods
- `get_transaction(signature)` - Get transaction details
- `get_block(slot)` - Get block information

### Network Methods
- `get_health()` - Check node health
- `get_version()` - Get Solana version
- `get_slot()` - Get current slot
- `get_cluster_nodes()` - Get cluster node info

### Compression Methods
- `get_compressed_account(hash)` - Get compressed account
- `get_compressed_token_accounts_by_owner(owner)` - Get compressed token accounts

## 🎯 Integration with Sniper Pipeline

The RPC enrichment is integrated into the `/sniper/start` endpoint:

```
1. Fetch raw tokens from Dexscreener
2. Enrich with Dexscreener market data
3. Parse and normalize data
4. **Enrich with on-chain RPC data** ← New step
5. Return comprehensive token data
```

### API Endpoints

#### GET `/sniper/start`
Run complete sniper pipeline with RPC enrichment.

**Response:**
```json
{
  "status": "success",
  "raw_count": 68,
  "dex_enriched_count": 67,
  "parsed_count": 67,
  "rpc_enriched_count": 67,
  "statistics": {
    "total_tokens": 67,
    "on_chain_verified": 45,
    "verification_rate": 67.16,
    "avg_market_cap": 779067.03,
    "tokens_with_holder_info": 10
  },
  "tokens": [...]
}
```

#### GET `/sniper/analyze/{token_address}`
Deep analysis for a specific token.

**Example:**
```
GET /sniper/analyze/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
```

**Response:**
```json
{
  "token_address": "...",
  "market_data": {...},
  "supply": {...},
  "concentration": {
    "top_1_percent": 15.5,
    "top_5_percent": 45.2,
    "top_10_percent": 67.8
  },
  "gini_coefficient": 0.72,
  "top_holders": [...],
  "risk_assessment": {
    "risk_level": "MEDIUM",
    "risk_score": 4,
    "flags": ["CENTRALIZED: Top 10 holders own >75%"],
    "recommendation": "..."
  }
}
```

#### GET `/sniper/health`
Check RPC connection health.

## ⚙️ Configuration

RPC configuration is managed by `RpcManager` in `app/Services/rpc_manager.py`.

**config.yaml structure:**
```yaml
rpc:
  endpoint_template: "https://mainnet.helius-rpc.com/?api-key={api_key}"
  helius:
    keys:
      - name: pipeline_10m
        key: HELIUS_API_KEY_10M
      - name: pipeline_snapshots
        key: HELIUS_API_KEY_SNAPSHOTS
      - name: buffer_1
        key: HELIUS_BUFFER_1
      - name: buffer_2
        key: HELIUS_BUFFER_2
```

**Environment variables (.env):**
```env
HELIUS_API_KEY_10M=your-key-here
HELIUS_API_KEY_SNAPSHOTS=your-key-here
HELIUS_BUFFER_1=your-buffer-key-1
HELIUS_BUFFER_2=your-buffer-key-2
```

## 🔄 Error Handling & Retries

The system includes comprehensive error handling:

- **Exponential Backoff**: Automatically retries failed requests with increasing delays
- **Rate Limit Handling**: Detects 429 errors and implements backoff
- **Endpoint Failover**: Switches to backup RPC endpoints on failures
- **Graceful Degradation**: Returns partial data if some enrichments fail

### Retry Configuration

```python
client = HeliusRpcClient(
    max_retries=3,          # Max retry attempts
    base_delay=1.0,         # Base delay (seconds)
    max_delay=30.0,         # Max delay cap
    timeout=30.0            # Request timeout
)
```

## 📊 Token Distribution Analysis

Analyze token holder concentration and distribution:

```python
# Analyze distribution
distribution = await processor.analyze_token_distribution(
    mint_address,
    top_n=100  # Analyze top 100 holders
)

print(f"Top 1 holder: {distribution['concentration']['top_1_percent']}%")
print(f"Top 10 holders: {distribution['concentration']['top_10_percent']}%")
print(f"Gini coefficient: {distribution['gini_coefficient']}")
```

### Risk Assessment

Tokens are automatically assessed for risk based on:

- **Concentration**: Top holder percentages
- **Distribution**: Gini coefficient
- **Market Cap**: Total market capitalization
- **Volume**: Trading volume
- **Age**: Token/pair age

**Risk Levels:**
- `MINIMAL` (0-1 points)
- `LOW` (1-3 points)
- `MEDIUM` (3-5 points)
- `HIGH` (5-7 points)
- `CRITICAL` (7+ points)

## 🛠️ Utility Functions

### Parsing Functions

```python
from app.Enrichment import (
    parse_token_account,
    parse_mint_account,
    parse_transaction_instructions,
    extract_token_transfers
)

# Parse token account
account_info = parse_token_account(rpc_data)
print(f"Owner: {account_info['owner']}")
print(f"Balance: {account_info['token_amount']['ui_amount']}")

# Extract transfers from transaction
transfers = extract_token_transfers(tx_data)
for transfer in transfers:
    print(f"Mint: {transfer['mint']}, Change: {transfer['change']}")
```

### Calculation Functions

```python
from app.Enrichment import (
    calculate_token_amount,
    format_token_amount,
    calculate_concentration_ratio
)

# Convert raw amount to decimal
amount = calculate_token_amount("1000000000", decimals=9)  # 1.0

# Format for display
formatted = format_token_amount("1000000000", decimals=9, symbol="SOL")
# Output: "1 SOL"

# Calculate concentration
ratios = calculate_concentration_ratio(holder_balances, total_supply)
print(f"Top 10 holders: {ratios['top_10']}%")
```

### Validation Functions

```python
from app.Enrichment import (
    is_valid_pubkey,
    is_system_program,
    validate_account_data
)

# Validate pubkey format
if is_valid_pubkey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"):
    print("Valid Solana public key")

# Check if system program
if is_system_program(program_id):
    print("This is a system program")
```

## 📈 Performance Optimization

### Batch Size Configuration

Adjust batch sizes based on rate limits and performance needs:

```python
processor = BatchProcessor(
    batch_size=100,          # Items per RPC batch (max 100 for getMultipleAccounts)
    max_concurrent=10        # Max concurrent batches
)
```

### Selective Enrichment

For large datasets, enrich only high-value tokens:

```python
async def enrich_with_rpc_data(tokens):
    for token in tokens:
        # Basic enrichment for all
        basic_data = await get_account_info(token['address'])
        
        # Detailed enrichment only for valuable tokens
        if should_fetch_detailed_data(token):
            holder_info = await get_token_holder_info(token['address'])
```

## 🧪 Testing

Run the example script:

```bash
python -m app.Enrichment.examples
```

This will execute all example functions demonstrating the RPC enrichment capabilities.

## 🐛 Troubleshooting

### "No available endpoints after retries"

**Cause**: RPC endpoints are not responding or invalid API keys

**Solutions:**
1. Check `.env` file has valid Helius API keys
2. Verify `config.yaml` has correct endpoint template
3. Test endpoint health: `GET /sniper/health`
4. Check Helius dashboard for API key status/limits

### "Rate limit exceeded"

**Cause**: Too many requests to RPC endpoint

**Solutions:**
1. Increase `retry_delay` in RpcClient
2. Reduce `max_concurrent` in BatchProcessor
3. Add more buffer keys in config
4. Upgrade Helius plan for higher rate limits

### "Batch enrichment failures"

**Cause**: Some accounts don't exist or are invalid

**Solutions:**
1. Check `result.failed` list for details
2. Validate token addresses before enrichment
3. Use `is_valid_pubkey()` to filter addresses
4. Handle partial failures gracefully

## 📚 Additional Resources

- [Helius RPC Documentation](https://docs.helius.dev/solana-rpc-nodes/alpha-rpc-nodes)
- [Solana JSON-RPC API](https://docs.solana.com/api)
- [Dexscreener API](https://docs.dexscreener.com/)

## 🤝 Contributing

When adding new RPC methods:

1. Add method to `HeliusRpcClient` in `rpc_client.py`
2. Add helper function to `rpc_utils.py` if needed
3. Add example usage to `examples.py`
4. Update this README with documentation

## 📝 License

Part of TokenScout v2 - Token Sniper Bot
