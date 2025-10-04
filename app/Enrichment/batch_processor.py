"""
Batch processing utilities for efficient RPC data enrichment.

This module provides high-level batch processing capabilities for token enrichment,
account monitoring, and transaction analysis.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar
from dataclasses import dataclass
from collections import defaultdict

from app.Enrichment.rpc_client import HeliusRpcClient, RpcResponse, Encoding, Commitment

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class BatchResult:
    """Result container for batch operations."""
    successful: List[Any]
    failed: List[Dict[str, Any]]
    total: int
    success_rate: float


class BatchProcessor:
    """
    High-performance batch processor for RPC operations.
    
    Features:
    - Automatic batching and chunking
    - Concurrent request processing
    - Progress tracking
    - Error aggregation
    - Rate limit aware
    """
    
    def __init__(
        self,
        rpc_client: Optional[HeliusRpcClient] = None,
        batch_size: int = 100,
        max_concurrent: int = 10,
        retry_failed: bool = True
    ):
        """
        Initialize batch processor.
        
        Args:
            rpc_client: HeliusRpcClient instance
            batch_size: Number of items per batch
            max_concurrent: Maximum concurrent batch operations
            retry_failed: Whether to retry failed items
        """
        self.rpc_client = rpc_client or HeliusRpcClient()
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.retry_failed = retry_failed
    
    async def process_batch(
        self,
        items: List[T],
        process_func: Callable[[T], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchResult:
        """
        Process a batch of items with a given function.
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            progress_callback: Optional callback for progress updates
        
        Returns:
            BatchResult with successful and failed items
        """
        successful = []
        failed = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(idx: int, item: T) -> None:
            async with semaphore:
                try:
                    result = await process_func(item)
                    successful.append(result)
                except Exception as e:
                    logger.error(f"Failed to process item {idx}: {str(e)}")
                    failed.append({"index": idx, "item": item, "error": str(e)})
                
                if progress_callback:
                    progress_callback(len(successful) + len(failed), len(items))
        
        tasks = [process_with_semaphore(idx, item) for idx, item in enumerate(items)]
        await asyncio.gather(*tasks)
        
        total = len(items)
        success_rate = len(successful) / total if total > 0 else 0.0
        
        return BatchResult(
            successful=successful,
            failed=failed,
            total=total,
            success_rate=success_rate
        )
    
    async def enrich_token_accounts(
        self,
        token_addresses: List[str],
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED
    ) -> BatchResult:
        """
        Enrich multiple token accounts with RPC data.
        
        Args:
            token_addresses: List of token mint addresses
            encoding: Encoding format
            commitment: Commitment level
        
        Returns:
            BatchResult with enriched token data
        """
        logger.info(f"Enriching {len(token_addresses)} token accounts...")
        
        successful = []
        failed = []
        
        # Process in chunks of batch_size
        for i in range(0, len(token_addresses), self.batch_size):
            chunk = token_addresses[i:i + self.batch_size]
            
            responses = await self.rpc_client.batch_get_account_info(
                chunk,
                encoding=encoding,
                commitment=commitment
            )
            
            for addr, response in zip(chunk, responses):
                if response.success and response.data:
                    successful.append({
                        "address": addr,
                        "account_data": response.data
                    })
                else:
                    failed.append({
                        "address": addr,
                        "error": response.error
                    })
            
            logger.info(f"Processed {min(i + self.batch_size, len(token_addresses))}/{len(token_addresses)}")
        
        total = len(token_addresses)
        success_rate = len(successful) / total if total > 0 else 0.0
        
        logger.info(
            f"Enrichment complete: {len(successful)}/{total} successful "
            f"({success_rate:.1%})"
        )
        
        return BatchResult(
            successful=successful,
            failed=failed,
            total=total,
            success_rate=success_rate
        )
    
    async def get_token_holder_info(
        self,
        mint_address: str,
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED
    ) -> Dict[str, Any]:
        """
        Get comprehensive token holder information.
        
        Args:
            mint_address: Token mint address
            encoding: Encoding format
            commitment: Commitment level
        
        Returns:
            Dictionary with token supply, largest holders, and metadata
        """
        logger.info(f"Fetching holder info for {mint_address}")
        
        # Fetch supply, largest accounts, and mint account info concurrently
        supply_task = self.rpc_client.get_token_supply(mint_address, commitment)
        largest_task = self.rpc_client.get_token_largest_accounts(mint_address, commitment)
        mint_task = self.rpc_client.get_account_info(mint_address, encoding, commitment)
        
        supply_resp, largest_resp, mint_resp = await asyncio.gather(
            supply_task,
            largest_task,
            mint_task
        )
        
        result = {
            "mint_address": mint_address,
            "supply": None,
            "largest_holders": [],
            "mint_account": None,
            "errors": []
        }
        
        if supply_resp.success:
            result["supply"] = supply_resp.data
        else:
            result["errors"].append({"type": "supply", "error": supply_resp.error})
        
        if largest_resp.success:
            result["largest_holders"] = largest_resp.data.get("value", [])
        else:
            result["errors"].append({"type": "largest_holders", "error": largest_resp.error})
        
        if mint_resp.success:
            result["mint_account"] = mint_resp.data
        else:
            result["errors"].append({"type": "mint_account", "error": mint_resp.error})
        
        return result
    
    async def enrich_transactions(
        self,
        signatures: List[str],
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED
    ) -> BatchResult:
        """
        Enrich multiple transactions with full details.
        
        Args:
            signatures: List of transaction signatures
            encoding: Encoding format
            commitment: Commitment level
        
        Returns:
            BatchResult with enriched transaction data
        """
        logger.info(f"Enriching {len(signatures)} transactions...")
        
        responses = await self.rpc_client.batch_get_transactions(
            signatures,
            encoding=encoding,
            commitment=commitment,
            max_concurrent=self.max_concurrent
        )
        
        successful = []
        failed = []
        
        for sig, response in zip(signatures, responses):
            if response.success and response.data:
                successful.append({
                    "signature": sig,
                    "transaction": response.data
                })
            else:
                failed.append({
                    "signature": sig,
                    "error": response.error
                })
        
        total = len(signatures)
        success_rate = len(successful) / total if total > 0 else 0.0
        
        logger.info(
            f"Transaction enrichment complete: {len(successful)}/{total} successful "
            f"({success_rate:.1%})"
        )
        
        return BatchResult(
            successful=successful,
            failed=failed,
            total=total,
            success_rate=success_rate
        )
    
    async def get_program_token_accounts(
        self,
        program_id: str,
        filters: Optional[List[Dict[str, Any]]] = None,
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED
    ) -> Dict[str, Any]:
        """
        Get all token accounts for a specific program with optional filters.
        
        Args:
            program_id: Program public key
            filters: Optional account filters
            encoding: Encoding format
            commitment: Commitment level
        
        Returns:
            Dictionary with program accounts and metadata
        """
        logger.info(f"Fetching accounts for program {program_id}")
        
        response = await self.rpc_client.get_program_accounts(
            program_id,
            encoding=encoding,
            commitment=commitment,
            filters=filters
        )
        
        if not response.success:
            logger.error(f"Failed to fetch program accounts: {response.error}")
            return {
                "program_id": program_id,
                "accounts": [],
                "count": 0,
                "error": response.error
            }
        
        accounts = response.data or []
        
        return {
            "program_id": program_id,
            "accounts": accounts,
            "count": len(accounts),
            "error": None
        }
    
    async def monitor_accounts(
        self,
        account_addresses: List[str],
        interval_seconds: float = 10.0,
        max_iterations: Optional[int] = None,
        change_callback: Optional[Callable[[str, Dict, Dict], None]] = None
    ) -> None:
        """
        Monitor accounts for changes over time.
        
        Args:
            account_addresses: List of accounts to monitor
            interval_seconds: Polling interval in seconds
            max_iterations: Maximum number of polling iterations (None = infinite)
            change_callback: Callback function when changes detected
        """
        logger.info(f"Starting account monitor for {len(account_addresses)} accounts")
        
        previous_states = {}
        iteration = 0
        
        while max_iterations is None or iteration < max_iterations:
            try:
                responses = await self.rpc_client.batch_get_account_info(
                    account_addresses,
                    batch_size=self.batch_size
                )
                
                for addr, response in zip(account_addresses, responses):
                    if response.success and response.data:
                        current_state = response.data
                        previous_state = previous_states.get(addr)
                        
                        # Detect changes
                        if previous_state and current_state != previous_state:
                            logger.info(f"Change detected for account {addr}")
                            if change_callback:
                                await change_callback(addr, previous_state, current_state)
                        
                        previous_states[addr] = current_state
                
                iteration += 1
                await asyncio.sleep(interval_seconds)
            
            except asyncio.CancelledError:
                logger.info("Account monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error in account monitoring: {str(e)}", exc_info=True)
                await asyncio.sleep(interval_seconds)
    
    async def analyze_token_distribution(
        self,
        mint_address: str,
        top_n: int = 100
    ) -> Dict[str, Any]:
        """
        Analyze token holder distribution and concentration.
        
        Args:
            mint_address: Token mint address
            top_n: Number of top holders to analyze
        
        Returns:
            Dictionary with distribution metrics
        """
        logger.info(f"Analyzing token distribution for {mint_address}")
        
        # Get token supply and largest accounts
        holder_info = await self.get_token_holder_info(mint_address)
        
        if holder_info.get("errors"):
            logger.warning(f"Errors fetching holder info: {holder_info['errors']}")
        
        supply_data = holder_info.get("supply", {})
        total_supply = float(supply_data.get("value", {}).get("amount", 0)) if supply_data else 0
        
        largest_holders = holder_info.get("largest_holders", [])[:top_n]
        
        # Calculate distribution metrics
        holder_balances = [
            float(holder.get("amount", 0)) for holder in largest_holders
        ]
        
        if not holder_balances or total_supply == 0:
            return {
                "mint_address": mint_address,
                "total_supply": total_supply,
                "top_holders_count": 0,
                "concentration": {},
                "error": "Insufficient data"
            }
        
        # Concentration metrics
        top_1_concentration = (holder_balances[0] / total_supply * 100) if len(holder_balances) > 0 else 0
        top_5_concentration = (sum(holder_balances[:5]) / total_supply * 100) if len(holder_balances) >= 5 else 0
        top_10_concentration = (sum(holder_balances[:10]) / total_supply * 100) if len(holder_balances) >= 10 else 0
        
        return {
            "mint_address": mint_address,
            "total_supply": total_supply,
            "top_holders_count": len(largest_holders),
            "concentration": {
                "top_1_percent": round(top_1_concentration, 2),
                "top_5_percent": round(top_5_concentration, 2),
                "top_10_percent": round(top_10_concentration, 2),
            },
            "largest_holders": largest_holders,
            "gini_coefficient": self._calculate_gini(holder_balances)
        }
    
    @staticmethod
    def _calculate_gini(balances: List[float]) -> float:
        """
        Calculate Gini coefficient for token distribution.
        
        Args:
            balances: List of token balances
        
        Returns:
            Gini coefficient (0 = perfect equality, 1 = perfect inequality)
        """
        if not balances:
            return 0.0
        
        sorted_balances = sorted(balances)
        n = len(sorted_balances)
        cumsum = 0
        
        for i, balance in enumerate(sorted_balances):
            cumsum += (2 * (i + 1) - n - 1) * balance
        
        total = sum(sorted_balances)
        if total == 0:
            return 0.0
        
        return cumsum / (n * total)


class TokenEnricher:
    """
    Specialized enricher for token data from Dexscreener + RPC.
    
    Combines Dexscreener market data with on-chain RPC data for comprehensive
    token analysis.
    """
    
    def __init__(
        self,
        batch_processor: Optional[BatchProcessor] = None
    ):
        """
        Initialize token enricher.
        
        Args:
            batch_processor: BatchProcessor instance
        """
        self.batch_processor = batch_processor or BatchProcessor()
    
    async def enrich_dexscreener_tokens(
        self,
        parsed_tokens: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich Dexscreener tokens with on-chain RPC data.
        
        Args:
            parsed_tokens: List of parsed Dexscreener token data
        
        Returns:
            List of enriched tokens with on-chain data
        """
        logger.info(f"Enriching {len(parsed_tokens)} Dexscreener tokens with RPC data")
        
        # Extract token addresses
        token_addresses = []
        for token in parsed_tokens:
            base_addr = token.get("base_token", {}).get("address")
            if base_addr:
                token_addresses.append(base_addr)
        
        # Batch fetch account info
        account_result = await self.batch_processor.enrich_token_accounts(token_addresses)
        
        # Create address -> account data mapping
        account_map = {
            item["address"]: item["account_data"]
            for item in account_result.successful
        }
        
        # Enrich tokens with on-chain data
        enriched_tokens = []
        for token in parsed_tokens:
            base_addr = token.get("base_token", {}).get("address")
            
            enriched = {**token}  # Copy original data
            
            if base_addr and base_addr in account_map:
                enriched["on_chain_data"] = account_map[base_addr]
            else:
                enriched["on_chain_data"] = None
            
            enriched_tokens.append(enriched)
        
        logger.info(
            f"Enrichment complete: {len(account_result.successful)}/{len(token_addresses)} "
            f"accounts enriched"
        )
        
        return enriched_tokens
    
    async def get_comprehensive_token_data(
        self,
        mint_address: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive token data including distribution, holders, and metadata.
        
        Args:
            mint_address: Token mint address
        
        Returns:
            Dictionary with comprehensive token data
        """
        logger.info(f"Fetching comprehensive data for {mint_address}")
        
        # Fetch multiple data sources concurrently
        distribution_task = self.batch_processor.analyze_token_distribution(mint_address)
        holder_task = self.batch_processor.get_token_holder_info(mint_address)
        account_task = self.batch_processor.rpc_client.get_account_info(mint_address)
        
        distribution, holder_info, account_info = await asyncio.gather(
            distribution_task,
            holder_task,
            account_task
        )
        
        return {
            "mint_address": mint_address,
            "distribution_analysis": distribution,
            "holder_info": holder_info,
            "account_info": account_info.data if account_info.success else None,
            "timestamp": asyncio.get_event_loop().time()
        }
