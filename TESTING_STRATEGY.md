# RMR Testing Strategy

## Overview
This document outlines the comprehensive testing strategy for validating the Reduce-Margin-Ratio (RMR) feature in Injective Protocol's perpetual markets.

## Test Scope

### In Scope
1. **RMR Parameter Integration**
   - Market creation with RMR values via governance
   - RMR storage and retrieval from blockchain state
   - RMR updates via admin messages

2. **Constraint Validation**
   - Mathematical constraint enforcement: RMR ≥ IMR > MMR
   - Edge case and boundary value testing
   - Invalid input rejection and error handling

3. **Data Integrity**
   - Precision handling for RMR values
   - Persistence across blockchain queries
   - Update idempotency and consistency

### Out of Scope
- Liquidation engine behavior with RMR
- Position decrease edge cases during trading
- Performance testing under high load
- Cross-chain RMR synchronization

## Test Categories

### 1. Governance Flow Testing
**Objective**: Verify RMR integration in market creation process

**Test Cases**:
- Create perpetual markets with various RMR values
- Verify RMR constraint enforcement during governance
- Test invalid RMR rejection mechanisms
- Validate RMR precision handling

**Success Criteria**:
- Markets created successfully with valid RMR values
- Invalid RMR constraints properly rejected
- RMR values stored accurately in blockchain state

### 2. Market Update Testing  
**Objective**: Validate RMR update functionality via admin messages

**Test Cases**:
- Update existing market RMR values
- Test constraint validation during updates
- Verify authorization requirements
- Test update persistence and idempotency

**Success Criteria**:
- RMR updates execute successfully with valid values
- Invalid updates are rejected with clear errors
- Updated values persist across queries

### 3. Validation Logic Testing
**Objective**: Ensure robust constraint enforcement and error handling

**Test Cases**:
- Mathematical constraint validation (RMR ≥ IMR > MMR)
- Edge case and boundary value testing
- Invalid input type and value testing
- Floating-point precision edge cases

**Success Criteria**:
- Constraints enforced consistently across all contexts
- Edge cases handled gracefully
- Clear, informative error messages for invalid inputs

## Test Environment

### Requirements
- Local Injective node with test configuration
- Test keys with appropriate permissions
- Python 3.8+ with pytest framework
- CLI access to `injectived` binary

### Setup
1. Configure test environment variables
2. Import test keys to keyring
3. Verify node connectivity and permissions
4. Run smoke tests to validate setup

## Test Data Strategy

### RMR Test Values
```python
{
    "valid_high": 0.15,     # 15% - Above IMR
    "valid_medium": 0.10,   # 10% - Above IMR  
    "valid_low": 0.05,      # 5% - Equal to IMR (boundary)
    "invalid_low": 0.02,    # 2% - Below IMR (invalid)
    "boundary": 0.035,      # 3.5% - Edge case testing
    "precision": 0.051234   # High precision testing
}
```

### Market Templates
- Standard perpetual market configuration
- High-precision market setup
- Low-fee market variant
- Custom oracle configurations

## Execution Strategy

### Test Execution Order
1. **Setup Validation** - Verify environment and connectivity
2. **Smoke Tests** - Quick validation tests (~2 minutes)
3. **Validation Tests** - Constraint and edge case testing (~5 minutes)
4. **Update Tests** - Market update functionality (~10 minutes)  
5. **Governance Tests** - Full governance flow (~15 minutes)

### Parallel Execution
- Validation tests can run in parallel (independent)
- Governance tests should run sequentially (create markets)
- Update tests require existing markets from governance tests

### Retry Strategy
- Network operations: 3 retries with exponential backoff
- Governance proposals: Wait for voting period completion
- Market updates: Verify state changes before proceeding

## Risk Mitigation

### Potential Risks
1. **Network Connectivity Issues**
   - Mitigation: Comprehensive retry logic and timeouts
   
2. **Key Permission Issues**  
   - Mitigation: Pre-test key validation and clear error messages
   
3. **Governance Timing Issues**
   - Mitigation: Proper wait times and state verification
   
4. **Precision Loss in RMR Values**
   - Mitigation: Tolerance-based comparison and validation

### Fallback Procedures
- Local test data for offline validation testing
- Mock CLI responses for unit testing
- Alternative test keys for permission testing

## Reporting

### Success Metrics
- **Test Coverage**: >95% of RMR functionality covered
- **Pass Rate**: 100% for valid scenarios
- **Error Coverage**: All invalid scenarios properly rejected
- **Performance**: Tests complete within 30 minutes

### Test Reports
- Detailed pytest HTML report with test results
- Coverage report showing code coverage percentage  
- Execution logs with timestamps and details
- Summary report with pass/fail statistics

## Maintenance

### Test Data Updates
- Update RMR test values when chain parameters change
- Refresh market templates for new oracle types
- Update CLI commands for new injective versions

### Environment Updates
- Monitor for Injective protocol upgrades
- Update Python dependencies regularly
- Refresh test keys when needed
- Update documentation with changes

## Conclusion

This testing strategy ensures comprehensive validation of the RMR feature while maintaining efficiency and reliability. The multi-layered approach covers functional requirements, edge cases, and error conditions to provide confidence in the RMR implementation. 