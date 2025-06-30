"""
Test cases for RMR governance flow - launching perpetual markets with RMR values.
"""

import pytest
import logging
import time

from market_utils import MarketUtils
from test_config import config


logger = logging.getLogger(__name__)


class TestRMRGovernance:
    """Test suite for RMR governance functionality."""
    
    @pytest.mark.governance
    @pytest.mark.slow
    def test_create_perp_market_with_rmr(self, unique_ticker, test_keys, rmr_test_values):
        """
        Test: Verify that perpetual markets can be launched with RMR values via governance.
        
        This test validates the core functionality of creating a perpetual market
        with a specific RMR value through the governance process.
        """
        logger.info(f"Testing market creation with RMR for ticker: {unique_ticker}")
        
        # Use medium RMR value for this test
        rmr = rmr_test_values["valid_medium"]
        
        # Create governance proposal JSON
        proposal_json = MarketUtils.create_market_proposal_json(
            ticker=unique_ticker,
            base_denom="tst",
            quote_denom="usdt",
            rmr=rmr
        )
        
        logger.info(f"Created proposal for market {unique_ticker} with RMR={rmr}")
        
        # Submit and pass the proposal
        proposal_id = MarketUtils.submit_and_pass_proposal(proposal_json, timeout=120)
        
        # Verify proposal passed
        assert proposal_id is not None, "Proposal should have been created and passed"
        logger.info(f"Proposal {proposal_id} passed successfully")
        
        # Wait for market to be available
        time.sleep(15)
        
        # Verify market was created
        market = MarketUtils.get_market_by_ticker(unique_ticker)
        assert market is not None, f"Market {unique_ticker} should exist after governance"
        
        market_id = market.get("market", {}).get("market_id", "")
        assert market_id, "Market should have a valid ID"
        
        logger.info(f"Successfully created market {unique_ticker} with ID: {market_id}")
    
    @pytest.mark.governance
    def test_rmr_stored_correctly(self, clean_test_market, rmr_test_values):
        """
        Test: Verify that RMR value is stored and retrievable from the blockchain.
        
        This test ensures that the RMR value specified during market creation
        is correctly stored and can be queried from the blockchain state.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        expected_rmr = market_data["rmr"]
        
        logger.info(f"Verifying RMR storage for market {market_id}")
        
        # Verify the stored RMR value matches what we set
        rmr_correct = MarketUtils.verify_rmr_value(market_id, expected_rmr)
        assert rmr_correct, f"Market {market_id} should have RMR={expected_rmr}"
        
        logger.info(f"RMR value correctly stored for market {market_id}")
    
    @pytest.mark.governance
    @pytest.mark.parametrize("rmr_scenario", ["valid_high", "valid_medium", "valid_low"])
    def test_rmr_constraint_validation(self, unique_ticker, test_keys, rmr_test_values, 
                                     margin_ratios, rmr_scenario):
        """
        Test: Verify RMR constraint (RMR >= IMR > MMR) is enforced during market creation.
        
        This test validates that the blockchain enforces the mathematical constraint
        that RMR must be greater than or equal to IMR, which must be greater than MMR.
        """
        rmr = rmr_test_values[rmr_scenario]
        imr = margin_ratios["imr"]
        mmr = margin_ratios["mmr"]
        
        logger.info(f"Testing RMR constraint for scenario '{rmr_scenario}': "
                   f"RMR={rmr}, IMR={imr}, MMR={mmr}")
        
        # Verify constraint is mathematically valid
        assert config.validate_rmr_constraint(rmr, imr, mmr), \
            f"Test data should satisfy RMR({rmr}) >= IMR({imr}) > MMR({mmr})"
        
        # Create market with these values
        proposal_json = MarketUtils.create_market_proposal_json(
            ticker=unique_ticker,
            base_denom="tst", 
            quote_denom="usdt",
            rmr=rmr,
            imr=imr,
            mmr=mmr
        )
        
        # Market should be created successfully
        proposal_id = MarketUtils.submit_and_pass_proposal(proposal_json, timeout=120)
        assert proposal_id is not None, "Valid RMR constraint should allow market creation"
        
        # Wait for market creation
        time.sleep(15)
        
        # Verify market exists and has correct RMR
        market = MarketUtils.get_market_by_ticker(unique_ticker)
        assert market is not None, "Market should be created with valid RMR constraint"
        
        market_id = market.get("market", {}).get("market_id", "")
        rmr_correct = MarketUtils.verify_rmr_value(market_id, rmr)
        assert rmr_correct, f"Market should have the specified RMR value: {rmr}"
        
        logger.info(f"Successfully validated RMR constraint for scenario '{rmr_scenario}'")
    
    @pytest.mark.governance  
    def test_invalid_rmr_constraint_rejected(self, unique_ticker, test_keys, 
                                           rmr_test_values, margin_ratios):
        """
        Test: Verify that markets with invalid RMR constraints are rejected.
        
        This test validates that the system properly rejects market creation
        attempts where RMR < IMR, violating the required constraint.
        """
        # Use invalid RMR (below IMR)
        invalid_rmr = rmr_test_values["invalid_low"]  # 0.02 (2%)
        imr = margin_ratios["imr"]  # 0.05 (5%)
        mmr = margin_ratios["mmr"]  # 0.03 (3%)
        
        logger.info(f"Testing invalid RMR constraint: RMR={invalid_rmr}, IMR={imr}, MMR={mmr}")
        
        # This should fail validation during proposal creation
        with pytest.raises(ValueError, match="Invalid margin ratios"):
            MarketUtils.create_market_proposal_json(
                ticker=unique_ticker,
                base_denom="tst",
                quote_denom="usdt", 
                rmr=invalid_rmr,
                imr=imr,
                mmr=mmr
            )
        
        logger.info("Invalid RMR constraint correctly rejected during proposal creation")
    
    @pytest.mark.governance
    def test_rmr_precision_handling(self, unique_ticker, test_keys):
        """
        Test: Verify that RMR values with high precision are handled correctly.
        
        This test ensures that RMR values with multiple decimal places
        are properly stored and retrieved without precision loss.
        """
        # Use high precision RMR value
        high_precision_rmr = 0.051234  # 5.1234%
        
        logger.info(f"Testing high precision RMR: {high_precision_rmr}")
        
        proposal_json = MarketUtils.create_market_proposal_json(
            ticker=unique_ticker,
            base_denom="tst",
            quote_denom="usdt",
            rmr=high_precision_rmr
        )
        
        proposal_id = MarketUtils.submit_and_pass_proposal(proposal_json, timeout=120)
        assert proposal_id is not None, "High precision RMR should be accepted"
        
        # Wait for market creation
        time.sleep(15)
        
        # Verify market exists
        market = MarketUtils.get_market_by_ticker(unique_ticker)
        assert market is not None, "Market should be created with high precision RMR"
        
        market_id = market.get("market", {}).get("market_id", "")
        
        # Verify RMR precision (allow for reasonable tolerance due to blockchain precision)
        rmr_correct = MarketUtils.verify_rmr_value(market_id, high_precision_rmr, tolerance=0.000001)
        assert rmr_correct, f"Market should preserve RMR precision: {high_precision_rmr}"
        
        logger.info("High precision RMR value handled correctly")
    
    @pytest.mark.governance
    def test_multiple_markets_with_different_rmr(self, test_keys, rmr_test_values):
        """
        Test: Verify that multiple markets can be created with different RMR values.
        
        This test validates that the system can handle multiple markets
        each with their own distinct RMR configurations.
        """
        import uuid
        
        markets_created = []
        
        try:
            # Create multiple markets with different RMR values
            test_scenarios = [
                ("valid_high", "HIGH"),
                ("valid_medium", "MED"),
                ("valid_low", "LOW")
            ]
            
            for rmr_key, suffix in test_scenarios:
                timestamp = int(time.time())
                unique_id = str(uuid.uuid4())[:6]
                ticker = f"MULTI{suffix}{timestamp}{unique_id}/USDT PERP"
                rmr = rmr_test_values[rmr_key]
                
                logger.info(f"Creating market {ticker} with RMR={rmr}")
                
                proposal_json = MarketUtils.create_market_proposal_json(
                    ticker=ticker,
                    base_denom="tst",
                    quote_denom="usdt",
                    rmr=rmr
                )
                
                proposal_id = MarketUtils.submit_and_pass_proposal(proposal_json, timeout=120)
                assert proposal_id is not None, f"Market {ticker} should be created"
                
                # Wait between creations to avoid conflicts
                time.sleep(10)
                
                # Verify market exists
                market = MarketUtils.get_market_by_ticker(ticker)
                assert market is not None, f"Market {ticker} should exist"
                
                market_id = market.get("market", {}).get("market_id", "")
                markets_created.append({
                    "ticker": ticker,
                    "market_id": market_id,
                    "rmr": rmr
                })
            
            # Verify all markets have correct RMR values
            for market_info in markets_created:
                rmr_correct = MarketUtils.verify_rmr_value(
                    market_info["market_id"], 
                    market_info["rmr"]
                )
                assert rmr_correct, \
                    f"Market {market_info['ticker']} should have RMR={market_info['rmr']}"
            
            logger.info(f"Successfully created {len(markets_created)} markets with different RMR values")
            
        except Exception as e:
            logger.error(f"Failed to create multiple markets: {e}")
            raise 