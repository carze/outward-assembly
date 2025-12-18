# Unit Testing Implementation Plan
## Outward Assembly Bioinformatics Pipeline

**Version**: 1.0
**Date**: December 2024
**Status**: Ready for Implementation

---

## Executive Summary

This document provides a comprehensive implementation plan for adding robust unit testing to the outward-assembly pipeline. The plan addresses critical gaps in test coverage that currently prevent safe optimization and enhancement of the codebase.

### Current State
- **Source Code**: ~2,451 lines across 13 Python modules
- **Test Code**: ~1,376 lines across 11 test files
- **Test-to-Source Ratio**: ~0.56 (industry target: 1.0-2.0)
- **Estimated Coverage**: ~56%

### Critical Findings

**Production Risks Identified**:
1. **Four core modules have zero test coverage**: `execution_state.py` (148 LOC), `strategy.py` (55 LOC), `kmer_freq_filter.py` (249 LOC), `strategy_helper.py` (18 LOC)
2. **External tool failures not tested**: Subprocess calls to MEGAHIT, BBDuk, and KMC lack error handling tests
3. **State management untested**: Configuration parsing, time limits, and iteration tracking have no coverage

**Goals**:
- Achieve >80% overall line coverage
- >90% coverage for critical modules (execution_state, pipeline, decision_manager)
- 100+ unit tests, 20+ integration tests
- Comprehensive error path testing
- Enable safe refactoring and optimization

### Implementation Timeline
**8-week phased approach** with immediate priorities on critical gaps, followed by systematic coverage expansion, quality refinement, and CI/CD integration.

---

## Table of Contents

