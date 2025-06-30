"""
Pytest configuration and fixtures for RMR tests.
"""

import pytest
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from injective_cli import cli, InjectiveCLIError
from test_config import config
from market_utils import MarketUtils


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "test_execution.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def injective_node():
    """
    Ensure Injective node is running and accessible.
    """
    logger.info("Checking Injective node connection...")
    
    try:
        # Try to get latest block height
        height = cli.get_latest_block_height()
        logger.info(f"Connected to Injective node at block height: {height}")
        
        if height == 0:
            pytest.fail("Node is not producing blocks")
            
        return {"height": height, "connected": True}
        
    except Exception as e:
        pytest.fail(f"Failed to connect to Injective node: {e}")


@pytest.fixture(scope="session")
def test_keys(injective_node):
    """
    Verify test keys are available.
    """
    logger.info("Verifying test keys...")
    
    keys_to_check = [
        config.testcandidate_key,
        config.validator_key,
        config.admin_key
    ]
    
    available_keys = {}
    
    for key_name in keys_to_check:
        try:
            account_info = cli.get_account_info(key_name)
            available_keys[key_name] = account_info.get("output", "")
            logger.info(f"Key '{key_name}' is available")
        except InjectiveCLIError as e:
            logger.error(f"Key '{key_name}' not found: {e}")
            pytest.fail(f"Required key '{key_name}' not found")
    
    return available_keys


@pytest.fixture(scope="session")
def market_templates():
    """
    Load market templates from configuration.
    """
    templates_file = Path(__file__).parent.parent / "config" / "market_templates.json"
    
    if not templates_file.exists():
        pytest.fail(f"Market templates file not found: {templates_file}")
    
    try:
        with open(templates_file, 'r') as f:
            templates = json.load(f)
        
        logger.info(f"Loaded {len(templates.get('templates', {}))} market templates")
        return templates
        
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to parse market templates: {e}")


@pytest.fixture
def unique_ticker():
    """
    Generate a unique ticker for each test.
    """
    import uuid
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    return f"TEST{timestamp}{unique_id}/USDT PERP"


@pytest.fixture
def clean_test_market(unique_ticker, test_keys):
    """
    Create a clean test market for each test.
    Returns market ID and cleans up after test.
    """
    market_id = None
    
    try:
        # Create market with default RMR
        rmr = config.rmr_test_values["valid_medium"]  # 10%
        
        proposal_json = MarketUtils.create_market_proposal_json(
            ticker=unique_ticker,
            base_denom="tst",
            quote_denom="usdt",
            rmr=rmr
        )
        
        logger.info(f"Creating test market: {unique_ticker}")
        proposal_id = MarketUtils.submit_and_pass_proposal(proposal_json)
        
        # Wait for market creation
        time.sleep(10)
        
        # Find created market
        market = MarketUtils.get_market_by_ticker(unique_ticker)
        if not market:
            pytest.fail(f"Failed to create test market: {unique_ticker}")
        
        market_id = market.get("market", {}).get("market_id", "")
        logger.info(f"Created test market {unique_ticker} with ID: {market_id}")
        
        yield {
            "market_id": market_id,
            "ticker": unique_ticker,
            "rmr": rmr,
            "proposal_id": proposal_id
        }
        
    except Exception as e:
        logger.error(f"Failed to create test market: {e}")
        pytest.fail(f"Test market creation failed: {e}")
    
    finally:
        # Cleanup would go here if needed
        # For now, we'll leave test markets as they don't interfere
        logger.info(f"Test completed for market: {unique_ticker}")


@pytest.fixture
def rmr_test_values():
    """
    Provide RMR test values from configuration.
    """
    return config.rmr_test_values


@pytest.fixture
def margin_ratios():
    """
    Provide standard margin ratios.
    """
    return config.margin_ratios


def pytest_configure(config):
    """
    Configure pytest with custom markers.
    """
    config.addinivalue_line(
        "markers", "governance: tests for governance flow"
    )
    config.addinivalue_line(
        "markers", "updates: tests for market updates"
    )
    config.addinivalue_line(
        "markers", "validation: tests for validation logic"
    )
    config.addinivalue_line(
        "markers", "slow: tests that take longer to run"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers automatically.
    """
    for item in items:
        # Add slow marker to governance tests
        if "governance" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        
        # Add markers based on filename
        if "test_rmr_governance" in item.nodeid:
            item.add_marker(pytest.mark.governance)
        elif "test_rmr_updates" in item.nodeid:
            item.add_marker(pytest.mark.updates)
        elif "test_rmr_validation" in item.nodeid:
            item.add_marker(pytest.mark.validation)


@pytest.fixture(autouse=True)
def test_logging(request):
    """
    Log test start and end for each test.
    """
    logger.info(f"Starting test: {request.node.name}")
    
    yield
    
    logger.info(f"Completed test: {request.node.name}")


# Error handling fixture
@pytest.fixture
def handle_cli_errors():
    """
    Fixture to handle CLI errors gracefully in tests.
    """
    def _handle_error(func, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except InjectiveCLIError as e:
            logger.error(f"CLI Error in test: {e}")
            pytest.fail(f"CLI command failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in test: {e}")
            pytest.fail(f"Unexpected error: {e}")
    
    return _handle_error 