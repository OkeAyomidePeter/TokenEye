"""
Usage examples for the RPC enrichment module.

This file demonstrates how to use the HeliusRpcClient, BatchProcessor,
and TokenEnricher for various token enrichment tasks.
"""

import asyncio
import logging
from typing import List, Dict, Any

from app.Enrichment import (
    HeliusRpcClient,
    BatchProcessor,
    TokenEnricher,
    Encoding,
    Commitment,
    parse_token_account,
    format_token_amount
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# -------------------------
# Example 1: Basic RPC Client Usage
# -------------------------

async def example_basic_rpc_usage():
    """Demonstrate basic RPC client operations."""
    logger.info("=== Example 1: Basic RPC Client Usage ===")
    
    # Initialize client
    client = HeliusRpcClient(pipeline="pipeline_10m")
    
    # Example token mint address (USDC)
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # 1. Get account info
    account_response = await client.get_account_info(usdc_mint)
    if account_response.success:
        logger.info(f"✓ Retrieved account info for {usdc_mint}")
        logger.info(f"  Owner: {account_response.data.get('value', {}).get('owner')}")
    else:
        logger.error(f"✗ Failed to get account info: {account_response.error}")
    
    # 2. Get token supply
    supply_response = await client.get_token_supply(usdc_mint)
    if supply_response.success:
        supply_data = supply_response.data.get('value', {})
        logger.info(f"✓ Token supply: {supply_data.get('uiAmountString', 'N/A')}")
    
    # 3. Get largest holders
    holders_response = await client.get_token_largest_accounts(usdc_mint)
    if holders_response.success:
        holders = holders_response.data.get('value', [])
        logger.info(f"✓ Found {len(holders)} largest holders")
        if holders:
            top_holder = holders[0]
            logger.info(f"  Top holder: {top_holder.get('address')}")
            logger.info(f"  Balance: {top_holder.get('uiAmountString')}")
    
    # 4. Check node health
    health_response = await client.get_health()
    logger.info(f"✓ Node health: {'OK' if health_response.success else 'ERROR'}")
    
    return {
        "account_info": account_response.data,
        "supply": supply_response.data,
        "largest_holders": holders_response.data
    }


# -------------------------
# Example 2: Batch Processing
# -------------------------

async def example_batch_processing():
    """Demonstrate batch processing of multiple tokens."""
    logger.info("\n=== Example 2: Batch Processing ===")
    
    # Initialize batch processor
    processor = BatchProcessor(batch_size=100, max_concurrent=10)
    
    # Example token addresses (replace with real addresses)
    token_addresses = [
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        "So11111111111111111111111111111111111111112",   # Wrapped SOL
    ]
    
    # Enrich token accounts
    result = await processor.enrich_token_accounts(token_addresses)
    
    logger.info(f"✓ Batch processing complete:")
    logger.info(f"  Total: {result.total}")
    logger.info(f"  Successful: {len(result.successful)}")
    logger.info(f"  Failed: {len(result.failed)}")
    logger.info(f"  Success rate: {result.success_rate:.1%}")
    
    # Display enriched data
    for item in result.successful[:3]:  # Show first 3
        address = item.get('address')
        account = item.get('account_data', {})
        logger.info(f"\n  Token: {address}")
        logger.info(f"    Lamports: {account.get('lamports', 0)}")
        logger.info(f"    Owner: {account.get('owner')}")
    
    return result


# -------------------------
# Example 3: Token Holder Analysis
# -------------------------

async def example_token_holder_analysis():
    """Demonstrate comprehensive token holder analysis."""
    logger.info("\n=== Example 3: Token Holder Analysis ===")
    
    processor = BatchProcessor()
    
    # Example token (replace with actual mint address)
    mint_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Get comprehensive holder info
    holder_info = await processor.get_token_holder_info(mint_address)
    
    logger.info(f"✓ Token: {mint_address}")
    
    if holder_info.get('supply'):
        supply = holder_info['supply'].get('value', {})
        logger.info(f"  Total Supply: {supply.get('uiAmountString', 'N/A')}")
    
    largest_holders = holder_info.get('largest_holders', [])
    logger.info(f"  Largest Holders: {len(largest_holders)}")
    
    for i, holder in enumerate(largest_holders[:5], 1):
        logger.info(f"    #{i}: {holder.get('uiAmountString')} tokens")
    
    if holder_info.get('errors'):
        logger.warning(f"  Errors encountered: {len(holder_info['errors'])}")
    
    return holder_info


# -------------------------
# Example 4: Distribution Analysis
# -------------------------

async def example_distribution_analysis():
    """Demonstrate token distribution and concentration analysis."""
    logger.info("\n=== Example 4: Distribution Analysis ===")
    
    processor = BatchProcessor()
    
    # Example token
    mint_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Analyze distribution
    distribution = await processor.analyze_token_distribution(
        mint_address,
        top_n=100
    )
    
    logger.info(f"✓ Distribution analysis for {mint_address}")
    logger.info(f"  Total Supply: {distribution.get('total_supply', 0):,.0f}")
    
    concentration = distribution.get('concentration', {})
    logger.info(f"  Concentration:")
    logger.info(f"    Top 1 holder: {concentration.get('top_1_percent', 0)}%")
    logger.info(f"    Top 5 holders: {concentration.get('top_5_percent', 0)}%")
    logger.info(f"    Top 10 holders: {concentration.get('top_10_percent', 0)}%")
    
    gini = distribution.get('gini_coefficient', 0)
    logger.info(f"  Gini Coefficient: {gini:.4f}")
    logger.info(f"    (0 = perfect equality, 1 = perfect inequality)")
    
    return distribution


# -------------------------
# Example 5: Transaction Enrichment
# -------------------------

async def example_transaction_enrichment():
    """Demonstrate transaction enrichment."""
    logger.info("\n=== Example 5: Transaction Enrichment ===")
    
    processor = BatchProcessor()
    
    # Example transaction signatures (replace with real signatures)
    signatures = [
        # Add real transaction signatures here
    ]
    
    if not signatures:
        logger.warning("  No signatures provided - skipping example")
        return None
    
    # Enrich transactions
    result = await processor.enrich_transactions(signatures)
    
    logger.info(f"✓ Transaction enrichment complete:")
    logger.info(f"  Success rate: {result.success_rate:.1%}")
    
    for item in result.successful[:3]:
        sig = item.get('signature')
        tx = item.get('transaction', {})
        logger.info(f"\n  Signature: {sig[:16]}...")
        logger.info(f"    Slot: {tx.get('slot', 'N/A')}")
        logger.info(f"    Block time: {tx.get('blockTime', 'N/A')}")
    
    return result


# -------------------------
# Example 6: Token Enrichment with Dexscreener Data
# -------------------------

async def example_combined_enrichment():
    """Demonstrate combining Dexscreener data with RPC enrichment."""
    logger.info("\n=== Example 6: Combined Enrichment ===")
    
    enricher = TokenEnricher()
    
    # Example parsed Dexscreener tokens
    dex_tokens = [
        {
            "pair_address": "example_pair",
            "base_token": {
                "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "name": "USD Coin",
                "symbol": "USDC"
            },
            "price_usd": 1.0,
            "fdv": 1000000000,
            "volume": {"h24": 50000000}
        }
    ]
    
    # Enrich with on-chain data
    enriched = await enricher.enrich_dexscreener_tokens(dex_tokens)
    
    logger.info(f"✓ Enriched {len(enriched)} tokens with on-chain data")
    
    for token in enriched:
        base_addr = token.get('base_token', {}).get('address')
        on_chain = token.get('on_chain_data')
        
        logger.info(f"\n  Token: {base_addr}")
        logger.info(f"    Name: {token.get('base_token', {}).get('name')}")
        logger.info(f"    Price: ${token.get('price_usd', 0):.6f}")
        
        if on_chain:
            logger.info(f"    On-chain: ✓ Available")
            logger.info(f"    Lamports: {on_chain.get('lamports', 0)}")
        else:
            logger.info(f"    On-chain: ✗ Not available")
    
    return enriched


# -------------------------
# Example 7: Comprehensive Token Data
# -------------------------

async def example_comprehensive_token_data():
    """Demonstrate getting all available data for a token."""
    logger.info("\n=== Example 7: Comprehensive Token Data ===")
    
    enricher = TokenEnricher()
    
    # Example token
    mint_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    # Get comprehensive data
    comprehensive = await enricher.get_comprehensive_token_data(mint_address)
    
    logger.info(f"✓ Comprehensive data for {mint_address}")
    
    # Distribution
    distribution = comprehensive.get('distribution_analysis', {})
    logger.info(f"\n  Distribution:")
    logger.info(f"    Total Supply: {distribution.get('total_supply', 0):,.0f}")
    concentration = distribution.get('concentration', {})
    logger.info(f"    Top 10 holders: {concentration.get('top_10_percent', 0)}%")
    
    # Holder Info
    holder_info = comprehensive.get('holder_info', {})
    largest = holder_info.get('largest_holders', [])
    logger.info(f"\n  Largest Holders: {len(largest)}")
    
    # Account Info
    account_info = comprehensive.get('account_info')
    if account_info:
        logger.info(f"\n  Account Info:")
        logger.info(f"    Owner: {account_info.get('value', {}).get('owner')}")
        logger.info(f"    Executable: {account_info.get('value', {}).get('executable')}")
    
    return comprehensive


# -------------------------
# Main Example Runner
# -------------------------

async def run_all_examples():
    """Run all examples."""
    logger.info("=" * 60)
    logger.info("RPC ENRICHMENT MODULE - USAGE EXAMPLES")
    logger.info("=" * 60)
    
    try:
        # Run examples
        await example_basic_rpc_usage()
        await example_batch_processing()
        await example_token_holder_analysis()
        await example_distribution_analysis()
        await example_transaction_enrichment()
        await example_combined_enrichment()
        await example_comprehensive_token_data()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ All examples completed successfully!")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"Error running examples: {str(e)}", exc_info=True)


if __name__ == "__main__":
    # Run all examples
    asyncio.run(run_all_examples())
