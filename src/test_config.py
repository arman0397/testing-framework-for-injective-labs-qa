"""
Test configuration module for Injective Chain RMR tests.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


class TestConfig:
    """Central configuration management for RMR tests."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize test configuration."""
        if config_file:
            load_dotenv(config_file)
        else:
            # Try to load from default location
            config_path = Path(__file__).parent.parent / "config" / "test_env.env"
            if config_path.exists():
                load_dotenv(config_path)
    
    # Injective Node Configuration
    @property
    def chain_id(self) -> str:
        return os.getenv("INJECTIVE_CHAIN_ID", "injective-1")
    
    @property
    def node_url(self) -> str:
        return os.getenv("INJECTIVE_NODE_URL", "tcp://localhost:26657")
    
    @property
    def grpc_url(self) -> str:
        return os.getenv("INJECTIVE_GRPC_URL", "localhost:9900")
    
    # Test Configuration
    @property
    def keyring_backend(self) -> str:
        return os.getenv("KEYRING_BACKEND", "test")
    
    @property
    def test_timeout(self) -> int:
        return int(os.getenv("TEST_TIMEOUT", "300"))
    
    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")
    
    # Test Keys
    @property
    def testcandidate_key(self) -> str:
        return os.getenv("TESTCANDIDATE_KEY", "testcandidate")
    
    @property
    def validator_key(self) -> str:
        return os.getenv("VALIDATOR_KEY", "val")
    
    @property
    def admin_key(self) -> str:
        return os.getenv("ADMIN_KEY", "testcandidate")
    
    # RMR Test Constants
    @property
    def rmr_test_values(self) -> Dict[str, float]:
        """Return test RMR values for different scenarios."""
        return {
            "valid_high": 0.15,     # 15% - Valid high RMR
            "valid_medium": 0.10,   # 10% - Valid medium RMR
            "valid_low": 0.05,      # 5% - Valid low RMR
            "invalid_low": 0.02,    # 2% - Too low (below IMR)
            "boundary": 0.035,      # 3.5% - Edge case
        }
    
    @property
    def margin_ratios(self) -> Dict[str, float]:
        """Standard margin ratios for testing."""
        return {
            "mmr": 0.03,  # 3% - Maintenance Margin Ratio
            "imr": 0.05,  # 5% - Initial Margin Ratio
        }
    
    def validate_rmr_constraint(self, rmr: float, imr: float, mmr: float) -> bool:
        """Validate RMR constraint: RMR >= IMR > MMR"""
        return rmr >= imr > mmr
    
    def get_cli_base_args(self) -> list:
        """Get base CLI arguments for injectived commands."""
        return [
            "--chain-id", self.chain_id,
            "--node", self.node_url,
            "--keyring-backend", self.keyring_backend,
            "--yes",  # Auto-confirm transactions
            "--output", "json",
        ]


# Global config instance
config = TestConfig() 