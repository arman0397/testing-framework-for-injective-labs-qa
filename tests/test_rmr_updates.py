"""
Test cases for RMR market updates - updating existing market RMR values via admin messages.
"""

import pytest
import logging
import time

from market_utils import MarketUtils
from test_config import config
from injective_cli import InjectiveCLIError


logger = logging.getLogger(__name__)


class TestRMRUpdates:
    """Test suite for RMR market update functionality."""
    
    @pytest.mark.updates
    def test_update_market_rmr(self, clean_test_market, rmr_test_values):
        """
        Test: Verify RMR can be updated via admin message.
        
        This test validates the core functionality of updating an existing
        market's RMR value through admin messages.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        original_rmr = market_data["rmr"]
        
        # Choose a different RMR value for update
        new_rmr = rmr_test_values["valid_high"]  # 15%
        
        logger.info(f"Updating market {market_id} RMR from {original_rmr} to {new_rmr}")
        
        # Update the market RMR
        update_success = MarketUtils.update_market_rmr(market_id, new_rmr)
        assert update_success, "RMR update should succeed"
        
        # Verify the update took effect
        rmr_correct = MarketUtils.verify_rmr_value(market_id, new_rmr)
        assert rmr_correct, f"Market should have updated RMR value: {new_rmr}"
        
        logger.info(f"Successfully updated market {market_id} RMR to {new_rmr}")
    
    @pytest.mark.updates
    def test_rmr_update_persistence(self, clean_test_market, rmr_test_values):
        """
        Test: Verify updated RMR values persist across queries.
        
        This test ensures that RMR updates are permanently stored
        and remain consistent across multiple blockchain queries.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        
        new_rmr = rmr_test_values["valid_low"]  # 5%
        
        logger.info(f"Testing RMR persistence for market {market_id}")
        
        # Update RMR
        update_success = MarketUtils.update_market_rmr(market_id, new_rmr)
        assert update_success, "RMR update should succeed"
        
        # Wait a bit for blockchain state to settle
        time.sleep(5)
        
        # Query multiple times to verify persistence
        for i in range(3):
            logger.info(f"Verification attempt {i+1}/3")
            rmr_correct = MarketUtils.verify_rmr_value(market_id, new_rmr)
            assert rmr_correct, f"RMR should persist across queries (attempt {i+1})"
            time.sleep(2)
        
        logger.info("RMR update persistence verified")
    
    @pytest.mark.updates
    @pytest.mark.parametrize("new_rmr_scenario", ["valid_high", "valid_medium", "boundary"])
    def test_rmr_update_constraint_validation(self, clean_test_market, rmr_test_values, 
                                            margin_ratios, new_rmr_scenario):
        """
        Test: Verify RMR constraint validation during updates.
        
        This test validates that RMR updates still enforce the constraint
        RMR >= IMR > MMR, ensuring data integrity during updates.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        
        new_rmr = rmr_test_values[new_rmr_scenario]
        imr = margin_ratios["imr"]
        mmr = margin_ratios["mmr"]
        
        logger.info(f"Testing RMR update constraint for scenario '{new_rmr_scenario}': "
                   f"new_RMR={new_rmr}, IMR={imr}, MMR={mmr}")
        
        # Verify constraint is valid
        constraint_valid = config.validate_rmr_constraint(new_rmr, imr, mmr)
        assert constraint_valid, f"Test data should satisfy constraint: RMR({new_rmr}) >= IMR({imr}) > MMR({mmr})"
        
        # Update should succeed with valid constraint
        update_success = MarketUtils.update_market_rmr(market_id, new_rmr)
        assert update_success, f"Valid RMR update should succeed for scenario '{new_rmr_scenario}'"
        
        # Verify the update
        rmr_correct = MarketUtils.verify_rmr_value(market_id, new_rmr)
        assert rmr_correct, f"Market should have updated RMR: {new_rmr}"
        
        logger.info(f"RMR update constraint validation passed for scenario '{new_rmr_scenario}'")
    
    @pytest.mark.updates
    def test_invalid_rmr_update_rejected(self, clean_test_market, rmr_test_values):
        """
        Test: Verify invalid RMR updates are rejected.
        
        This test ensures that attempts to update RMR to values that violate
        the constraint (RMR < IMR) are properly rejected by the system.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        original_rmr = market_data["rmr"]
        
        # Try to update to invalid RMR (below IMR)
        invalid_rmr = rmr_test_values["invalid_low"]  # 2%
        
        logger.info(f"Testing invalid RMR update: market {market_id}, invalid_RMR={invalid_rmr}")
        
        # This update should fail
        update_success = MarketUtils.update_market_rmr(market_id, invalid_rmr)
        assert not update_success, "Invalid RMR update should be rejected"
        
        # Verify original RMR is unchanged
        rmr_unchanged = MarketUtils.verify_rmr_value(market_id, original_rmr)
        assert rmr_unchanged, "Original RMR should remain unchanged after failed update"
        
        logger.info("Invalid RMR update correctly rejected")
    
    @pytest.mark.updates
    def test_rmr_update_precision(self, clean_test_market):
        """
        Test: Verify RMR update precision handling.
        
        This test ensures that RMR updates with high precision values
        are handled correctly without precision loss.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        
        # Use high precision RMR
        high_precision_rmr = 0.087654  # 8.7654%
        
        logger.info(f"Testing high precision RMR update: {high_precision_rmr}")
        
        # Update to high precision value
        update_success = MarketUtils.update_market_rmr(market_id, high_precision_rmr)
        assert update_success, "High precision RMR update should succeed"
        
        # Verify precision is maintained (with reasonable tolerance)
        rmr_correct = MarketUtils.verify_rmr_value(
            market_id, 
            high_precision_rmr, 
            tolerance=0.000001
        )
        assert rmr_correct, f"High precision RMR should be maintained: {high_precision_rmr}"
        
        logger.info("High precision RMR update handled correctly")
    
    @pytest.mark.updates
    def test_multiple_rmr_updates(self, clean_test_market, rmr_test_values):
        """
        Test: Verify multiple consecutive RMR updates work correctly.
        
        This test validates that a market can undergo multiple RMR updates
        in sequence, with each update taking effect properly.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        
        # Sequence of RMR updates
        update_sequence = [
            ("valid_high", rmr_test_values["valid_high"]),    # 15%
            ("valid_medium", rmr_test_values["valid_medium"]), # 10% 
            ("valid_low", rmr_test_values["valid_low"]),      # 5%
            ("boundary", rmr_test_values["boundary"])         # 3.5%
        ]
        
        logger.info(f"Testing multiple RMR updates for market {market_id}")
        
        for i, (scenario, rmr_value) in enumerate(update_sequence):
            logger.info(f"Update {i+1}/{len(update_sequence)}: {scenario} -> RMR={rmr_value}")
            
            # Perform update
            update_success = MarketUtils.update_market_rmr(market_id, rmr_value)
            assert update_success, f"Update {i+1} should succeed"
            
            # Verify update
            rmr_correct = MarketUtils.verify_rmr_value(market_id, rmr_value)
            assert rmr_correct, f"Update {i+1} should set RMR to {rmr_value}"
            
            # Wait between updates
            time.sleep(3)
        
        logger.info("Multiple RMR updates completed successfully")
    
    @pytest.mark.updates
    def test_rmr_update_authorization(self, clean_test_market, rmr_test_values):
        """
        Test: Verify RMR updates require proper admin authorization.
        
        This test ensures that only authorized admin accounts can update
        market RMR values, maintaining security and access control.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        original_rmr = market_data["rmr"]
        
        new_rmr = rmr_test_values["valid_high"]
        
        logger.info(f"Testing RMR update authorization for market {market_id}")
        
        # Test with correct admin key (should succeed)
        logger.info("Testing with authorized admin key...")
        update_success = MarketUtils.update_market_rmr(market_id, new_rmr)
        assert update_success, "Update with admin key should succeed"
        
        # Verify update took effect
        rmr_correct = MarketUtils.verify_rmr_value(market_id, new_rmr)
        assert rmr_correct, "Admin update should take effect"
        
        logger.info("Authorized RMR update succeeded as expected")
        
        # Note: Testing unauthorized access would require a non-admin key,
        # which is beyond the scope of this basic test suite
    
    @pytest.mark.updates
    def test_rmr_update_idempotency(self, clean_test_market, rmr_test_values):
        """
        Test: Verify RMR updates are idempotent.
        
        This test ensures that updating RMR to the same value multiple times
        doesn't cause issues and maintains consistency.
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        
        target_rmr = rmr_test_values["valid_medium"]  # 10%
        
        logger.info(f"Testing RMR update idempotency for market {market_id}")
        
        # Perform the same update multiple times
        for i in range(3):
            logger.info(f"Idempotent update attempt {i+1}/3")
            
            update_success = MarketUtils.update_market_rmr(market_id, target_rmr)
            assert update_success, f"Idempotent update {i+1} should succeed"
            
            # Verify RMR value
            rmr_correct = MarketUtils.verify_rmr_value(market_id, target_rmr)
            assert rmr_correct, f"RMR should remain consistent after update {i+1}"
            
            time.sleep(2)
        
        logger.info("RMR update idempotency verified")
    
    @pytest.mark.updates
    def test_rmr_update_boundary_values(self, clean_test_market, margin_ratios):
        """
        Test: Verify RMR updates work correctly with boundary values.
        
        This test validates RMR updates with values at the boundaries
        of the valid range (e.g., exactly equal to IMR).
        """
        market_data = clean_test_market
        market_id = market_data["market_id"]
        
        # Test boundary case: RMR exactly equal to IMR
        imr = margin_ratios["imr"]
        boundary_rmr = imr  # RMR = IMR (minimum valid value)
        
        logger.info(f"Testing boundary RMR update: RMR={boundary_rmr} (equals IMR)")
        
        # This should be valid (RMR = IMR satisfies RMR >= IMR)
        update_success = MarketUtils.update_market_rmr(market_id, boundary_rmr)
        assert update_success, "Boundary RMR update (RMR=IMR) should succeed"
        
        # Verify the boundary value
        rmr_correct = MarketUtils.verify_rmr_value(market_id, boundary_rmr)
        assert rmr_correct, f"Boundary RMR value should be set correctly: {boundary_rmr}"
        
        logger.info("Boundary RMR update handled correctly") 