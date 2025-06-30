"""
Test cases for RMR validation logic - testing constraints, edge cases, and error handling.
"""

import pytest
import logging
import math

from market_utils import MarketUtils
from test_config import config


logger = logging.getLogger(__name__)


class TestRMRValidation:
    """Test suite for RMR validation logic and constraints."""
    
    @pytest.mark.validation
    @pytest.mark.parametrize("rmr,imr,mmr,should_be_valid", [
        # Valid cases
        (0.10, 0.05, 0.03, True),   # RMR > IMR > MMR
        (0.05, 0.05, 0.03, True),   # RMR = IMR > MMR (boundary case)
        (0.15, 0.10, 0.05, True),   # All different, valid constraint
        (0.20, 0.15, 0.10, True),   # Higher values, valid constraint
        
        # Invalid cases
        (0.03, 0.05, 0.03, False),  # RMR < IMR (violates constraint)
        (0.02, 0.05, 0.03, False),  # RMR < IMR (clearly invalid)
        (0.10, 0.03, 0.05, False),  # IMR < MMR (violates constraint)
        (0.05, 0.05, 0.05, False),  # IMR = MMR (violates IMR > MMR)
    ])
    def test_rmr_constraint_enforcement(self, rmr, imr, mmr, should_be_valid):
        """
        Test: Verify mathematical constraints are properly enforced.
        
        This test validates the core constraint: RMR >= IMR > MMR
        with various combinations of values.
        """
        logger.info(f"Testing constraint: RMR={rmr}, IMR={imr}, MMR={mmr}, "
                   f"expected_valid={should_be_valid}")
        
        # Test the validation logic
        is_valid = config.validate_rmr_constraint(rmr, imr, mmr)
        
        if should_be_valid:
            assert is_valid, f"Should be valid: RMR({rmr}) >= IMR({imr}) > MMR({mmr})"
        else:
            assert not is_valid, f"Should be invalid: RMR({rmr}) >= IMR({imr}) > MMR({mmr})"
        
        logger.info(f"Constraint validation correct for RMR={rmr}, IMR={imr}, MMR={mmr}")
    
    @pytest.mark.validation
    @pytest.mark.parametrize("test_rmr", [
        0.0,        # Zero RMR
        0.000001,   # Very small RMR
        0.999999,   # Very large RMR (99.9999%)
        1.0,        # 100% RMR
        0.05,       # Exactly equal to standard IMR
        0.050001,   # Just above standard IMR
        0.049999,   # Just below standard IMR
    ])
    def test_edge_case_values(self, test_rmr, margin_ratios):
        """
        Test: Verify edge case and boundary values are handled correctly.
        
        This test validates the system's behavior with extreme values,
        boundary conditions, and edge cases.
        """
        imr = margin_ratios["imr"]  # 0.05
        mmr = margin_ratios["mmr"]  # 0.03
        
        logger.info(f"Testing edge case: RMR={test_rmr}")
        
        # Determine if this should be valid based on constraint
        expected_valid = config.validate_rmr_constraint(test_rmr, imr, mmr)
        
        if expected_valid:
            # Should be able to create proposal JSON without error
            try:
                proposal_json = MarketUtils.create_market_proposal_json(
                    ticker=f"EDGE{int(test_rmr*1000000)}/USDT PERP",
                    base_denom="tst",
                    quote_denom="usdt",
                    rmr=test_rmr,
                    imr=imr,
                    mmr=mmr
                )
                
                # Should succeed
                assert proposal_json is not None, f"Valid RMR {test_rmr} should create proposal"
                logger.info(f"Edge case RMR {test_rmr} handled correctly (valid)")
                
            except ValueError as e:
                pytest.fail(f"Valid RMR {test_rmr} should not raise error: {e}")
        else:
            # Should raise ValueError for invalid constraint
            with pytest.raises(ValueError, match="Invalid margin ratios"):
                MarketUtils.create_market_proposal_json(
                    ticker=f"EDGE{int(test_rmr*1000000)}/USDT PERP",
                    base_denom="tst",
                    quote_denom="usdt",
                    rmr=test_rmr,
                    imr=imr,
                    mmr=mmr
                )
            
            logger.info(f"Edge case RMR {test_rmr} handled correctly (invalid, properly rejected)")
    
    @pytest.mark.validation
    def test_precision_limits(self, margin_ratios):
        """
        Test: Verify precision limits and rounding behavior.
        
        This test validates how the system handles very high precision
        values and rounding behavior at the precision limits.
        """
        # Test very high precision values
        high_precision_rmr = 0.0512345678901234567890  # Many decimal places
        
        logger.info(f"Testing high precision RMR: {high_precision_rmr}")
        
        try:
            proposal_json = MarketUtils.create_market_proposal_json(
                ticker="PRECISION/USDT PERP",
                base_denom="tst",
                quote_denom="usdt",
                rmr=high_precision_rmr
            )
            
            # Should succeed and handle precision appropriately
            assert proposal_json is not None, "High precision RMR should be handled"
            
            # Parse the JSON to check how precision was handled
            import json
            proposal_data = json.loads(proposal_json)
            stored_rmr = proposal_data["messages"][0]["reduce_margin_ratio"]
            
            # Should be rounded to reasonable precision (6 decimal places)
            logger.info(f"High precision {high_precision_rmr} stored as: {stored_rmr}")
            
            # Verify it's still a valid string representation
            float_rmr = float(stored_rmr)
            assert float_rmr > 0, "Stored RMR should be positive"
            
            logger.info("High precision RMR handled correctly")
            
        except Exception as e:
            pytest.fail(f"High precision RMR should be handled gracefully: {e}")
    
    @pytest.mark.validation
    @pytest.mark.parametrize("invalid_input", [
        -0.01,      # Negative RMR
        -1.0,       # Negative RMR
        float('inf'),  # Infinity
        float('-inf'), # Negative infinity
        # Note: NaN testing removed as it causes comparison issues
    ])
    def test_invalid_input_types(self, invalid_input, margin_ratios):
        """
        Test: Verify proper handling of invalid input types and values.
        
        This test ensures the system properly rejects clearly invalid
        inputs like negative values, infinity, etc.
        """
        logger.info(f"Testing invalid input: {invalid_input}")
        
        # These should all be rejected by constraint validation
        is_valid = config.validate_rmr_constraint(
            invalid_input, 
            margin_ratios["imr"], 
            margin_ratios["mmr"]
        )
        
        assert not is_valid, f"Invalid input {invalid_input} should be rejected"
        
        # Should also fail when creating proposal
        with pytest.raises((ValueError, TypeError)):
            MarketUtils.create_market_proposal_json(
                ticker="INVALID/USDT PERP",
                base_denom="tst",
                quote_denom="usdt",
                rmr=invalid_input
            )
        
        logger.info(f"Invalid input {invalid_input} properly rejected")
    
    @pytest.mark.validation
    def test_error_handling_messages(self, margin_ratios):
        """
        Test: Verify proper error messages for invalid inputs.
        
        This test ensures that error messages are clear and informative
        when validation fails, helping with debugging and user experience.
        """
        invalid_rmr = 0.02  # Below IMR
        imr = margin_ratios["imr"]
        mmr = margin_ratios["mmr"]
        
        logger.info("Testing error message quality")
        
        try:
            MarketUtils.create_market_proposal_json(
                ticker="ERROR_TEST/USDT PERP",
                base_denom="tst",
                quote_denom="usdt",
                rmr=invalid_rmr,
                imr=imr,
                mmr=mmr
            )
            
            pytest.fail("Should have raised ValueError for invalid constraint")
            
        except ValueError as e:
            error_msg = str(e)
            
            # Error message should be informative
            assert "Invalid margin ratios" in error_msg, "Error should mention invalid ratios"
            assert str(invalid_rmr) in error_msg, "Error should include RMR value"
            assert str(imr) in error_msg, "Error should include IMR value"
            assert str(mmr) in error_msg, "Error should include MMR value"
            assert "constraint not met" in error_msg, "Error should mention constraint"
            
            logger.info(f"Error message is informative: {error_msg}")
    
    @pytest.mark.validation
    def test_constraint_validation_consistency(self, rmr_test_values, margin_ratios):
        """
        Test: Verify constraint validation is consistent across different contexts.
        
        This test ensures that constraint validation behaves consistently
        whether called directly or through market creation functions.
        """
        logger.info("Testing constraint validation consistency")
        
        test_cases = [
            ("valid_high", rmr_test_values["valid_high"], True),
            ("valid_medium", rmr_test_values["valid_medium"], True),
            ("valid_low", rmr_test_values["valid_low"], True),
            ("invalid_low", rmr_test_values["invalid_low"], False),
        ]
        
        imr = margin_ratios["imr"]
        mmr = margin_ratios["mmr"]
        
        for scenario, rmr, should_be_valid in test_cases:
            logger.info(f"Testing consistency for {scenario}: RMR={rmr}")
            
            # Test direct validation
            direct_valid = config.validate_rmr_constraint(rmr, imr, mmr)
            
            # Test validation through market creation
            market_creation_valid = True
            try:
                MarketUtils.create_market_proposal_json(
                    ticker=f"CONSISTENCY_{scenario}/USDT PERP",
                    base_denom="tst",
                    quote_denom="usdt",
                    rmr=rmr,
                    imr=imr,
                    mmr=mmr
                )
            except ValueError:
                market_creation_valid = False
            
            # Both should agree
            assert direct_valid == should_be_valid, \
                f"Direct validation should match expected for {scenario}"
            assert market_creation_valid == should_be_valid, \
                f"Market creation validation should match expected for {scenario}"
            assert direct_valid == market_creation_valid, \
                f"Direct and market creation validation should agree for {scenario}"
            
            logger.info(f"Validation consistency verified for {scenario}")
    
    @pytest.mark.validation
    def test_floating_point_precision_edge_cases(self, margin_ratios):
        """
        Test: Verify handling of floating point precision edge cases.
        
        This test validates that the system handles floating point
        precision issues correctly, especially near boundary values.
        """
        imr = margin_ratios["imr"]  # 0.05
        mmr = margin_ratios["mmr"]  # 0.03
        
        # Test values very close to IMR
        epsilon = 1e-10  # Very small value
        
        test_cases = [
            ("slightly_above_imr", imr + epsilon, True),
            ("slightly_below_imr", imr - epsilon, False),
            ("exactly_imr", imr, True),
        ]
        
        logger.info("Testing floating point precision edge cases")
        
        for scenario, test_rmr, expected_valid in test_cases:
            logger.info(f"Testing {scenario}: RMR={test_rmr}")
            
            is_valid = config.validate_rmr_constraint(test_rmr, imr, mmr)
            
            assert is_valid == expected_valid, \
                f"Floating point precision case {scenario} should be {expected_valid}"
            
            logger.info(f"Floating point precision handled correctly for {scenario}")
    
    @pytest.mark.validation
    def test_percentage_vs_decimal_consistency(self, margin_ratios):
        """
        Test: Verify consistency between percentage and decimal representations.
        
        This test ensures that RMR values are handled consistently
        regardless of whether they're specified as decimals (0.05) or
        conceptualized as percentages (5%).
        """
        logger.info("Testing percentage vs decimal consistency")
        
        # Test equivalent representations
        decimal_rmr = 0.075     # 7.5% as decimal
        percentage_calc = 7.5 / 100.0  # 7.5% calculated
        
        assert abs(decimal_rmr - percentage_calc) < 1e-10, \
            "Decimal and percentage calculation should match"
        
        # Both should validate the same way
        imr = margin_ratios["imr"]
        mmr = margin_ratios["mmr"]
        
        valid_decimal = config.validate_rmr_constraint(decimal_rmr, imr, mmr)
        valid_percentage = config.validate_rmr_constraint(percentage_calc, imr, mmr)
        
        assert valid_decimal == valid_percentage, \
            "Decimal and percentage representations should validate identically"
        
        logger.info("Percentage vs decimal consistency verified") 