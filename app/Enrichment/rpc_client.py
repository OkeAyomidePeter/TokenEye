"""
Asynchronous Helius RPC Client for Solana blockchain data enrichment.

This module provides a high-performance, fault-tolerant interface to Helius RPC endpoints
with automatic retries, exponential backoff, and batch processing capabilities.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

import httpx

from app.Services.rpc_manager import RpcManager

logger = logging.getLogger(__name__)



class Encoding(str, Enum):
    """Supported encoding formats for account data."""
    BASE58 = "base58"
    BASE64 = "base64"
    BASE64_ZSTD = "base64+zstd"
    JSON_PARSED = "jsonParsed"


class Commitment(str, Enum):
    """Commitment levels for transaction confirmation."""
    FINALIZED = "finalized"
    CONFIRMED = "confirmed"
    PROCESSED = "processed"


@dataclass
class RpcResponse:
    """Standardized RPC response wrapper."""
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    method: Optional[str] = None


class RpcError(Exception):
    """Custom exception for RPC-related errors."""
    pass


class HeliusRpcClient:
    """
    Asynchronous Helius RPC client with built-in retry logic and batch processing.
    
    Features:
    - Automatic endpoint failover via RpcManager
    - Exponential backoff for transient errors
    - Batch request processing
    - Request/response logging
    - Rate limit handling
    """
    
    def __init__(
        self,
        rpc_manager: Optional[RpcManager] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout: float = 30.0,
        pipeline: str = "pipeline_10m"
    ):
        """
        Initialize the Helius RPC client.
        
        Args:
            rpc_manager: RpcManager instance for endpoint management
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay between retries (seconds)
            timeout: Request timeout in seconds
            pipeline: Pipeline name for endpoint selection
        """
        self.rpc_manager = rpc_manager or RpcManager()
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self.pipeline = pipeline
        self._request_id = 0
    
    def _get_next_request_id(self) -> int:
        """Generate unique request ID for JSON-RPC calls."""
        self._request_id += 1
        return self._request_id
    
    async def _make_request(
        self,
        method: str,
        params: Optional[List[Any]] = None,
        endpoint: Optional[str] = None
    ) -> RpcResponse:
        """
        Make a single JSON-RPC request with retry logic.
        
        Args:
            method: RPC method name
            params: Method parameters
            endpoint: Optional specific endpoint (otherwise fetched from manager)
        
        Returns:
            RpcResponse object with result or error
        """
        if params is None:
            params = []
        
        payload = {
            "jsonrpc": "2.0",
            "id": self._get_next_request_id(),
            "method": method,
            "params": params
        }
        
        for attempt in range(self.max_retries):
            try:
                # Get endpoint if not provided
                if endpoint is None:
                    endpoint = await self.rpc_manager.get_endpoint(self.pipeline)
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    # Check for RPC-level errors
                    if "error" in result:
                        error = result["error"]
                        logger.error(
                            f"RPC error for {method}: {error.get('message', 'Unknown error')}"
                        )
                        return RpcResponse(
                            success=False,
                            error=error,
                            method=method
                        )
                    
                    # Successful response
                    return RpcResponse(
                        success=True,
                        data=result.get("result"),
                        method=method
                    )
            
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"HTTP error on attempt {attempt + 1}/{self.max_retries} "
                    f"for {method}: {e.response.status_code}"
                )
                
                # Rate limit handling
                if e.response.status_code == 429:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.info(f"Rate limited. Waiting {delay}s before retry...")
                    await asyncio.sleep(delay)
                    endpoint = None  # Force new endpoint on next attempt
                    continue
                
                # Server errors - retry with backoff
                if 500 <= e.response.status_code < 600:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    endpoint = None
                    continue
                
                # Client errors - don't retry
                return RpcResponse(
                    success=False,
                    error={"message": f"HTTP {e.response.status_code}", "code": e.response.status_code},
                    method=method
                )
            
            except httpx.RequestError as e:
                logger.warning(
                    f"Request error on attempt {attempt + 1}/{self.max_retries} "
                    f"for {method}: {str(e)}"
                )
                
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    endpoint = None
                    continue
            
            except Exception as e:
                logger.error(f"Unexpected error for {method}: {str(e)}", exc_info=True)
                return RpcResponse(
                    success=False,
                    error={"message": str(e), "code": -1},
                    method=method
                )
        
        # All retries exhausted
        return RpcResponse(
            success=False,
            error={"message": "Max retries exhausted", "code": -1},
            method=method
        )
    
    async def _make_batch_request(
        self,
        requests: List[Dict[str, Any]],
        endpoint: Optional[str] = None
    ) -> List[RpcResponse]:
        """
        Make a batch JSON-RPC request.
        
        Args:
            requests: List of request payloads
            endpoint: Optional specific endpoint
        
        Returns:
            List of RpcResponse objects
        """
        if not requests:
            return []
        
        # Assign unique IDs to requests
        for i, req in enumerate(requests):
            req["jsonrpc"] = "2.0"
            req["id"] = self._get_next_request_id()
        
        for attempt in range(self.max_retries):
            try:
                if endpoint is None:
                    endpoint = await self.rpc_manager.get_endpoint(self.pipeline)
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(endpoint, json=requests)
                    response.raise_for_status()
                    
                    results = response.json()
                    
                    # Parse batch results
                    responses = []
                    for result in results:
                        if "error" in result:
                            responses.append(RpcResponse(
                                success=False,
                                error=result["error"],
                                method=result.get("method", "batch")
                            ))
                        else:
                            responses.append(RpcResponse(
                                success=True,
                                data=result.get("result"),
                                method=result.get("method", "batch")
                            ))
                    
                    return responses
            
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning(
                    f"Batch request error on attempt {attempt + 1}/{self.max_retries}: {str(e)}"
                )
                
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    await asyncio.sleep(delay)
                    endpoint = None
                    continue
        
        # All retries failed - return error responses
        return [
            RpcResponse(
                success=False,
                error={"message": "Batch request failed", "code": -1},
                method="batch"
            )
            for _ in requests
        ]

    # -------------------------
    # Account Information Methods
    # -------------------------
    
    async def get_account_info(
        self,
        pubkey: str,
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED
    ) -> RpcResponse:
        """
        Get information about a specific account.
        
        Args:
            pubkey: Public key of the account
            encoding: Encoding format for account data
            commitment: Commitment level
        
        Returns:
            RpcResponse with account information
        """
        params = [
            pubkey,
            {
                "encoding": encoding.value,
                "commitment": commitment.value
            }
        ]
        
        return await self._make_request("getAccountInfo", params)
    
    async def get_multiple_accounts(
        self,
        pubkeys: List[str],
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED
    ) -> RpcResponse:
        """
        Get information for multiple accounts in a single request.
        
        Args:
            pubkeys: List of public keys (max 100)
            encoding: Encoding format for account data
            commitment: Commitment level
        
        Returns:
            RpcResponse with array of account information
        """
        if len(pubkeys) > 100:
            logger.warning(f"Requested {len(pubkeys)} accounts, but max is 100. Truncating.")
            pubkeys = pubkeys[:100]
        
        params = [
            pubkeys,
            {
                "encoding": encoding.value,
                "commitment": commitment.value
            }
        ]
        
        return await self._make_request("getMultipleAccounts", params)
    
    async def get_program_accounts(
        self,
        program_id: str,
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED,
        filters: Optional[List[Dict[str, Any]]] = None
    ) -> RpcResponse:
        """
        Get all accounts owned by a specific program.
        
        Args:
            program_id: Program public key
            encoding: Encoding format
            commitment: Commitment level
            filters: Optional filters for accounts
        
        Returns:
            RpcResponse with list of program accounts
        """
        config = {
            "encoding": encoding.value,
            "commitment": commitment.value
        }
        
        if filters:
            config["filters"] = filters
        
        params = [program_id, config]
        
        return await self._make_request("getProgramAccounts", params)
    
    # -------------------------
    # Transaction Methods
    # -------------------------
    
    async def get_transaction(
        self,
        signature: str,
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED,
        max_supported_transaction_version: int = 0
    ) -> RpcResponse:
        """
        Get details of a specific transaction.
        
        Args:
            signature: Transaction signature
            encoding: Encoding format
            commitment: Commitment level
            max_supported_transaction_version: Max transaction version to support
        
        Returns:
            RpcResponse with transaction details
        """
        params = [
            signature,
            {
                "encoding": encoding.value,
                "commitment": commitment.value,
                "maxSupportedTransactionVersion": max_supported_transaction_version
            }
        ]
        
        return await self._make_request("getTransaction", params)
    
    async def get_block(
        self,
        slot: int,
        encoding: Encoding = Encoding.JSON_PARSED,
        max_supported_transaction_version: int = 0,
        transaction_details: str = "full",
        rewards: bool = True
    ) -> RpcResponse:
        """
        Get information about a specific block.
        
        Args:
            slot: Slot number
            encoding: Encoding format
            max_supported_transaction_version: Max transaction version
            transaction_details: Level of transaction detail ("full", "accounts", "signatures", "none")
            rewards: Whether to include rewards
        
        Returns:
            RpcResponse with block information
        """
        params = [
            slot,
            {
                "encoding": encoding.value,
                "maxSupportedTransactionVersion": max_supported_transaction_version,
                "transactionDetails": transaction_details,
                "rewards": rewards
            }
        ]
        
        return await self._make_request("getBlock", params)
    
    # -------------------------
    # Network & Cluster Methods
    # -------------------------
    
    async def get_cluster_nodes(self) -> RpcResponse:
        """
        Get information about all nodes in the cluster.
        
        Returns:
            RpcResponse with cluster node information
        """
        return await self._make_request("getClusterNodes")
    
    async def get_health(self) -> RpcResponse:
        """
        Check the health status of the RPC node.
        
        Returns:
            RpcResponse with health status
        """
        return await self._make_request("getHealth")
    
    async def get_version(self) -> RpcResponse:
        """
        Get the current Solana version running on the node.
        
        Returns:
            RpcResponse with version information
        """
        return await self._make_request("getVersion")
    
    async def get_slot(self, commitment: Commitment = Commitment.FINALIZED) -> RpcResponse:
        """
        Get the current slot the node is processing.
        
        Args:
            commitment: Commitment level
        
        Returns:
            RpcResponse with current slot number
        """
        params = [{"commitment": commitment.value}]
        return await self._make_request("getSlot", params)
    
    # -------------------------
    # Token Methods
    # -------------------------
    
    async def get_token_accounts_by_owner(
        self,
        owner: str,
        mint: Optional[str] = None,
        program_id: Optional[str] = None,
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED
    ) -> RpcResponse:
        """
        Get all token accounts owned by an address.
        
        Args:
            owner: Owner public key
            mint: Optional mint address to filter by
            program_id: Optional token program ID (default: Token Program)
            encoding: Encoding format
            commitment: Commitment level
        
        Returns:
            RpcResponse with token accounts
        """
        config = {
            "encoding": encoding.value,
            "commitment": commitment.value
        }
        
        # Either mint or programId must be specified
        if mint:
            filter_config = {"mint": mint}
        elif program_id:
            filter_config = {"programId": program_id}
        else:
            # Default to Token Program
            filter_config = {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}
        
        params = [owner, filter_config, config]
        
        return await self._make_request("getTokenAccountsByOwner", params)
    
    async def get_token_supply(
        self,
        mint: str,
        commitment: Commitment = Commitment.FINALIZED
    ) -> RpcResponse:
        """
        Get the total supply of a token.
        
        Args:
            mint: Token mint address
            commitment: Commitment level
        
        Returns:
            RpcResponse with token supply information
        """
        params = [mint, {"commitment": commitment.value}]
        return await self._make_request("getTokenSupply", params)
    
    async def get_token_largest_accounts(
        self,
        mint: str,
        commitment: Commitment = Commitment.FINALIZED
    ) -> RpcResponse:
        """
        Get the largest token accounts for a specific mint.
        
        Args:
            mint: Token mint address
            commitment: Commitment level
        
        Returns:
            RpcResponse with largest token accounts
        """
        params = [mint, {"commitment": commitment.value}]
        return await self._make_request("getTokenLargestAccounts", params)
    
    # -------------------------
    # Compression Methods (State Compression / cNFTs)
    # -------------------------
    
    async def get_compressed_account(
        self,
        account_hash: str
    ) -> RpcResponse:
        """
        Get information about a compressed account.
        
        Args:
            account_hash: Hash of the compressed account
        
        Returns:
            RpcResponse with compressed account data
        """
        params = [account_hash]
        return await self._make_request("getCompressedAccount", params)
    
    async def get_compressed_token_accounts_by_owner(
        self,
        owner: str,
        mint: Optional[str] = None
    ) -> RpcResponse:
        """
        Get all compressed token accounts owned by an address.
        
        Args:
            owner: Owner public key
            mint: Optional mint address to filter by
        
        Returns:
            RpcResponse with compressed token accounts
        """
        config = {"owner": owner}
        if mint:
            config["mint"] = mint
        
        params = [config]
        return await self._make_request("getCompressedTokenAccountsByOwner", params)
    
    # -------------------------
    # Batch Processing Methods
    # -------------------------
    
    async def batch_get_account_info(
        self,
        pubkeys: List[str],
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED,
        batch_size: int = 100
    ) -> List[RpcResponse]:
        """
        Get account info for multiple accounts using optimal batching.
        
        Args:
            pubkeys: List of public keys
            encoding: Encoding format
            commitment: Commitment level
            batch_size: Maximum accounts per batch (max 100)
        
        Returns:
            List of RpcResponse objects
        """
        all_responses = []
        
        # Split into chunks of batch_size
        for i in range(0, len(pubkeys), batch_size):
            batch = pubkeys[i:i + batch_size]
            response = await self.get_multiple_accounts(batch, encoding, commitment)
            
            # Expand batch response into individual responses
            if response.success and response.data:
                accounts = response.data.get("value", [])
                for account in accounts:
                    all_responses.append(RpcResponse(
                        success=True,
                        data=account,
                        method="getAccountInfo"
                    ))
            else:
                # If batch failed, add error responses for all accounts in batch
                for _ in batch:
                    all_responses.append(response)
        
        return all_responses
    
    async def batch_get_transactions(
        self,
        signatures: List[str],
        encoding: Encoding = Encoding.JSON_PARSED,
        commitment: Commitment = Commitment.FINALIZED,
        max_concurrent: int = 10
    ) -> List[RpcResponse]:
        """
        Get multiple transactions concurrently.
        
        Args:
            signatures: List of transaction signatures
            encoding: Encoding format
            commitment: Commitment level
            max_concurrent: Maximum concurrent requests
        
        Returns:
            List of RpcResponse objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(sig: str) -> RpcResponse:
            async with semaphore:
                return await self.get_transaction(sig, encoding, commitment)
        
        tasks = [fetch_with_semaphore(sig) for sig in signatures]
        return await asyncio.gather(*tasks)
