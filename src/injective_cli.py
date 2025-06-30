"""
CLI wrapper for injectived commands.

This module provides Python wrappers around the injectived CLI,
with proper error handling, JSON parsing, and retry logic.
"""

import json
import subprocess
import time
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from test_config import config


logger = logging.getLogger(__name__)


class InjectiveCLIError(Exception):
    """Custom exception for CLI command errors."""
    pass


class InjectiveCLI:
    """Wrapper for injectived CLI commands."""
    
    def __init__(self, binary_path: str = "injectived"):
        """Initialize CLI wrapper."""
        self.binary_path = binary_path
        self.base_args = config.get_cli_base_args()
    
    def _run_command(self, cmd: List[str], retry_count: int = 3) -> Dict[str, Any]:
        """
        Execute a CLI command with retry logic.
        
        Args:
            cmd: Command arguments list
            retry_count: Number of retries on failure
            
        Returns:
            Parsed JSON response
            
        Raises:
            InjectiveCLIError: On command failure
        """
        full_cmd = [self.binary_path] + cmd + self.base_args
        
        for attempt in range(retry_count):
            try:
                logger.info(f"Executing command (attempt {attempt + 1}): {' '.join(full_cmd)}")
                
                result = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.test_timeout,
                    check=False
                )
                
                if result.returncode == 0:
                    if result.stdout.strip():
                        try:
                            return json.loads(result.stdout)
                        except json.JSONDecodeError:
                            # Some commands return plain text
                            return {"output": result.stdout.strip()}
                    else:
                        return {"success": True}
                else:
                    error_msg = f"Command failed with code {result.returncode}: {result.stderr}"
                    logger.error(error_msg)
                    
                    if attempt < retry_count - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise InjectiveCLIError(error_msg)
                        
            except subprocess.TimeoutExpired:
                error_msg = f"Command timed out after {config.test_timeout} seconds"
                logger.error(error_msg)
                
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise InjectiveCLIError(error_msg)
            
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(error_msg)
                
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise InjectiveCLIError(error_msg)
        
        raise InjectiveCLIError("All retry attempts failed")
    
    def query_market(self, market_id: str) -> Dict[str, Any]:
        """Query perpetual market by ID."""
        cmd = ["query", "exchange", "perpetual-market-info", market_id]
        return self._run_command(cmd)
    
    def query_all_markets(self) -> Dict[str, Any]:
        """Query all perpetual markets."""
        cmd = ["query", "exchange", "perpetual-markets"]
        return self._run_command(cmd)
    
    def create_market_proposal(self, proposal_json: str, from_key: str) -> Dict[str, Any]:
        """
        Submit a governance proposal to create a perpetual market.
        
        Args:
            proposal_json: JSON string or file path containing proposal
            from_key: Key name to submit proposal from
            
        Returns:
            Transaction result
        """
        # Check if it's a file path or JSON string
        if Path(proposal_json).exists():
            cmd = ["tx", "gov", "submit-proposal", proposal_json, "--from", from_key]
        else:
            # Write JSON to temporary file
            temp_file = Path("/tmp/market_proposal.json")
            temp_file.write_text(proposal_json)
            cmd = ["tx", "gov", "submit-proposal", str(temp_file), "--from", from_key]
        
        return self._run_command(cmd)
    
    def vote_proposal(self, proposal_id: str, vote: str, from_key: str) -> Dict[str, Any]:
        """Vote on a governance proposal."""
        cmd = ["tx", "gov", "vote", proposal_id, vote, "--from", from_key]
        return self._run_command(cmd)
    
    def query_proposal(self, proposal_id: str) -> Dict[str, Any]:
        """Query governance proposal status."""
        cmd = ["query", "gov", "proposal", proposal_id]
        return self._run_command(cmd)
    
    def update_market_admin(self, market_id: str, rmr: str, from_key: str) -> Dict[str, Any]:
        """
        Update market parameters via admin message.
        
        Args:
            market_id: Market ID to update
            rmr: New RMR value as string (e.g., "0.1")
            from_key: Admin key name
            
        Returns:
            Transaction result
        """
        cmd = [
            "tx", "exchange", "admin-update-perpetual-market",
            market_id,
            "--reduce-margin-ratio", rmr,
            "--from", from_key
        ]
        return self._run_command(cmd)
    
    def get_account_info(self, key_name: str) -> Dict[str, Any]:
        """Get account information for a key."""
        cmd = ["keys", "show", key_name, "--address"]
        return self._run_command(cmd)
    
    def wait_for_next_block(self, blocks: int = 1) -> None:
        """Wait for specified number of blocks."""
        logger.info(f"Waiting for {blocks} block(s)...")
        time.sleep(blocks * 3)  # Assume ~3 second block time
    
    def get_latest_block_height(self) -> int:
        """Get the current block height."""
        cmd = ["query", "block"]
        result = self._run_command(cmd)
        return int(result.get("block", {}).get("header", {}).get("height", 0))


# Global CLI instance
cli = InjectiveCLI() 