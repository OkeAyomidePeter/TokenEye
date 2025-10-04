"""
Utility functions for RPC data enrichment and transformation.

This module provides helper functions for parsing, transforming, and analyzing
RPC responses from Helius/Solana endpoints.
"""

import base64
import json
import logging
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal

logger = logging.getLogger(__name__)


# -------------------------
# Account Data Parsers
# -------------------------

def parse_token_account(account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse token account data from RPC response.
    
    Args:
        account_data: Raw account data from RPC
    
    Returns:
        Parsed token account info or None if not a token account
    """
    if not account_data or "parsed" not in account_data:
        return None
    
    try:
        parsed = account_data["parsed"]
        if parsed.get("type") != "account":
            return None
        
        info = parsed.get("info", {})
        
        return {
            "mint": info.get("mint"),
            "owner": info.get("owner"),
            "token_amount": {
                "amount": info.get("tokenAmount", {}).get("amount"),
                "decimals": info.get("tokenAmount", {}).get("decimals"),
                "ui_amount": info.get("tokenAmount", {}).get("uiAmount"),
                "ui_amount_string": info.get("tokenAmount", {}).get("uiAmountString"),
            },
            "state": info.get("state"),
            "is_native": info.get("isNative", False),
            "delegate": info.get("delegate"),
            "delegated_amount": info.get("delegatedAmount", {}).get("amount"),
            "close_authority": info.get("closeAuthority"),
        }
    except Exception as e:
        logger.error(f"Error parsing token account: {str(e)}")
        return None


def parse_mint_account(account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse mint account data from RPC response.
    
    Args:
        account_data: Raw account data from RPC
    
    Returns:
        Parsed mint info or None if not a mint account
    """
    if not account_data or "parsed" not in account_data:
        return None
    
    try:
        parsed = account_data["parsed"]
        if parsed.get("type") != "mint":
            return None
        
        info = parsed.get("info", {})
        
        return {
            "mint_authority": info.get("mintAuthority"),
            "supply": info.get("supply"),
            "decimals": info.get("decimals"),
            "is_initialized": info.get("isInitialized", False),
            "freeze_authority": info.get("freezeAuthority"),
        }
    except Exception as e:
        logger.error(f"Error parsing mint account: {str(e)}")
        return None


def decode_base64_data(encoded_data: str) -> Optional[bytes]:
    """
    Decode base64-encoded account data.
    
    Args:
        encoded_data: Base64 encoded string
    
    Returns:
        Decoded bytes or None on error
    """
    try:
        return base64.b64decode(encoded_data)
    except Exception as e:
        logger.error(f"Error decoding base64 data: {str(e)}")
        return None


def extract_account_owner(account_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract owner/program from account data.
    
    Args:
        account_data: Raw account data
    
    Returns:
        Owner public key or None
    """
    try:
        return account_data.get("value", {}).get("owner")
    except Exception:
        return None


# -------------------------
# Transaction Parsers
# -------------------------

def parse_transaction_instructions(tx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse instructions from transaction data.
    
    Args:
        tx_data: Transaction data from RPC
    
    Returns:
        List of parsed instructions
    """
    if not tx_data:
        return []
    
    try:
        transaction = tx_data.get("transaction", {})
        message = transaction.get("message", {})
        instructions = message.get("instructions", [])
        
        parsed_instructions = []
        for instruction in instructions:
            parsed = {
                "program": instruction.get("program"),
                "program_id": instruction.get("programId"),
                "accounts": instruction.get("accounts", []),
                "data": instruction.get("data"),
                "parsed": instruction.get("parsed"),
            }
            parsed_instructions.append(parsed)
        
        return parsed_instructions
    except Exception as e:
        logger.error(f"Error parsing transaction instructions: {str(e)}")
        return []


def extract_token_transfers(tx_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract token transfers from transaction data.
    
    Args:
        tx_data: Transaction data from RPC
    
    Returns:
        List of token transfers
    """
    transfers = []
    
    try:
        meta = tx_data.get("meta", {})
        token_balances_pre = meta.get("preTokenBalances", [])
        token_balances_post = meta.get("postTokenBalances", [])
        
        # Create mapping by account index and mint
        pre_map = {
            (tb.get("accountIndex"), tb.get("mint")): tb.get("uiTokenAmount", {})
            for tb in token_balances_pre
        }
        
        for post_balance in token_balances_post:
            account_idx = post_balance.get("accountIndex")
            mint = post_balance.get("mint")
            post_amount = post_balance.get("uiTokenAmount", {})
            
            key = (account_idx, mint)
            pre_amount = pre_map.get(key, {})
            
            pre_ui = float(pre_amount.get("uiAmount", 0) or 0)
            post_ui = float(post_amount.get("uiAmount", 0) or 0)
            
            if pre_ui != post_ui:
                transfers.append({
                    "account_index": account_idx,
                    "mint": mint,
                    "pre_balance": pre_ui,
                    "post_balance": post_ui,
                    "change": post_ui - pre_ui,
                    "decimals": post_amount.get("decimals"),
                })
        
        return transfers
    except Exception as e:
        logger.error(f"Error extracting token transfers: {str(e)}")
        return []


def get_transaction_fee(tx_data: Dict[str, Any]) -> Optional[int]:
    """
    Extract transaction fee in lamports.
    
    Args:
        tx_data: Transaction data from RPC
    
    Returns:
        Fee in lamports or None
    """
    try:
        return tx_data.get("meta", {}).get("fee")
    except Exception:
        return None


def get_transaction_status(tx_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract transaction execution status.
    
    Args:
        tx_data: Transaction data from RPC
    
    Returns:
        Status information
    """
    try:
        meta = tx_data.get("meta", {})
        err = meta.get("err")
        
        return {
            "success": err is None,
            "error": err,
            "compute_units_consumed": meta.get("computeUnitsConsumed"),
            "log_messages": meta.get("logMessages", []),
        }
    except Exception as e:
        logger.error(f"Error getting transaction status: {str(e)}")
        return {"success": False, "error": str(e)}


# -------------------------
# Token Calculations
# -------------------------

def calculate_token_amount(
    raw_amount: Union[str, int],
    decimals: int
) -> Decimal:
    """
    Convert raw token amount to decimal representation.
    
    Args:
        raw_amount: Raw token amount (smallest unit)
        decimals: Token decimals
    
    Returns:
        Decimal representation of amount
    """
    try:
        amount = Decimal(str(raw_amount))
        return amount / Decimal(10 ** decimals)
    except Exception as e:
        logger.error(f"Error calculating token amount: {str(e)}")
        return Decimal(0)


def format_token_amount(
    raw_amount: Union[str, int],
    decimals: int,
    symbol: Optional[str] = None
) -> str:
    """
    Format token amount for display.
    
    Args:
        raw_amount: Raw token amount
        decimals: Token decimals
        symbol: Optional token symbol
    
    Returns:
        Formatted string
    """
    amount = calculate_token_amount(raw_amount, decimals)
    formatted = f"{amount:,.{min(decimals, 6)}f}".rstrip('0').rstrip('.')
    
    if symbol:
        return f"{formatted} {symbol}"
    return formatted


def calculate_concentration_ratio(
    holder_amounts: List[float],
    total_supply: float
) -> Dict[str, float]:
    """
    Calculate holder concentration ratios.
    
    Args:
        holder_amounts: List of holder balances (sorted descending)
        total_supply: Total token supply
    
    Returns:
        Dictionary with concentration metrics
    """
    if not holder_amounts or total_supply == 0:
        return {
            "top_1": 0.0,
            "top_5": 0.0,
            "top_10": 0.0,
            "top_20": 0.0,
        }
    
    def calc_percent(n: int) -> float:
        if len(holder_amounts) < n:
            return sum(holder_amounts) / total_supply * 100
        return sum(holder_amounts[:n]) / total_supply * 100
    
    return {
        "top_1": round(calc_percent(1), 2),
        "top_5": round(calc_percent(5), 2),
        "top_10": round(calc_percent(10), 2),
        "top_20": round(calc_percent(20), 2),
    }


# -------------------------
# Data Validation
# -------------------------

def is_valid_pubkey(pubkey: str) -> bool:
    """
    Validate Solana public key format.
    
    Args:
        pubkey: Public key string
    
    Returns:
        True if valid format
    """
    if not pubkey or not isinstance(pubkey, str):
        return False
    
    # Solana pubkeys are base58 encoded, typically 32-44 characters
    if len(pubkey) < 32 or len(pubkey) > 44:
        return False
    
    # Check for valid base58 characters
    valid_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
    return all(c in valid_chars for c in pubkey)


def is_system_program(program_id: str) -> bool:
    """
    Check if program ID is a known system program.
    
    Args:
        program_id: Program public key
    
    Returns:
        True if system program
    """
    system_programs = {
        "11111111111111111111111111111111",  # System Program
        "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token Program
        "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",  # Token-2022 Program
        "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",  # Associated Token Program
        "Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo",  # Memo Program
        "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr",  # Memo Program v2
    }
    return program_id in system_programs


def validate_account_data(account_data: Dict[str, Any]) -> bool:
    """
    Validate that account data has expected structure.
    
    Args:
        account_data: Account data from RPC
    
    Returns:
        True if valid structure
    """
    if not account_data:
        return False
    
    value = account_data.get("value")
    if value is None:
        return False
    
    # Check for required fields
    required_fields = ["data", "executable", "lamports", "owner", "rentEpoch"]
    return all(field in value for field in required_fields)


# -------------------------
# Filtering Helpers
# -------------------------

def filter_token_accounts(
    accounts: List[Dict[str, Any]],
    min_balance: Optional[float] = None,
    mint_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter token accounts based on criteria.
    
    Args:
        accounts: List of token accounts
        min_balance: Minimum balance filter
        mint_filter: Specific mint to filter by
    
    Returns:
        Filtered list of accounts
    """
    filtered = accounts
    
    if mint_filter:
        filtered = [
            acc for acc in filtered
            if acc.get("mint") == mint_filter
        ]
    
    if min_balance is not None:
        filtered = [
            acc for acc in filtered
            if acc.get("token_amount", {}).get("ui_amount", 0) >= min_balance
        ]
    
    return filtered


def filter_recent_transactions(
    transactions: List[Dict[str, Any]],
    max_age_slots: Optional[int] = None,
    require_success: bool = True
) -> List[Dict[str, Any]]:
    """
    Filter transactions based on recency and success.
    
    Args:
        transactions: List of transactions
        max_age_slots: Maximum age in slots
        require_success: Only include successful transactions
    
    Returns:
        Filtered list of transactions
    """
    filtered = transactions
    
    if require_success:
        filtered = [
            tx for tx in filtered
            if tx.get("meta", {}).get("err") is None
        ]
    
    if max_age_slots is not None:
        # This would require current slot information
        # Implementation depends on having slot context
        pass
    
    return filtered


# -------------------------
# Aggregation Helpers
# -------------------------

def aggregate_token_balances(
    accounts: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate token balances by mint.
    
    Args:
        accounts: List of token accounts
    
    Returns:
        Dictionary mapping mint -> total balance
    """
    balances = {}
    
    for account in accounts:
        mint = account.get("mint")
        if not mint:
            continue
        
        amount = account.get("token_amount", {}).get("ui_amount", 0) or 0
        
        if mint in balances:
            balances[mint] += amount
        else:
            balances[mint] = amount
    
    return balances


def summarize_transaction_activity(
    transactions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Summarize transaction activity metrics.
    
    Args:
        transactions: List of transactions
    
    Returns:
        Summary statistics
    """
    if not transactions:
        return {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "total_fees": 0,
            "success_rate": 0.0,
        }
    
    successful = sum(1 for tx in transactions if tx.get("meta", {}).get("err") is None)
    failed = len(transactions) - successful
    total_fees = sum(
        tx.get("meta", {}).get("fee", 0) or 0
        for tx in transactions
    )
    
    return {
        "total": len(transactions),
        "successful": successful,
        "failed": failed,
        "total_fees": total_fees,
        "success_rate": (successful / len(transactions) * 100) if transactions else 0.0,
        "avg_fee": total_fees / len(transactions) if transactions else 0,
    }


# -------------------------
# Export Helpers
# -------------------------

def format_for_export(
    data: Dict[str, Any],
    format_type: str = "json"
) -> str:
    """
    Format enriched data for export.
    
    Args:
        data: Data to export
        format_type: Export format ("json", "csv")
    
    Returns:
        Formatted string
    """
    if format_type == "json":
        return json.dumps(data, indent=2, default=str)
    elif format_type == "csv":
        # Simple CSV conversion for flat data
        if isinstance(data, dict):
            headers = ",".join(str(k) for k in data.keys())
            values = ",".join(str(v) for v in data.values())
            return f"{headers}\n{values}"
        return str(data)
    else:
        return str(data)