1. [Current State Assessment](#current-state-assessment)
2. [Critical Gaps & Risk Analysis](#critical-gaps--risk-analysis)
3. [Testing Strategy & Architecture](#testing-strategy--architecture)
4. [Implementation Roadmap](#implementation-roadmap)
5. [Module-Specific Testing Plans](#module-specific-testing-plans)
6. [Testing Standards & Best Practices](#testing-standards--best-practices)
7. [Quality Assurance & Metrics](#quality-assurance--metrics)
8. [Code Examples & Templates](#code-examples--templates)
9. [CI/CD Integration](#cicd-integration)
10. [Troubleshooting & Maintenance](#troubleshooting--maintenance)

---

## Current State Assessment

### Well-Tested Modules (>80% coverage)

**`dedup.py` (351 LOC) - EXCELLENT**
- Test file: `tests/test_dedup.py` (610 LOC - ratio 1.74:1)
- Comprehensive coverage of minimizers, bucketing, graph operations
- **Quality**: Excellent - serves as model for other tests
- **Keep as reference** for testing patterns

**`basic_seq_operations.py` (84 LOC) - GOOD**
- Test file: `tests/test_basic_seq_operations.py` (79 LOC)
- Good edge case coverage
- **Minor enhancement**: Add property-based tests

**`io_helpers.py` (188 LOC) - GOOD WITH GAPS**
- Test file: `tests/test_io_helpers.py` (113 LOC)
- **Missing**: `s3_files_with_prefix`, `get_s3_paths_by_priority`, `load_config`

**`overlap_graph.py` (237 LOC) - MODERATE**
- Test file: `tests/test_overlap_graph.py` (81 LOC)
- **Missing**: Helper function coverage

### Partially Tested Modules (20-50% coverage)

**`actions.py` (19 LOC)**
- Basic tests exist (37 LOC)
- **Missing**: Edge cases, boundary conditions, state mutation safety

**`decision_manager.py` (40 LOC)**
- One parameterized test exists (54 LOC)
- **Missing**: Error handling, invalid strategies, automate=False scenarios

**`pipeline.py` (362 LOC) - CRITICAL GAP**
- Minimal unit testing (28 LOC)
- One slow integration test (95 LOC)
- **Missing**: ~90% of module logic including main loop, metrics computation, error handling

**`pipeline_steps.py` (685 LOC - LARGEST MODULE) - CRITICAL GAP**
- Only `_subset_contigs` tested
- **Missing**: External tool command construction, batch vs local modes, error handling

### Untested Modules (0% coverage) - HIGHEST PRIORITY

| Module | LOC | Risk Level | Impact |
|--------|-----|------------|--------|
| `execution_state.py` | 148 | **CRITICAL** | Config parsing errors → incorrect analysis, wasted compute |
| `kmer_freq_filter.py` | 249 | **HIGH** | Filtering errors → data corruption |
| `strategy.py` | 55 | **MEDIUM** | Decision errors → wasted resources |
| `strategy_helper.py` | 18 | **LOW** | TypedDict validation |

### Test Infrastructure Assessment

**Current Fixtures** (`tests/conftest.py`):
- `temp_workdir()` - Temporary directory
- `temp_empty_file()` - Empty file in temp dir

**Current Markers** (from `pyproject.toml`):
- `fast`, `slow`, `unit`, `integration`, `e2e`
- `requires_tools`, `requires_aws`

**Strengths**:
- Good marker system for categorization
- Clear fast/slow separation

**Weaknesses**:
- No S3 mocking fixtures
- No subprocess mocking fixtures
- No FASTA/FASTQ test data fixtures
- No config dictionary fixtures

---

## Critical Gaps & Risk Analysis

### Priority 1: CRITICAL - Must Fix Before Refactoring

#### 1.1 Untested State Management (execution_state.py)

**Risk**: Configuration errors cause runaway processes, premature termination, or data loss

**Failure Scenarios**:
- Invalid time format → process runs indefinitely
- Missing iteration limit → infinite loop
- Serialization bugs → cannot resume jobs

**Required Tests**:
```
✓ Config parsing with invalid YAML
✓ Missing required fields handling
✓ Time format validation (edge cases: "5", "5 days", "-5 hours")
✓ Default value application
✓ Limit checking at exact boundaries (off-by-one errors)
✓ YAML roundtrip (config → state → YAML → state)
✓ Clock changes during time limit checking
```

**Target Coverage**: 95%

#### 1.2 External Tool Error Handling (pipeline_steps.py)

**Risk**: Tool failures go undetected, pipeline continues with corrupt data

**Current Issue** (from quality review):
```python
# pipeline_steps.py:107
subprocess.run(["megahit", ...], check=True)
# Errors only logged to file, no validation that tools completed successfully
```

**Failure Scenario**:
MEGAHIT fails → empty contig file → pipeline processes empty file → user receives zero results with "success" status

**Required Tests**:
```
✓ Command construction for MEGAHIT, BBDuk, KMC
✓ Subprocess failure propagation
✓ Output file existence validation
✓ Output file non-empty validation
✓ Resource limit handling
✓ Batch vs local mode switching
```

**Target Coverage**: 75%

#### 1.3 Resource Leak Risk (pipeline.py)

**Risk**: Temporary directories not cleaned, disk fills over multiple runs

**Current Issue** (from quality review):
```python
# pipeline.py:309-362
tempfile.mkdtemp creates directory at line 309
Cleanup at line 359 in finally block
Exceptions between those lines may prevent cleanup
```

**Required Tests**:
```
✓ Cleanup on successful completion
✓ Cleanup on exception during assembly
✓ Cleanup on keyboard interrupt
✓ Multiple concurrent assemblies (no collision)
```

**Recommended Fix**: Use `tempfile.TemporaryDirectory` context manager

**Target Coverage**: 85%

### Priority 2: HIGH - Needed for Production Readiness

#### 2.1 K-mer Frequency Filtering (kmer_freq_filter.py)

**Risk**: Incorrect filtering corrupts biological data silently

**Required Tests**:
```
✓ KMC command construction
✓ Parallel execution management
✓ Temporary file cleanup
✓ Disk space handling
✓ Memory limit validation
✓ Empty result handling
✓ /tmp directory warnings
```

**Target Coverage**: 70%

#### 2.2 Decision Logic (decision_manager.py, strategy.py)

**Risk**: Automation makes poor decisions, wastes compute

**Required Tests**:
```
✓ Strategy loading errors
✓ Invalid strategy names
✓ Action composition (multiple sequential actions)
✓ State mutation safety
✓ Condition evaluation edge cases
✓ Missing metrics handling
```

**Target Coverage**: 95%

### Priority 3: MEDIUM - Project Conformance Issues

#### 3.1 Missing Type Hints in Tests

**Issue** (from quality review):
Project documentation (CLAUDE.md line 69) explicitly requires type hints, but test files lack them.

**Example Violation**:
```python
# Current (violates standard)
def test_increase_k():
    curr_exec_state = {"read_subset_k": 10}

# Required (conforms to standard)
def test_increase_k() -> None:
    curr_exec_state: Dict[str, int] = {"read_subset_k": 10}
```

**Action Required**: Add type annotations to all test functions and fixtures

#### 3.2 Inconsistent Test Organization

**Issue**: Tests exist at both `tests/` root and `tests/unit_tests/`, violating documented structure (CLAUDE.md lines 498-511)

**Current**:
```
tests/
├── test_dedup.py              # Should be in unit_tests/
├── test_basic_seq_operations.py  # Should be in unit_tests/
├── unit_tests/
│   ├── test_actions.py
│   └── test_decision_manager.py
```

**Required**:
```
tests/
├── unit_tests/
│   ├── test_dedup.py
│   ├── test_basic_seq_operations.py
│   ├── test_actions.py
│   └── test_decision_manager.py
├── integration/
│   └── test_pipeline.py
```

**Action Required**: Move root-level test files to `tests/unit_tests/`

---

## Testing Strategy & Architecture

### Test Categories

#### 1. Pure Unit Tests
**Modules**: `execution_state.py`, `actions.py`, `strategy.py`

**Approach**:
- Mock all file I/O
- Use in-memory data structures
- No external dependencies
- Fast execution (<1s per test)

**Example**:
```python
@pytest.mark.fast
@pytest.mark.unit
def test_from_config_invalid_time(minimal_config):
    minimal_config["decision"]["limits"]["compute_time"] = "5 minutes"

    with pytest.raises(ValueError, match="must be in hours"):
        ExecutionState.from_config(minimal_config)
```

#### 2. Integration Tests with Mocked Tools
**Modules**: `pipeline_steps.py`, `kmer_freq_filter.py`

**Approach**:
- Mock `subprocess.run` to verify command construction
- Use temporary files for I/O
- No actual tool execution
- Fast execution (<1s per test)

**Example**:
```python
@pytest.mark.fast
@pytest.mark.unit
def test_assemble_contigs_command(mocker, temp_workdir):
    mock_run = mocker.patch("subprocess.run")

    _assemble_contigs(temp_workdir, iter=1, freq_filter=False)

    # Verify correct megahit command construction
    call_args = mock_run.call_args_list[0][0][0]
    assert "megahit" in call_args
    assert "-k-list" in call_args
```

#### 3. Integration Tests with Real Tools
**Modules**: `pipeline_steps.py`, `kmer_freq_filter.py`

**Approach**:
- Use tiny test datasets (10 reads)
- Run actual MEGAHIT/BBDuk/KMC
- Mark as `@pytest.mark.slow` and `@pytest.mark.requires_tools`
- Run in CI only on PR/nightly

**Example**:
```python
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_tools
def test_megahit_real(temp_workdir, tiny_fastq_fixture):
    _assemble_contigs(temp_workdir, iter=1, freq_filter=False)

    # Verify output exists and is valid FASTA
    output = temp_workdir / "megahit_out_iter1-1/final.contigs.fa"
    assert output.exists()
    assert_fasta_valid(output)
```

#### 4. Property-Based Tests
**Modules**: `dedup.py`, `basic_seq_operations.py`

**Approach**:
- Use Hypothesis library
- Test invariants (e.g., reverse complement is an involution)
- Find edge cases automatically

**Example**:
```python
from hypothesis import given
from hypothesis.strategies import text

@given(text(alphabet="ACGT", min_size=1, max_size=100))
def test_reverse_complement_involution(seq):
    """RC(RC(x)) should equal x"""
    assert _reverse_complement(_reverse_complement(seq)) == seq
```

### Test Boundaries & Mocking Strategy

**Mock at System Boundaries**:
- ✓ Subprocess calls (`subprocess.run`)
- ✓ File system operations (where appropriate)
- ✓ AWS S3 operations (`boto3.client`)
- ✓ Time-dependent operations (`datetime.now`)

**Do NOT Mock**:
- ✗ Internal project functions (test actual behavior)
- ✗ BioPython (use with small test data)
- ✗ Standard library utilities (pathlib, etc.)

**Fixture Design Pattern**:
```python
# tests/conftest.py

@pytest.fixture
def mock_subprocess_success(mocker):
    """Mock successful subprocess execution"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    return mock_run

@pytest.fixture
def valid_config_dict():
    """Minimal valid configuration dictionary"""
    return {
        "assembly": {
            "input_seed_path": "/path/to/seed.fasta",
            "input_dataset_list": "/path/to/dataset.csv",
            "work_dir": "/tmp/work",
            "out_dir": "/tmp/output",
            "output_filename": "contigs.fasta",
        },
        "decision": {
            "automate": False,
            "strategy": None,
            "limits": {
                "compute_time": "5 hours",
                "iterations": 20,
            },
        },
    }
```

---

## Implementation Roadmap

### Phase 1: Foundation & Critical Gaps (Weeks 1-2)

**Goal**: Establish test infrastructure and cover highest-priority untested modules

#### Week 1: Infrastructure & execution_state.py

**Tasks**:
1. **Enhance test fixtures** (2 days)
   - Create `conftest.py` additions:
     - `valid_config_dict()` - Base configuration
     - `invalid_config_variants()` - Parameterized invalid configs
     - `mock_subprocess_success()` / `mock_subprocess_failure()`
     - `sample_fasta_file()` / `sample_fastq_pair()`
     - `mock_s3_client()`

2. **Test `execution_state.py` comprehensively** (3 days)
   - `TestExecutionStateFromConfig` class (~80 LOC)
     - Valid config parsing
     - Invalid time formats (parameterized)
     - Missing required fields
     - Default application
     - Automate without strategy error
   - `TestExecutionStateLimitChecking` class (~60 LOC)
     - At iteration limit (boundary testing)
     - One before limit (off-by-one)
     - At time limit
     - Just under time limit
   - `TestExecutionStateYAMLSerialization` class (~50 LOC)
     - to_yaml_config structure
     - Roundtrip fidelity
     - write_config file creation
   - **Target**: 95% coverage, ~200 LOC tests

#### Week 2: actions.py & decision_manager.py

**Tasks**:
1. **Complete `actions.py` testing** (1 day)
   - Edge cases: negative k, zero, MAX_INT
   - State immutability (functions don't mutate input)
   - Priority wrapping (next_priority at end of list)
   - **Target**: 100% coverage, ~80 LOC tests

2. **Complete `decision_manager.py` testing** (2 days)
   - `__init__` with invalid strategy names
   - `collect_actions` with missing strategy file
   - automate=False scenarios (should return empty list)
   - Strategy function exceptions
   - Multiple actions returned
   - **Target**: 95% coverage, ~120 LOC tests

3. **Reorganize tests for conformance** (1 day)
   - Move `test_dedup.py` → `tests/unit_tests/`
   - Move `test_basic_seq_operations.py` → `tests/unit_tests/`
   - Move `test_overlap_graph.py` → `tests/unit_tests/`
   - Move `test_io_helpers.py` → `tests/unit_tests/`
   - Update import paths if needed

**Phase 1 Deliverables**:
- Enhanced `conftest.py` with 10+ new fixtures
- `tests/unit_tests/test_execution_state.py` (~200 LOC)
- Enhanced `tests/unit_tests/test_actions.py` (~80 LOC)
- Enhanced `tests/unit_tests/test_decision_manager.py` (~120 LOC)
- Reorganized test directory structure

### Phase 2: External Tool Integration (Weeks 3-4)

**Goal**: Test all external tool invocations with proper mocking

#### Week 3: pipeline_steps.py - Command Construction

**Tasks**:
1. **Create `tests/unit_tests/test_pipeline_steps_commands.py`** (4 days)
   - `TestAssembleContigs` class (~150 LOC)
     - Without frequency filtering (2 assemblies)
     - With frequency filtering (3 assemblies)
     - K-list parameter validation
     - Output directory naming
     - Subprocess failure propagation
   - `TestPrepareQuerySeqs` class (~40 LOC)
     - Sequence selection logic
     - Edge cases (empty input)
   - `TestCopyIterationReads` class (~30 LOC)
     - File copying logic
     - Error handling
   - **Target**: 40% coverage of module, ~220 LOC tests

#### Week 4: kmer_freq_filter.py & pipeline_steps.py Part 2

**Tasks**:
1. **Create `tests/unit_tests/test_kmer_freq_filter.py`** (3 days)
   - `TestMakeKmerCountCommands` class (~100 LOC)
     - Basic command construction
     - Multiple files
     - Max count calculation (parameterized)
     - Thread/memory parameters
   - `TestHighFreqKmersSplitFiles` class (~80 LOC)
     - /tmp directory rejection
     - /tmp directory warning
     - Nonexistent workdir rejection
     - Parallel execution parameter
   - **Target**: 60% coverage, ~180 LOC tests

2. **Expand pipeline_steps.py testing** (2 days)
   - `_choose_best_subiter` logic (~40 LOC)
   - `_fasta_longest_total` parsing (~30 LOC)
   - **Target**: 60% coverage of module total

**Phase 2 Deliverables**:
- `tests/unit_tests/test_pipeline_steps_commands.py` (~300 LOC total)
- `tests/unit_tests/test_kmer_freq_filter.py` (~180 LOC)
- Subprocess mocking patterns documented

### Phase 3: Pipeline Orchestration (Week 5)

**Goal**: Test main pipeline logic and iteration management

**Tasks**:
1. **Create `tests/unit_tests/test_pipeline_logic.py`** (3 days)
   - `TestComputeIterationMetrics` class (~60 LOC)
     - Various iteration states
     - Empty data handling
   - `TestComputeAssemblyMetrics` class (~40 LOC)
     - Edge cases (zero iterations)
     - Timing calculations
   - `TestOutwardAssembly` class (~80 LOC)
     - Parameter validation
     - Error handling
     - Cleanup verification (mock TemporaryDirectory)
   - **Target**: 50% coverage of pipeline.py, ~180 LOC tests

2. **Add integration points testing** (2 days)
   - `_subset_contigs` extended scenarios
   - Batch vs local mode switching
   - **Target**: 65% coverage of pipeline_steps.py

**Phase 3 Deliverables**:
- `tests/unit_tests/test_pipeline_logic.py` (~180 LOC)
- Cleanup and resource management tests

### Phase 4: Strategy & Helpers (Week 6)

**Goal**: Complete coverage of smaller modules

**Tasks**:
1. **Test `strategy.py` and `strategy_helper.py`** (2 days)
   - `tests/unit_tests/test_strategy.py` (~80 LOC)
     - `example_strategy` all branches
     - Condition evaluation
     - Action generation
   - `tests/unit_tests/test_strategy_helper.py` (~20 LOC)
     - TypedDict validation
   - **Target**: 100% coverage for both

2. **Complete `io_helpers.py` testing** (2 days)
   - `s3_files_with_prefix` with mocked boto3
   - `get_s3_paths_by_priority` validation
   - `dir_to_s3_paths` logic
   - `load_config` error handling
   - **Target**: 95% coverage, +80 LOC tests

3. **Add type hints to all test files** (1 day)
   - Review all test files for missing type hints
   - Add return types (-> None) to test functions
   - Add parameter types to fixtures
   - Add types to test variables where clarity helps

**Phase 4 Deliverables**:
- `tests/unit_tests/test_strategy.py` (~80 LOC)
- `tests/unit_tests/test_strategy_helper.py` (~20 LOC)
- Enhanced `tests/unit_tests/test_io_helpers.py` (+80 LOC)
- Type hints added throughout test suite

### Phase 5: Integration & Refinement (Week 7)

**Goal**: Integration tests with real tools, coverage analysis

**Tasks**:
1. **Create integration tests with real tools** (3 days)
   - `tests/integration/test_tools_integration.py` (~150 LOC)
     - Small-scale MEGAHIT assembly (10 reads)
     - BBDuk adapter trimming (tiny dataset)
     - KMC k-mer counting (tiny dataset)
     - All marked `@pytest.mark.slow` and `@pytest.mark.requires_tools`

2. **Coverage analysis** (1 day)
   - Run pytest with --cov plugin
   - Generate HTML coverage report
   - Identify critical uncovered lines
   - Create targeted tests for gaps

3. **Refactor and document tests** (1 day)
   - Add docstrings to complex tests
   - Extract common patterns to fixtures
   - Update CLAUDE.md with testing guidelines

**Phase 5 Deliverables**:
- `tests/integration/test_tools_integration.py` (~150 LOC)
- Coverage report showing >80% overall
- Updated CLAUDE.md

### Phase 6: Documentation & CI/CD (Week 8)

**Goal**: Testing documentation and automation

**Tasks**:
1. **Create testing documentation** (2 days)
   - Create `TESTING.md` with:
     - How to run tests (fast/slow/integration)
     - How to add new tests
     - Fixture usage guide
     - Mocking strategies
     - Coverage expectations
   - Update CLAUDE.md testing section
   - Document common test patterns

2. **CI/CD integration** (2 days)
   - Update `.github/workflows/ci.yml`:
     - Fast tests on every push
     - Integration tests on PR
     - Coverage reporting to Codecov
   - Add coverage badge to README
   - Configure pytest-xdist for parallel execution

3. **Final review and polish** (1 day)
   - Review all test code for consistency
   - Ensure all tests have docstrings
   - Fix any flaky tests
   - Verify coverage targets met

**Phase 6 Deliverables**:
- `TESTING.md` documentation
- Updated CI/CD workflow
- Coverage badge in README
- Final test suite review report

---

## Module-Specific Testing Plans

### execution_state.py - State Management (Priority 1)

**Coverage Target**: 95%

**Test Classes**:
1. `TestExecutionStateFromConfig` - Config parsing and validation
2. `TestExecutionStateLimitChecking` - Time and iteration limits
3. `TestExecutionStateYAMLSerialization` - Serialization roundtrip
4. `TestExecutionStateUpdate` - State mutation

**Key Test Cases**:
```python
# Boundary testing for limits
test_check_limits_at_exact_iteration_boundary()
test_check_limits_one_before_iteration_limit()

# Time format validation (parameterized)
@pytest.mark.parametrize("invalid_time", [
    "5",           # missing unit
    "hours",       # missing number
    "5 days",      # wrong unit
    "-5 hours",    # negative
])
test_from_config_invalid_time_format(invalid_time)

# Roundtrip fidelity
test_yaml_roundtrip()  # config → state → yaml → state
```

**Example Implementation**: See [Code Examples](#code-examples--templates) section below

### pipeline_steps.py - Tool Integration (Priority 1)

**Coverage Target**: 75%

**Test Classes**:
1. `TestAssembleContigs` - MEGAHIT command construction
2. `TestAdapterTrim` - BBDuk command construction
3. `TestSubsetReads` - Read filtering logic
4. `TestChooseBestSubiter` - Assembly selection

**Key Test Cases**:
```python
# Command construction verification
test_assemble_contigs_without_freq_filter()
test_assemble_contigs_with_freq_filter()
test_assemble_contigs_k_list_parameter()

# Error handling
test_assemble_contigs_subprocess_failure()
test_assemble_contigs_missing_input_files()

# Output validation
test_assemble_contigs_creates_subdirectories()
test_assemble_contigs_output_file_exists()
```

### kmer_freq_filter.py - Filtering (Priority 2)

**Coverage Target**: 70%

**Test Classes**:
1. `TestMakeKmerCountCommands` - KMC command construction
2. `TestHighFreqKmersSplitFiles` - Parallel execution orchestration

**Key Test Cases**:
```python
# Command construction
test_command_construction_basic()
test_command_construction_multiple_files()

# Max count calculation (power of 2)
@pytest.mark.parametrize("min_freq,expected_max_count", [
    (100, 256),
    (1000, 2048),
    (2000, 4096),
])
test_max_count_calculation(min_freq, expected_max_count)

# Safety checks
test_tmp_directory_rejection()
test_tmp_directory_warning()
test_nonexistent_workdir_rejection()
```

### strategy.py - Decision Logic (Priority 2)

**Coverage Target**: 100%

**Test Classes**:
1. `TestExampleStrategy` - Conditional logic and action generation

**Key Test Cases**:
```python
# Branch coverage for all conditions
test_example_strategy_increase_k_condition()
test_example_strategy_decrease_k_condition()
test_example_strategy_next_priority_condition()
test_example_strategy_no_action_condition()

# Edge cases
test_example_strategy_missing_metrics()
test_example_strategy_invalid_state()
```

---

## Testing Standards & Best Practices

### Naming Conventions

**Test Files**:
- Unit tests: `tests/unit_tests/test_<module_name>.py`
- Integration tests: `tests/integration/test_<feature_name>.py`
- Match source module structure

**Test Functions**:
```python
def test_<function_name>_<scenario>_<expected_outcome>():
    """Test that <function> behaves correctly when <scenario>"""
```

**Examples**:
```python
def test_from_config_missing_required_field_raises_keyerror():
    """Test that from_config raises KeyError when required field missing"""

def test_assemble_contigs_with_freq_filter_creates_three_assemblies():
    """Test that _assemble_contigs creates 3 assemblies when freq_filter=True"""
```

### Test Structure - AAA Pattern

All tests should follow Arrange-Act-Assert:

```python
def test_function_scenario():
    """Clear description of what is being tested"""
    # Arrange: Set up test data and dependencies
    config = {"key": "value"}
    state = create_test_state(config)

    # Act: Execute the function under test
    result = function_under_test(state, param=123)

    # Assert: Verify the outcome
    assert result.status == "success"
    assert result.value == expected_value
```

### Documentation Standards

**Every test must have a docstring**:
```python
def test_check_limits_at_exact_iteration_boundary(execution_state_fixture):
    """Test limit checking when current_outer_iterations equals max_outer_iterations.

    This is a boundary condition that should trigger the limit check to return True,
    preventing further iterations. Tests for off-by-one errors.
    """
```

**Use comments for complex setup**:
```python
def test_complex_scenario():
    """Test complex multi-step scenario"""
    # Create state with specific iteration count to trigger edge case
    state = ExecutionState.from_config(config)
    state.current_outer_iterations = 19  # One before limit of 20

    # Advance time to just under limit
    state.start_time = datetime.now() - timedelta(hours=4, minutes=59)  # 1min before 5hr limit

    assert state.check_limits() is False
```

### Assertion Best Practices

**Prefer specific assertions**:
```python
# Good
assert result.contig_count == 5
assert output_path.exists()
assert "error" in log_message.lower()

# Avoid (too generic)
assert result is not None
assert True
```

**Use pytest helpers**:
```python
# Testing exceptions
with pytest.raises(ValueError, match="missing required field"):
    ExecutionState.from_config(invalid_config)

# Testing warnings
with pytest.warns(UserWarning, match="memory-backed"):
    process_in_tmp_dir(workdir)

# Approximate equality
assert result.value == pytest.approx(expected, rel=1e-5)
```

### Parametrization Guidelines

Use `@pytest.mark.parametrize` for variants of the same test:

```python
@pytest.mark.parametrize("k_value,expected_output", [
    (15, "small_kmer_result"),
    (21, "medium_kmer_result"),
    (31, "large_kmer_result"),
])
def test_kmer_filtering_by_size(k_value, expected_output):
    """Test k-mer filtering produces correct output for different k values"""
    result = filter_by_kmer(k=k_value)
    assert result == expected_output
```

### Type Hints in Tests

**All test functions and fixtures must have type hints** (project standard):

```python
from typing import Dict, Any
import pytest

@pytest.fixture
def valid_config_dict() -> Dict[str, Any]:
    """Minimal valid configuration dictionary"""
    return {
        "assembly": {
            "input_seed_path": "/path/to/seed.fasta",
            # ...
        }
    }

def test_from_config_valid(valid_config_dict: Dict[str, Any]) -> None:
    """Test that valid config creates ExecutionState successfully"""
    state: ExecutionState = ExecutionState.from_config(valid_config_dict)

    assert state.input_seed_path == "/path/to/seed.fasta"
```

---

## Quality Assurance & Metrics

### Coverage Targets by Module

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| `execution_state.py` | 0% | **95%** | CRITICAL |
| `pipeline.py` | 10% | **85%** | CRITICAL |
| `pipeline_steps.py` | 5% | **75%** | CRITICAL |
| `decision_manager.py` | 30% | **95%** | HIGH |
| `kmer_freq_filter.py` | 5% | **70%** | HIGH |
| `strategy.py` | 0% | **100%** | MEDIUM |
| `actions.py` | 60% | **100%** | MEDIUM |
| `io_helpers.py` | 70% | **90%** | MEDIUM |
| `overlap_graph.py` | 60% | **85%** | MEDIUM |
| `dedup.py` | 95% | **95%** | LOW (maintain) |
| `basic_seq_operations.py` | 85% | **90%** | LOW |
| `strategy_helper.py` | 0% | **100%** | LOW |
| **OVERALL** | **~56%** | **>80%** | - |

### Test Quality Checklist

Use this checklist when reviewing new tests:

- [ ] **Type hints** present on test function and fixtures
- [ ] **Docstring** explains WHAT is tested and WHY
- [ ] **Test name** follows pattern `test_<function>_<scenario>_<expected>`
- [ ] **One assertion concept** per test (multiple asserts OK if same concept)
- [ ] **No magic numbers** - use named constants or explain in comments
- [ ] **Error cases tested**, not just happy path
- [ ] **Mocks used** for external dependencies (subprocess, network, filesystem)
- [ ] **Marked appropriately** with pytest markers (fast/slow, unit/integration)
- [ ] **AAA pattern** followed (Arrange-Act-Assert)
- [ ] **Test is independent** - doesn't rely on other test state

### Coverage Measurement Commands

**Setup**:
```bash
uv add --dev pytest-cov
```

**Run tests with coverage**:
```bash
# All tests
uv run pytest tests/ --cov=outward_assembly --cov-report=html --cov-report=term

# Fast tests only
uv run pytest -m fast --cov=outward_assembly --cov-report=term

# Specific module with missing lines
uv run pytest tests/unit_tests/test_execution_state.py \
    --cov=outward_assembly.execution_state \
    --cov-report=term-missing

# Generate HTML report
uv run pytest --cov=outward_assembly --cov-report=html
open htmlcov/index.html
```

### Success Metrics

**Quantitative**:
- [ ] Overall line coverage > 80%
- [ ] Critical modules > 90% coverage
- [ ] All modules > 60% coverage
- [ ] >100 unit tests total
- [ ] >20 integration tests
- [ ] Test code > 2,500 lines (currently 1,376)
- [ ] Fast test suite < 30 seconds
- [ ] Full test suite < 5 minutes

**Qualitative**:
- [ ] All tests follow AAA pattern
- [ ] Consistent naming conventions
- [ ] No flaky tests (0% failure on re-run)
- [ ] All complex tests documented
- [ ] Fixtures eliminate test duplication

### Production Readiness Criteria

**Before refactoring is safe**:
- [ ] All 4 untested modules have 80%+ coverage
- [ ] External tool failures tested via mocking
- [ ] State management edge cases covered
- [ ] Configuration validation comprehensive
- [ ] Type hints added to test code
- [ ] Test organization matches documentation

**Before production-ready**:
- [ ] Integration tests cover AWS batch failures
- [ ] Data integrity validation tests
- [ ] Error recovery tests (partial assembly restart)
- [ ] Performance regression baseline established

---

## Code Examples & Templates

### Example 1: execution_state.py Tests

```python
# tests/unit_tests/test_execution_state.py

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
from outward_assembly.execution_state import ExecutionState


class TestExecutionStateFromConfig:
    """Tests for ExecutionState.from_config class method"""

    @pytest.fixture
    def minimal_valid_config(self) -> Dict[str, Any]:
        """Absolute minimum valid configuration"""
        return {
            "assembly": {
                "input_seed_path": "/path/to/seed.fasta",
                "input_dataset_list": "/path/to/dataset.csv",
                "work_dir": "/tmp/work",
                "out_dir": "/tmp/output",
                "output_filename": "contigs.fasta",
            },
            "decision": {
                "automate": False,
                "strategy": None,
                "limits": {
                    "compute_time": "5 hours",
                    "iterations": 20,
                },
            },
        }

    @pytest.mark.fast
    @pytest.mark.unit
    def test_from_config_minimal_valid(self, minimal_valid_config: Dict[str, Any]) -> None:
        """Test that minimal valid config creates ExecutionState successfully"""
        state: ExecutionState = ExecutionState.from_config(minimal_valid_config)

        assert state.input_seed_path == "/path/to/seed.fasta"
        assert state.max_outer_iterations == 20
        assert state.max_compute_time == timedelta(hours=5)
        assert state.automate is False
        assert state.current_outer_iterations == 0

    @pytest.mark.fast
    @pytest.mark.unit
    @pytest.mark.parametrize("invalid_time,error_pattern", [
        ("5", "cannot parse time"),
        ("hours", "cannot parse time"),
        ("5 minutes", "must be in hours"),
        ("-5 hours", "time cannot be negative"),
        ("0 hours", "time must be positive"),
    ])
    def test_from_config_invalid_time_format(
        self,
        minimal_valid_config: Dict[str, Any],
        invalid_time: str,
        error_pattern: str
    ) -> None:
        """Test that invalid time formats raise appropriate errors"""
        minimal_valid_config["decision"]["limits"]["compute_time"] = invalid_time

        with pytest.raises(ValueError, match=error_pattern):
            ExecutionState.from_config(minimal_valid_config)


class TestExecutionStateLimitChecking:
    """Tests for ExecutionState.check_limits method"""

    @pytest.mark.fast
    @pytest.mark.unit
    def test_check_limits_at_iteration_limit(self, execution_state_fixture: ExecutionState) -> None:
        """Test that check_limits returns True when at iteration limit.

        This is a boundary condition - when current equals max, we should stop.
        Tests for off-by-one errors.
        """
        state = execution_state_fixture
        state.current_outer_iterations = 20
        state.max_outer_iterations = 20

        assert state.check_limits() is True

    @pytest.mark.fast
    @pytest.mark.unit
    def test_check_limits_one_before_iteration_limit(self, execution_state_fixture: ExecutionState) -> None:
        """Test that check_limits returns False one iteration before limit.

        When current is 19 and max is 20, we should allow one more iteration.
        """
        state = execution_state_fixture
        state.current_outer_iterations = 19
        state.max_outer_iterations = 20

        assert state.check_limits() is False
```

### Example 2: pipeline_steps.py Tests

```python
# tests/unit_tests/test_pipeline_steps_commands.py

import pytest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from outward_assembly.pipeline_steps import _assemble_contigs


class TestAssembleContigs:
    """Tests for _assemble_contigs function"""

    @pytest.mark.fast
    @pytest.mark.unit
    def test_assemble_contigs_without_freq_filter(
        self,
        mocker: Any,
        temp_workdir: Path
    ) -> None:
        """Test that _assemble_contigs generates correct megahit commands without filtering"""
        mock_run: MagicMock = mocker.patch("subprocess.run")

        # Create required input files
        (temp_workdir / "reads_1.fastq").write_text("@r1\nACGT\n+\nIIII\n")
        (temp_workdir / "reads_2.fastq").write_text("@r1\nTGCA\n+\nIIII\n")
        (temp_workdir / "log.txt").touch()

        _assemble_contigs(temp_workdir, iter=1, freq_filter=False)

        # Should call subprocess.run twice (standard + permissive assemblies)
        assert mock_run.call_count == 2

        # Check first call (standard assembly)
        first_call = mock_run.call_args_list[0][0][0]
        assert "megahit" in first_call
        assert "-1" in first_call
        assert str(temp_workdir / "reads_1.fastq") in first_call
        assert "-2" in first_call
        assert str(temp_workdir / "reads_2.fastq") in first_call

    @pytest.mark.fast
    @pytest.mark.unit
    def test_assemble_contigs_k_list_parameter(
        self,
        mocker: Any,
        temp_workdir: Path
    ) -> None:
        """Test that megahit k-list parameter is correctly set"""
        mock_run: MagicMock = mocker.patch("subprocess.run")

        # Setup
        (temp_workdir / "reads_1.fastq").touch()
        (temp_workdir / "reads_2.fastq").touch()
        (temp_workdir / "log.txt").touch()

        _assemble_contigs(temp_workdir, iter=1, freq_filter=False)

        # Check k-list in all calls
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            assert "--k-list" in cmd
            k_list_idx = cmd.index("--k-list")
            assert cmd[k_list_idx + 1] == "15,21,29,39,59,79,99,119,141"
```

### Test Template

Use this template for new test files:

```python
"""
Unit tests for outward_assembly.<module_name>

This module tests <brief description>.
"""

import pytest
from typing import Any, Dict
from outward_assembly.<module> import function_under_test


class TestFunctionName:
    """Tests for function_name function

    This test class covers:
    - Normal operation scenarios
    - Edge cases and boundary conditions
    - Error handling
    """

    @pytest.fixture
    def sample_input(self) -> Dict[str, Any]:
        """Sample valid input for function_name"""
        return {"key": "value"}

    @pytest.mark.fast
    @pytest.mark.unit
    def test_function_name_normal_case(self, sample_input: Dict[str, Any]) -> None:
        """Test that function_name behaves correctly with valid input"""
        # Arrange
        expected_result = "expected"

        # Act
        result = function_under_test(sample_input)

        # Assert
        assert result == expected_result

    @pytest.mark.fast
    @pytest.mark.unit
    def test_function_name_empty_input(self) -> None:
        """Test that function_name handles empty input correctly"""
        # Arrange
        empty_input: Dict[str, Any] = {}

        # Act & Assert
        with pytest.raises(ValueError, match="cannot be empty"):
            function_under_test(empty_input)
```

---

## CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  fast-tests:
    name: Fast Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --extra dev

      - name: Run fast tests with coverage
        run: |
          uv run pytest -m fast \
            --cov=outward_assembly \
            --cov-report=xml \
            --cov-report=term

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --extra dev

      - name: Install bioinformatics tools
        run: |
          # Install MEGAHIT, BBTools, KMC via conda/mamba
          wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
          bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
          source $HOME/miniconda/bin/activate
          conda install -c bioconda megahit bbmap kmc -y

      - name: Run integration tests
        run: |
          source $HOME/miniconda/bin/activate
          uv run pytest -m "integration and not requires_aws"

  coverage-gate:
    name: Coverage Gate
    runs-on: ubuntu-latest
    needs: fast-tests
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --extra dev

      - name: Check coverage threshold
        run: |
          uv run pytest tests/ \
            --cov=outward_assembly \
            --cov-fail-under=80 \
            --cov-report=term
```

### Test Categorization for CI

**Fast Tests** (run on every commit):
- All unit tests with mocked dependencies
- Execution time: <30 seconds total
- Mark with `@pytest.mark.fast`

**Integration Tests** (run on PR):
- Tests with real tools on small datasets
- Execution time: 1-5 minutes total
- Mark with `@pytest.mark.integration` and `@pytest.mark.requires_tools`

**E2E Tests** (run on PR to main):
- Full pipeline tests with AWS
- Execution time: 5-30 minutes
- Mark with `@pytest.mark.e2e` and `@pytest.mark.requires_aws`

### Parallel Execution

Install pytest-xdist:
```bash
uv add --dev pytest-xdist
```

Run tests in parallel:
```bash
# Auto-detect CPU count
uv run pytest -n auto tests/

# Specific number of workers
uv run pytest -n 4 tests/
```

---

## Troubleshooting & Maintenance

### Common Test Issues

#### Issue 1: Flaky Tests

**Symptom**: Tests sometimes pass, sometimes fail for same code

**Causes**:
- Time-dependent assertions
- Race conditions
- Non-deterministic test data
- External state dependencies

**Solutions**:
```python
# Bad: Time-dependent
def test_timeout():
    time.sleep(1)
    assert time_elapsed > 1.0  # Flaky on slow CI

# Good: Mock time
def test_timeout(mocker):
    mock_time = mocker.patch("time.time")
    mock_time.side_effect = [0, 1.5]  # Deterministic
    assert check_timeout()

# Bad: Random data
def test_sort():
    data = [random.randint(0, 100) for _ in range(10)]

# Good: Fixed seed
def test_sort():
    random.seed(42)  # Deterministic
    data = [random.randint(0, 100) for _ in range(10)]
```

#### Issue 2: Slow Test Suite

**Symptom**: Test suite takes too long, developers skip running it

**Solutions**:
1. Profile slow tests:
   ```bash
   uv run pytest --durations=10 tests/
   ```

2. Mark and separate slow tests:
   ```python
   @pytest.mark.slow
   def test_large_dataset():
       # ...
   ```

3. Use parallel execution:
   ```bash
   uv run pytest -n auto -m fast
   ```

#### Issue 3: Mock Not Working

**Symptom**: Test still calls real function despite mock

**Common Causes**:
```python
# Wrong: Patching after import
from module import function
mocker.patch("module.function")  # Doesn't work!

# Right: Patch where it's used
mocker.patch("module_under_test.function")

# Wrong: Patching wrong module
mocker.patch("subprocess.run")  # If imported as 'from subprocess import run'

# Right: Patch where imported
mocker.patch("outward_assembly.pipeline_steps.run")
```

### Maintaining Tests Over Time

#### When Code Changes

**If you modify a function**:
1. Run existing tests for that module
2. If tests fail, determine if:
   - Bug in your code (fix code)
   - Intentional behavior change (update tests)
   - Test was too brittle (refactor test)

**If you add a parameter**:
1. Update existing test calls
2. Add tests for new parameter variations
3. Test backward compatibility if parameter is optional

**If you refactor internal logic**:
- Unit tests should NOT break (they test interface, not implementation)
- If tests break, they were too coupled to implementation
- Refactor tests to test behavior, not implementation details

#### When to Write New Tests

**Always write tests for**:
- New functions (at least one happy path test)
- New error conditions
- Bug fixes (regression test)
- Complex logic (multiple scenarios)

**Optional tests for**:
- Trivial getters/setters
- One-line functions
- Logging statements

### Test Debt Management

**Weekly**:
- Review test failures in CI
- Fix any flaky tests
- Keep test execution time under targets

**Monthly**:
- Run coverage analysis
- Identify new gaps from recent code changes
- Update test documentation if patterns change

**Quarterly**:
- Review and update this implementation plan
- Assess if coverage targets still appropriate
- Update fixtures for new common patterns

---

## Appendices

### Appendix A: Required Testing Libraries

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    "black",
    "pytest~=8.3.4",
    "pytest-mock~=3.12.0",    # Mocking support
    "pytest-cov~=4.1.0",      # Coverage measurement
    "pytest-xdist~=3.5.0",    # Parallel execution
    "pytest-timeout~=2.2.0",  # Prevent hanging tests
    "ruff",
    "ipython",
]
```

Install:
```bash
uv sync --extra dev
```

### Appendix B: Test Markers Reference

From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "fast: Quick unit tests (< 1s)",
    "slow: Slow tests (> 1s)",
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End to end tests",
    "requires_tools: Requires bioinformatics tools (megahit, bbduk, etc.)",
    "requires_aws: Requires AWS credentials and services",
]
```

Usage:
```bash
# Run only fast tests
pytest -m fast

# Run all except slow
pytest -m "not slow"

# Run integration tests without AWS
pytest -m "integration and not requires_aws"

# Run unit and integration, but not slow
pytest -m "(unit or integration) and not slow"
```

### Appendix C: Coverage Badge

Add to `README.md`:
```markdown
![Tests](https://github.com/carze/outward-assembly/actions/workflows/test.yml/badge.svg)
![Coverage](https://codecov.io/gh/carze/outward-assembly/branch/main/graph/badge.svg)
```

### Appendix D: Useful Commands Cheat Sheet

```bash
# Run fast tests only
uv run pytest -m fast

# Run with coverage
uv run pytest --cov=outward_assembly --cov-report=html

# Run specific test file
uv run pytest tests/unit_tests/test_execution_state.py

# Run specific test
uv run pytest tests/unit_tests/test_actions.py::test_increase_k

# Run with verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x

# Run tests in parallel
uv run pytest -n auto

# Show slowest 10 tests
uv run pytest --durations=10

# Run tests that failed last time
uv run pytest --lf

# Run tests modified since last commit
uv run pytest --testmon
```

---

## Summary & Next Steps

### Summary

This implementation plan provides a structured 8-week approach to achieve comprehensive unit testing coverage for the outward-assembly pipeline. The plan addresses:

1. **Critical Production Risks** - Untested modules and error handling
2. **Project Conformance** - Type hints and test organization
3. **Quality Standards** - Coverage targets and test review criteria
4. **Maintainability** - Documentation and CI/CD integration

### Immediate Next Steps

1. **Review & Approve** (1 day)
   - Team review of this plan
   - Adjust timeline if needed
   - Assign implementation responsibilities

2. **Begin Phase 1** (Week 1-2)
   - Set up enhanced fixtures in `conftest.py`
   - Create `tests/unit_tests/test_execution_state.py`
   - Achieve 95% coverage of `execution_state.py`

3. **Track Progress**
   - Run weekly coverage reports
   - Update this document with actual progress
   - Adjust plan based on learnings

### Success Criteria

By completion of this 8-week plan:
- ✓ >80% overall coverage
- ✓ >90% coverage on critical modules
- ✓ 100+ unit tests, 20+ integration tests
- ✓ All production risks mitigated
- ✓ Safe to refactor and optimize codebase

### Questions or Issues

For questions about this plan or testing in general:
1. Review CLAUDE.md testing section
2. Check existing test files as examples
3. Consult with team members
4. Update this document with learnings

---

**Document Version**: 1.0
**Last Updated**: December 2024
**Next Review**: After Phase 1 completion
