#!/usr/bin/env python3
"""
Test runner script for Injective RMR tests.

This script provides a convenient way to run the RMR test suite
with various options and configurations.
"""

import argparse
import sys
import subprocess
import os
import json
import re
from datetime import datetime
from pathlib import Path


def update_execution_log(test_type, command, output, returncode, start_time, end_time):
    """
    Update TEST_EXECUTION_LOG.md with the execution report.
    
    Args:
        test_type: Type of tests run
        command: Command that was executed
        output: Combined stdout/stderr output
        returncode: Exit code from the test run
        start_time: Test execution start time
        end_time: Test execution end time
    """
    duration = end_time - start_time
    log_file = Path(__file__).parent / "TEST_EXECUTION_LOG.md"
    
    # Parse test results from output
    passed_match = re.search(r'(\d+) passed', output)
    failed_match = re.search(r'(\d+) failed', output)
    error_match = re.search(r'(\d+) error', output)
    skipped_match = re.search(r'(\d+) skipped', output)
    
    passed = int(passed_match.group(1)) if passed_match else 0
    failed = int(failed_match.group(1)) if failed_match else 0
    errors = int(error_match.group(1)) if error_match else 0
    skipped = int(skipped_match.group(1)) if skipped_match else 0
    
    total = passed + failed + errors + skipped
    
    # Status based on results
    if returncode == 0 and failed == 0 and errors == 0:
        status = "✅ PASSED"
        status_icon = "🎉"
    elif failed > 0 or errors > 0:
        status = "❌ FAILED"
        status_icon = "🚨"
    else:
        status = "⚠️ PARTIAL"
        status_icon = "⚠️"
    
    # Create execution report
    report = f"""
---

## {status_icon} **Test Execution Report**

**📅 Execution Date**: {start_time.strftime('%B %d, %Y at %H:%M:%S')}  
**⏱️ Duration**: {duration.total_seconds():.2f} seconds  
**🧪 Test Type**: {test_type.title() if test_type else 'All Tests'}  
**📊 Status**: {status}  
**🔧 Command**: `{' '.join(command)}`

### **📈 Test Results Summary**

| Metric | Count | Percentage |
|--------|-------|------------|
| **✅ Passed** | {passed} | {(passed/total*100):.1f}% |
| **❌ Failed** | {failed} | {(failed/total*100):.1f}% |
| **🚨 Errors** | {errors} | {(errors/total*100):.1f}% |
| **⏭️ Skipped** | {skipped} | {(skipped/total*100):.1f}% |
| **📊 Total** | {total} | 100.0% |

### **🔍 Detailed Output**

```bash
{output}
```

### **💡 Execution Notes**

- **Exit Code**: {returncode}
- **Python Version**: {sys.version.split()[0]}
- **Working Directory**: {os.getcwd()}
- **Log File**: `logs/test_execution.log`

---
"""
    
    # Read existing content
    if log_file.exists():
        with open(log_file, 'r') as f:
            existing_content = f.read()
    else:
        existing_content = """# Test Execution Logs - RMR Automated Tests

**Project**: Injective RMR Feature Testing Suite  
**Purpose**: Automated execution logs for comprehensive RMR testing  
**Auto-Generated**: This file is automatically updated after each test run

"""
    
    # Append new report
    updated_content = existing_content + report
    
    # Write back to file
    with open(log_file, 'w') as f:
        f.write(updated_content)
    
    print(f"\n📝 Execution report added to TEST_EXECUTION_LOG.md")
    print(f"📊 Results: {passed} passed, {failed} failed, {errors} errors, {skipped} skipped")


def run_tests(test_type=None, verbose=False, parallel=False, coverage=False):
    """
    Run the RMR test suite.
    
    Args:
        test_type: Type of tests to run ('governance', 'updates', 'validation', or None for all)
        verbose: Enable verbose output
        parallel: Run tests in parallel
        coverage: Generate coverage reports
    """
    start_time = datetime.now()
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Create logs directory if it doesn't exist
    logs_dir = script_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Base pytest command
    cmd = ["python3", "-m", "pytest"]
    
    # Add verbose flag
    if verbose:
        cmd.append("-v")
    
    # Add parallel execution
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # Add coverage
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
    
    # Add test type filter
    if test_type:
        cmd.extend(["-m", test_type])
    
    # Add test path
    cmd.append("tests/")
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        # Capture both stdout and stderr
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        end_time = datetime.now()
        
        # Print output to console (for real-time feedback)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        # Combine output for logging
        combined_output = ""
        if result.stdout:
            combined_output += result.stdout
        if result.stderr:
            combined_output += "\n" + result.stderr
        
        # Update execution log
        update_execution_log(
            test_type=test_type,
            command=cmd,
            output=combined_output.strip(),
            returncode=result.returncode,
            start_time=start_time,
            end_time=end_time
        )
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run Injective RMR test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                    # Run all tests
  python run_tests.py -t governance      # Run only governance tests
  python run_tests.py -t updates -v      # Run update tests with verbose output
  python run_tests.py -t validation -c   # Run validation tests with coverage
  python run_tests.py --parallel         # Run all tests in parallel
  python run_tests.py --smoke           # Run smoke tests only
        """
    )
    
    parser.add_argument(
        "-t", "--test-type",
        choices=["governance", "updates", "validation"],
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage reports (requires pytest-cov)"
    )
    
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run smoke tests only (subset of fast tests)"
    )
    
    parser.add_argument(
        "--slow",
        action="store_true",
        help="Include slow tests (governance tests)"
    )
    
    args = parser.parse_args()
    
    # Handle smoke tests
    if args.smoke:
        start_time = datetime.now()
        # Run a subset of fast validation tests
        cmd = ["python3", "-m", "pytest", "-v", "-m", "validation and not slow", "tests/"]
        if args.coverage:
            cmd.extend(["--cov=src", "--cov-report=term"])
        
        print(f"Running smoke tests: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            end_time = datetime.now()
            
            # Print output to console
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            
            # Combine output for logging
            combined_output = ""
            if result.stdout:
                combined_output += result.stdout
            if result.stderr:
                combined_output += "\n" + result.stderr
            
            # Update execution log
            update_execution_log(
                test_type="smoke",
                command=cmd,
                output=combined_output.strip(),
                returncode=result.returncode,
                start_time=start_time,
                end_time=end_time
            )
            
            return result.returncode
            
        except Exception as e:
            print(f"Error running smoke tests: {e}")
            return 1
    
    # Set test type based on --slow flag
    test_type = args.test_type
    if args.slow and not test_type:
        test_type = "governance"
    
    return run_tests(
        test_type=test_type,
        verbose=args.verbose,
        parallel=args.parallel,
        coverage=args.coverage
    )


if __name__ == "__main__":
    sys.exit(main()) 