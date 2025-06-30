"""
Market-related utilities for RMR testing.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_DOWN

from injective_cli import cli, InjectiveCLIError
from test_config import config


logger = logging.getLogger(__name__)


class MarketUtils:
    """Utilities for perpetual market operations."""
    
    @staticmethod
    def create_market_proposal_json(
        ticker: str,
        base_denom: str,
        quote_denom: str,
        rmr: float,
        imr: float = None,
        mmr: float = None,
        **kwargs
    ) -> str:
        """
        Create a JSON proposal for launching a perpetual market with RMR.
        
        Args:
            ticker: Market ticker (e.g., "TST/USDT PERP")
            base_denom: Base denomination
            quote_denom: Quote denomination
            rmr: Reduce Margin Ratio
            imr: Initial Margin Ratio (defaults to config value)
            mmr: Maintenance Margin Ratio (defaults to config value)
            **kwargs: Additional market parameters
            
        Returns:
            JSON string for governance proposal
        """
        if imr is None:
            imr = config.margin_ratios["imr"]
        if mmr is None:
            mmr = config.margin_ratios["mmr"]
        
        # Validate RMR constraint
        if not config.validate_rmr_constraint(rmr, imr, mmr):
            raise ValueError(f"Invalid margin ratios: RMR({rmr}) >= IMR({imr}) > MMR({mmr}) constraint not met")
        
        # Convert to string format expected by blockchain
        rmr_str = str(Decimal(str(rmr)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))
        imr_str = str(Decimal(str(imr)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))
        mmr_str = str(Decimal(str(mmr)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))
        
        proposal = {
            "messages": [
                {
                    "@type": "/injective.exchange.v1beta1.MsgInstantPerpetualMarketLaunch",
                    "sender": kwargs.get("sender", "inj1..."),  # Will be replaced with actual sender
                    "ticker": ticker,
                    "base_denom": base_denom,
                    "quote_denom": quote_denom,
                    "oracle_base": kwargs.get("oracle_base", base_denom),
                    "oracle_quote": kwargs.get("oracle_quote", quote_denom),
                    "oracle_scale_factor": kwargs.get("oracle_scale_factor", 6),
                    "oracle_type": kwargs.get("oracle_type", "Band"),
                    "maker_fee_rate": kwargs.get("maker_fee_rate", "0.001"),
                    "taker_fee_rate": kwargs.get("taker_fee_rate", "0.002"),
                    "initial_margin_ratio": imr_str,
                    "maintenance_margin_ratio": mmr_str,
                    "reduce_margin_ratio": rmr_str,  # The key field we're testing
                    "min_price_tick_size": kwargs.get("min_price_tick_size", "0.000001"),
                    "min_quantity_tick_size": kwargs.get("min_quantity_tick_size", "0.001"),
                }
            ],
            "metadata": kwargs.get("metadata", "ipfs://CID"),
            "deposit": kwargs.get("deposit", "1000000000000000000inj"),  # 1 INJ
            "title": f"Launch {ticker} Perpetual Market with RMR",
            "summary": f"Proposal to launch {ticker} perpetual market with RMR={rmr_str}",
        }
        
        return json.dumps(proposal, indent=2)
    
    @staticmethod
    def submit_and_pass_proposal(proposal_json: str, timeout: int = 60) -> str:
        """
        Submit a governance proposal and vote to pass it.
        
        Args:
            proposal_json: Proposal JSON string
            timeout: Timeout in seconds
            
        Returns:
            Proposal ID
        """
        # Submit proposal
        logger.info("Submitting governance proposal...")
        result = cli.create_market_proposal(proposal_json, config.admin_key)
        
        if "code" in result and result["code"] != 0:
            raise InjectiveCLIError(f"Failed to submit proposal: {result}")
        
        # Extract proposal ID from transaction events
        proposal_id = MarketUtils._extract_proposal_id(result)
        logger.info(f"Proposal submitted with ID: {proposal_id}")
        
        # Wait for proposal to be in voting period
        time.sleep(5)
        
        # Vote on proposal
        logger.info(f"Voting on proposal {proposal_id}...")
        vote_result = cli.vote_proposal(proposal_id, "yes", config.validator_key)
        
        if "code" in vote_result and vote_result["code"] != 0:
            raise InjectiveCLIError(f"Failed to vote on proposal: {vote_result}")
        
        # Wait for proposal to pass
        start_time = time.time()
        while time.time() - start_time < timeout:
            proposal_status = cli.query_proposal(proposal_id)
            status = proposal_status.get("proposal", {}).get("status", "")
            
            if status == "PROPOSAL_STATUS_PASSED":
                logger.info(f"Proposal {proposal_id} passed successfully")
                return proposal_id
            elif status in ["PROPOSAL_STATUS_REJECTED", "PROPOSAL_STATUS_FAILED"]:
                raise InjectiveCLIError(f"Proposal {proposal_id} failed with status: {status}")
            
            time.sleep(3)
        
        raise InjectiveCLIError(f"Proposal {proposal_id} did not pass within timeout")
    
    @staticmethod
    def _extract_proposal_id(tx_result: Dict[str, Any]) -> str:
        """Extract proposal ID from transaction result."""
        # Look for proposal_id in events
        events = tx_result.get("events", [])
        for event in events:
            if event.get("type") == "submit_proposal":
                for attr in event.get("attributes", []):
                    if attr.get("key") == "proposal_id":
                        return attr.get("value")
        
        # Fallback: look in raw_log
        raw_log = tx_result.get("raw_log", "")
        if "proposal_id" in raw_log:
            import re
            match = re.search(r'"proposal_id":"(\d+)"', raw_log)
            if match:
                return match.group(1)
        
        raise InjectiveCLIError("Could not extract proposal ID from transaction result")
    
    @staticmethod
    def get_market_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
        """
        Find a market by its ticker.
        
        Args:
            ticker: Market ticker to search for
            
        Returns:
            Market information or None if not found
        """
        markets = cli.query_all_markets()
        
        for market in markets.get("markets", []):
            if market.get("market", {}).get("ticker") == ticker:
                return market
        
        return None
    
    @staticmethod
    def verify_rmr_value(market_id: str, expected_rmr: float, tolerance: float = 0.000001) -> bool:
        """
        Verify that a market has the expected RMR value.
        
        Args:
            market_id: Market ID to check
            expected_rmr: Expected RMR value
            tolerance: Tolerance for floating point comparison
            
        Returns:
            True if RMR matches expected value
        """
        market_info = cli.query_market(market_id)
        market_data = market_info.get("market", {})
        
        if not market_data:
            logger.error(f"Market {market_id} not found")
            return False
        
        # Get the RMR value from market data
        rmr_str = market_data.get("reduce_margin_ratio")
        if rmr_str is None:
            logger.error(f"RMR field not found in market {market_id}")
            return False
        
        try:
            actual_rmr = float(rmr_str)
            diff = abs(actual_rmr - expected_rmr)
            
            logger.info(f"Market {market_id} RMR: expected={expected_rmr}, actual={actual_rmr}, diff={diff}")
            
            return diff <= tolerance
            
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse RMR value '{rmr_str}': {e}")
            return False
    
    @staticmethod
    def update_market_rmr(market_id: str, new_rmr: float) -> bool:
        """
        Update market RMR via admin message.
        
        Args:
            market_id: Market ID to update
            new_rmr: New RMR value
            
        Returns:
            True if update was successful
        """
        rmr_str = str(Decimal(str(new_rmr)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))
        
        try:
            result = cli.update_market_admin(market_id, rmr_str, config.admin_key)
            
            if "code" in result and result["code"] != 0:
                logger.error(f"Failed to update market RMR: {result}")
                return False
            
            # Wait for update to take effect
            cli.wait_for_next_block(2)
            
            # Verify the update
            return MarketUtils.verify_rmr_value(market_id, new_rmr)
            
        except Exception as e:
            logger.error(f"Exception during market RMR update: {e}")
            return False


# Convenience functions
def create_test_market(ticker: str, rmr: float, **kwargs) -> str:
    """Create a test market with specified RMR and return market ID."""
    proposal_json = MarketUtils.create_market_proposal_json(
        ticker=ticker,
        base_denom="tst",
        quote_denom="usdt",
        rmr=rmr,
        **kwargs
    )
    
    proposal_id = MarketUtils.submit_and_pass_proposal(proposal_json)
    
    # Wait for market to be created
    time.sleep(10)
    
    # Find the created market
    market = MarketUtils.get_market_by_ticker(ticker)
    if not market:
        raise InjectiveCLIError(f"Market {ticker} not found after creation")
    
    return market.get("market", {}).get("market_id", "") 