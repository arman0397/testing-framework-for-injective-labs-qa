#!/usr/bin/env python3
"""
Mock Injective CLI for demonstration purposes.
This simulates the injectived CLI to show how governance tests would work.
"""

import json
import sys
import time
import random
from pathlib import Path

# Mock blockchain state
MOCK_BLOCK_HEIGHT = 1000000
MOCK_STATE_FILE = "/tmp/mock_injective_state.json"

# Load persistent state
def load_state():
    try:
        if Path(MOCK_STATE_FILE).exists():
            with open(MOCK_STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"proposals": {}, "markets": {}}

def save_state(state):
    try:
        with open(MOCK_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except:
        pass

# Initialize state
_state = load_state()
MOCK_PROPOSALS = _state.get("proposals", {})
MOCK_MARKETS = _state.get("markets", {})
MOCK_ACCOUNTS = {
    "testcandidate": "inj1testcandidate123456789",
    "val": "inj1validator123456789"
}

def mock_query_block():
    """Mock query block command."""
    return {
        "block": {
            "header": {
                "height": str(MOCK_BLOCK_HEIGHT + random.randint(0, 10))
            }
        }
    }

def mock_query_proposal(proposal_id):
    """Mock query proposal command."""
    if proposal_id in MOCK_PROPOSALS:
        return MOCK_PROPOSALS[proposal_id]
    else:
        return {
            "proposal": {
                "id": proposal_id,
                "status": "PROPOSAL_STATUS_PASSED",
                "final_tally_result": {
                    "yes_count": "1000000",
                    "no_count": "0"
                }
            }
        }

def mock_submit_proposal(proposal_file, from_key):
    """Mock submit proposal command."""
    proposal_id = str(random.randint(1, 1000))
    
    # Read proposal to extract market info
    with open(proposal_file, 'r') as f:
        proposal_data = json.load(f)
    
    # Store mock proposal
    MOCK_PROPOSALS[proposal_id] = {
        "proposal": {
            "id": proposal_id,
            "status": "PROPOSAL_STATUS_VOTING_PERIOD",
            "content": proposal_data
        }
    }
    
    # Extract market info to store in mock markets when proposal passes
    messages = proposal_data.get("messages", [])
    if messages:
        market_info = messages[0]
        ticker = market_info.get("ticker", "")
        market_id = f"market_{proposal_id}"
        
        # Store market for later retrieval
        MOCK_MARKETS[market_id] = {
            "market_id": market_id,
            "ticker": ticker,
            "reduce_margin_ratio": market_info.get("reduce_margin_ratio", "0.1"),
            "initial_margin_ratio": market_info.get("initial_margin_ratio", "0.05"),
            "maintenance_margin_ratio": market_info.get("maintenance_margin_ratio", "0.03"),
            "status": "ACTIVE"
        }
    
    # Save state to file
    save_state({"proposals": MOCK_PROPOSALS, "markets": MOCK_MARKETS})
    
    return {
        "txhash": f"0x{random.randint(100000, 999999)}",
        "code": 0,
        "events": [
            {
                "type": "submit_proposal", 
                "attributes": [
                    {"key": "proposal_id", "value": proposal_id}
                ]
            }
        ],
        "raw_log": f'[{{"msg_index":0,"events":[{{"type":"submit_proposal","attributes":[{{"key":"proposal_id","value":"{proposal_id}"}}]}}]}}]'
    }

def mock_vote_proposal(proposal_id, vote, from_key):
    """Mock vote on proposal."""
    if proposal_id in MOCK_PROPOSALS:
        MOCK_PROPOSALS[proposal_id]["proposal"]["status"] = "PROPOSAL_STATUS_PASSED"
        # Save state to file
        save_state({"proposals": MOCK_PROPOSALS, "markets": MOCK_MARKETS})
    
    return {
        "txhash": f"0x{random.randint(100000, 999999)}",
        "code": 0
    }

def mock_query_perpetual_markets():
    """Mock query all perpetual markets."""
    markets = []
    for market_id, market_data in MOCK_MARKETS.items():
        markets.append({
            "market": market_data
        })
    return {
        "markets": markets
    }

def mock_query_market(market_id):
    """Mock query specific market."""
    if market_id in MOCK_MARKETS:
        return {"market": MOCK_MARKETS[market_id]}
    else:
        return {"error": f"Market {market_id} not found"}

def mock_update_market(market_id, rmr, from_key):
    """Mock update market admin command."""
    if market_id in MOCK_MARKETS:
        MOCK_MARKETS[market_id]["reduce_margin_ratio"] = rmr
        return {
            "txhash": f"0x{random.randint(100000, 999999)}",
            "code": 0
        }
    else:
        return {"code": 1, "error": "Market not found"}

def mock_keys_show(key_name):
    """Mock keys show command."""
    if key_name in MOCK_ACCOUNTS:
        return {"output": MOCK_ACCOUNTS[key_name]}
    else:
        return {"error": "Key not found"}

def main():
    """Main CLI entry point."""
    args = sys.argv[1:]
    
    try:
        if len(args) == 0:
            print("Usage: demo_cli_mock.py <command> [args...]")
            return
        
        # Remove common flags for simplicity
        filtered_args = [arg for arg in args if not arg.startswith('--')]
        
        if filtered_args[0] == "query":
            if filtered_args[1] == "block":
                result = mock_query_block()
            elif filtered_args[1] == "gov" and filtered_args[2] == "proposal":
                result = mock_query_proposal(filtered_args[3])
            elif filtered_args[1] == "exchange":
                if filtered_args[2] == "perpetual-markets":
                    result = mock_query_perpetual_markets()
                elif filtered_args[2] == "perpetual-market-info":
                    result = mock_query_market(filtered_args[3])
                else:
                    result = {"error": "Unknown exchange query"}
            else:
                result = {"error": "Unknown query command"}
        
        elif filtered_args[0] == "tx":
            if filtered_args[1] == "gov":
                if filtered_args[2] == "submit-proposal":
                    from_idx = args.index("--from") + 1
                    result = mock_submit_proposal(filtered_args[3], args[from_idx])
                elif filtered_args[2] == "vote":
                    from_idx = args.index("--from") + 1
                    result = mock_vote_proposal(filtered_args[3], filtered_args[4], args[from_idx])
                else:
                    result = {"error": "Unknown gov tx command"}
            elif filtered_args[1] == "exchange":
                if filtered_args[2] == "admin-update-perpetual-market":
                    rmr_idx = args.index("--reduce-margin-ratio") + 1
                    from_idx = args.index("--from") + 1
                    result = mock_update_market(filtered_args[3], args[rmr_idx], args[from_idx])
                else:
                    result = {"error": "Unknown exchange tx command"}
            else:
                result = {"error": "Unknown tx command"}
        
        elif filtered_args[0] == "keys":
            if filtered_args[1] == "show":
                result = mock_keys_show(filtered_args[2])
            else:
                result = {"error": "Unknown keys command"}
        
        else:
            result = {"error": f"Unknown command: {filtered_args[0]}"}
        
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main() 