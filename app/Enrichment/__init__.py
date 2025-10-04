# app/Enrichment/__init__.py

# Dexscreener enrichment
from .dexscreener_enrichment import fetch_dexscreener_data
from .parser import parse_dexscreener_batch

# RPC enrichment
from .rpc_client import (
    HeliusRpcClient,
    RpcResponse,
    RpcError,
    Encoding,
    Commitment
)

from .batch_processor import (
    BatchProcessor,
    BatchResult,
    TokenEnricher
)

from .rpc_utils import (
    parse_token_account,
    parse_mint_account,
    parse_transaction_instructions,
    extract_token_transfers,
    calculate_token_amount,
    format_token_amount,
    is_valid_pubkey,
    filter_token_accounts,
    aggregate_token_balances
)

__all__ = [
    # Dexscreener
    "fetch_dexscreener_data",
    "parse_dexscreener_batch",
    
    # RPC Client
    "HeliusRpcClient",
    "RpcResponse",
    "RpcError",
    "Encoding",
    "Commitment",
    
    # Batch Processing
    "BatchProcessor",
    "BatchResult",
    "TokenEnricher",
    
    # Utilities
    "parse_token_account",
    "parse_mint_account",
    "parse_transaction_instructions",
    "extract_token_transfers",
    "calculate_token_amount",
    "format_token_amount",
    "is_valid_pubkey",
    "filter_token_accounts",
    "aggregate_token_balances",
]

from .rugcheck import RugCheckClient, RugCheckError

