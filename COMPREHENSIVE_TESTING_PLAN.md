# Comprehensive Unit Testing Implementation Plan
## Outward Assembly Pipeline

**Generated**: December 2024
**Repository**: outward-assembly
**Current Test Coverage**: ~1,376 lines of test code / ~2,451 lines of source code (56% ratio)

---

## Executive Summary

This document provides a detailed implementation plan for comprehensive unit testing of the outward-assembly bioinformatics pipeline. The analysis identifies significant gaps in test coverage, particularly for core pipeline orchestration modules, configuration management, and external tool integration points.

**Key Findings:**
- **Well-tested modules**: `dedup.py`, `basic_seq_operations.py`, `io_helpers.py`, `overlap_graph.py`
- **Partially tested modules**: `actions.py`, `decision_manager.py`, `pipeline.py`
- **Untested modules**: `execution_state.py`, `kmer_freq_filter.py`, `strategy.py`, `strategy_helper.py`, `pipeline_steps.py` (685 LOC - largest module)
- **Test infrastructure**: Basic fixtures exist; needs expansion for complex scenarios

---

## Part 1: Current State Assessment

### 1.1 Existing Test Coverage Analysis

#### Fully Tested Modules (>80% coverage estimate)

**`dedup.py` (351 LOC) - EXCELLENT COVERAGE**
- Test file: `tests/test_dedup.py` (610 LOC)
- Coverage areas:
  - Helper functions: reverse complement, canonical k-mer, mismatch counting
  - Minimizer extraction: normal windows, N-bases, edge cases
  - Sequence matching: exact matches, offsets, error thresholds
  - Read pair equivalence: strict/tolerant orientation modes
  - Bucketing: correct assignment, multiple buckets, duplicate detection
  - Graph operations: building graphs, duplicate detection, component selection
  - End-to-end deduplication: empty input, identical sequences, multiple clusters
- **Quality**: Comprehensive with unit and integration tests, parameterized tests, edge cases

**`basic_seq_operations.py` (84 LOC) - GOOD COVERAGE**
- Test file: `tests/test_basic_seq_operations.py` (79 LOC)
- Coverage areas:
  - `is_subseq`: empty strings, exact matches, substring matching, reverse complement
  - `contig_ids_by_seed`: multiple seeds, orientation detection
- **Quality**: Good coverage of main functions with edge cases

**`io_helpers.py` (188 LOC) - GOOD COVERAGE**
- Test file: `tests/test_io_helpers.py` (113 LOC)
- Coverage areas:
  - `process_s3_paths`: valid/invalid paths, filename generation
  - `_count_lines`: empty files, files without newlines
  - `concat_and_tag_fastq`: multiple files, empty files, error conditions
- **Gaps**: Missing tests for `s3_files_with_prefix`, `dir_to_s3_paths`, `get_s3_paths_by_priority`, `load_config`

**`overlap_graph.py` (237 LOC) - MODERATE COVERAGE**
- Test file: `tests/test_overlap_graph.py` (81 LOC)
- Coverage areas:
  - `get_overlapping_sequence_ids`: multiple seeds, connected components
  - `_traverse_subgraph_and_orient`: graph traversal, orientation propagation
- **Gaps**: Missing tests for other helper functions in the module

#### Partially Tested Modules (20-50% coverage estimate)

**`actions.py` (19 LOC) - BASIC COVERAGE**
- Test file: `tests/unit_tests/test_actions.py` (37 LOC)
- Coverage: Basic tests for `increase_k`, `decrease_k`, `next_priority`
- **Gaps**: No edge case testing (negative values, boundary conditions, state mutations)

**`decision_manager.py` (40 LOC) - BASIC COVERAGE**
- Test file: `tests/unit_tests/test_decision_manager.py` (54 LOC)
- Coverage: One parameterized test for `collect_actions`
- **Gaps**:
  - No tests for `__init__` error handling
  - No tests for missing/invalid strategies
  - No tests for automate=False scenarios
  - No tests for strategy function failures

**`pipeline.py` (362 LOC) - MINIMAL COVERAGE**
- Test files:
  - `tests/unit_tests/test_pipeline_metrics.py` (28 LOC)
  - `tests/integration/test_pipeline.py` (95 LOC)
- Coverage:
  - One unit test for `_compute_assembly_metrics` with empty iterations
  - One integration test for full pipeline (slow, requires AWS)
- **Gaps**:
  - No unit tests for `_compute_iteration_metrics`
  - No unit tests for `_outward_main_loop` logic
  - No tests for error conditions, parameter validation
  - No tests for cleanup behavior
  - Missing ~90% of the module's logic

**`pipeline_steps.py` (685 LOC - LARGEST MODULE) - MINIMAL COVERAGE**
- Test file: `tests/integration/test_pipeline_steps.py` (100+ LOC)
- Coverage: Only `_subset_contigs` tested
- **Gaps**: Most functions untested:
  - `_assemble_contigs`
  - `_prepare_query_seqs`
  - `_subset_split_files` (local and batch versions)
  - `_adapter_trim_iter_reads`
  - `_frequency_filter_reads`
  - `_copy_iteration_reads`
  - `_choose_best_subiter`
  - `_fasta_longest_total`
  - `_record_inputs`
  - Helper functions for batch processing

#### Untested Modules (0% coverage)

**`execution_state.py` (148 LOC) - NO TESTS**
- Critical module for state management
- Needs tests for:
  - `from_config`: parsing, validation, defaults, error handling
  - `get_adjustable_parameters`: dictionary conversion
  - `update_adjustable_parameters`: state updates, iteration counting
  - `check_limits`: time limits, iteration limits, boundary conditions
  - `to_yaml_config`: serialization correctness
  - `write_config`: file I/O, formatting

**`kmer_freq_filter.py` (249 LOC) - NO TESTS**
- Integration test exists (`test_kmer_counting.py`) but no unit tests
- Needs tests for:
  - `_make_kmer_count_commands`: command construction, parameter validation
  - `_high_freq_kmers_split_files`: directory validation, error handling
  - `frequency_filter_reads`: full workflow, error conditions

**`strategy.py` (55 LOC) - NO TESTS**
- Contains user-facing strategy functions
- Needs tests for:
  - `example_strategy`: all conditional branches, action generation

**`strategy_helper.py` (18 LOC) - NO TESTS**
- Simple module but should have tests for TypedDict validation

### 1.2 Test Infrastructure Assessment

**Current Fixtures (`tests/conftest.py`):**
```python
@pytest.fixture
def temp_workdir(): TemporaryDirectory

@pytest.fixture
def temp_empty_file(temp_workdir): Empty file in temp directory
```

**Current Test Markers:**
- `@pytest.mark.fast` - Quick unit tests
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (AWS, external tools)
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.requires_tools` - Needs bioinformatics tools
- `@pytest.mark.requires_aws` - Needs AWS access

**Strengths:**
- Good marker system for test categorization
- Basic temporary directory fixtures
- Clear separation of fast/slow tests

**Weaknesses:**
- No fixtures for mock S3 operations
- No fixtures for mock subprocess calls
- No fixtures for common test data (FASTA/FASTQ)
- No fixtures for config dictionaries
- No fixtures for execution states

---

## Part 2: Gap Analysis

### 2.1 Critical Gaps by Priority

#### Priority 1: HIGH - Core State Management (Security & Correctness)

**Module**: `execution_state.py` (148 LOC)
**Risk**: Configuration errors could lead to incorrect analysis, wasted compute, data loss
**Missing Tests**:
1. Config parsing with invalid YAML
2. Config parsing with missing required fields
3. Config parsing with invalid time formats
4. Default value application
5. Limit checking edge cases (exactly at limit, just before/after)
6. State serialization roundtrip (from_config -> to_yaml_config -> from_config)
7. Concurrent state updates (if applicable)
8. Time limit checking with clock changes

#### Priority 2: HIGH - External Tool Integration (Reliability)

**Module**: `pipeline_steps.py` (685 LOC)
**Risk**: Silent failures in tool execution, incorrect parameters, resource exhaustion
**Missing Tests**:
1. Megahit command construction and parameter validation
2. BBDuk command construction and parameter validation
3. Subprocess failure handling
4. File existence checks before tool execution
5. Output validation after tool execution
6. Resource limit handling (memory, CPU)
7. Batch vs local execution mode switching
8. Nextflow integration points

#### Priority 3: MEDIUM - Frequency Filtering (Performance & Correctness)

**Module**: `kmer_freq_filter.py` (249 LOC)
**Risk**: Incorrect filtering could remove valid data or include bad data
**Missing Tests**:
1. KMC command construction
2. Parallel execution management
3. Temporary file cleanup
4. Disk space handling
5. Memory limit validation
6. K-mer merging logic
7. Empty result handling
8. /tmp directory warnings

#### Priority 4: MEDIUM - Decision Logic (Automation Correctness)

**Modules**: `decision_manager.py`, `strategy.py`, `actions.py`
**Risk**: Incorrect automation decisions waste compute resources
**Missing Tests**:
1. Strategy loading errors
2. Invalid strategy names
3. Action composition (multiple actions in sequence)
4. State mutation safety
5. Condition evaluation edge cases
6. Missing metrics handling

#### Priority 5: MEDIUM - Pipeline Orchestration (Integration Points)

**Module**: `pipeline.py` (362 LOC)
**Risk**: Logic errors in main loop could cause infinite loops, missed convergence
**Missing Tests**:
1. Iteration loop termination conditions
2. Progress detection logic
3. Excess read threshold handling
4. Warm start integration
5. Cleanup behavior
6. Output path handling
7. Metrics computation edge cases

#### Priority 6: LOW - I/O Helpers (Completeness)

**Module**: `io_helpers.py` (188 LOC)
**Risk**: Low (mostly tested, but some gaps)
**Missing Tests**:
1. `s3_files_with_prefix` with pagination
2. `get_s3_paths_by_priority` validation logic
3. Priority sequence validation

---

## Part 3: Detailed Testing Strategy

### 3.1 Test Categories and Approaches

#### Category 1: Pure Unit Tests (No External Dependencies)

**Modules**: `execution_state.py`, `actions.py`, `strategy.py`, `strategy_helper.py`

**Approach**:
- Mock file I/O operations
- Use in-memory data structures
- Parameterize tests for multiple input scenarios
- Test edge cases and boundary conditions

**Example Test Structure**:
```python
@pytest.mark.fast
@pytest.mark.unit
class TestExecutionState:
    def test_from_config_minimal(self):
        """Test parsing config with only required fields"""

    def test_from_config_with_defaults(self):
        """Test that defaults are applied correctly"""

    @pytest.mark.parametrize("invalid_time", ["5", "hours", "5 days 3 hours"])
    def test_from_config_invalid_time_format(self, invalid_time):
        """Test that invalid time formats raise errors"""

    def test_check_limits_at_iteration_boundary(self):
        """Test limit checking exactly at max iterations"""
```

#### Category 2: Integration Tests with Mocked External Tools

**Modules**: `pipeline_steps.py`, `kmer_freq_filter.py`

**Approach**:
- Mock subprocess calls with realistic return values
- Verify command construction without actually running tools
- Test error handling with mocked failures
- Use temporary files for I/O testing

**Example Test Structure**:
```python
@pytest.mark.fast
@pytest.mark.unit
def test_assemble_contigs_command_construction(mocker, temp_workdir):
    """Verify megahit commands are constructed correctly"""
    mock_run = mocker.patch("subprocess.run")

    _assemble_contigs(temp_workdir, iter=1, freq_filter=False)

    # Verify subprocess.run was called with correct arguments
    calls = mock_run.call_args_list
    assert len(calls) == 2  # Two assemblies
    assert "megahit" in calls[0][0][0]
```

#### Category 3: Integration Tests with Real External Tools

**Modules**: `pipeline_steps.py`, `kmer_freq_filter.py`

**Approach**:
- Use small test datasets
- Mark as slow tests
- Require tools to be installed
- Verify actual outputs match expectations

**Example Test Structure**:
```python
@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.requires_tools
def test_assemble_contigs_real(temp_workdir, tiny_fastq_fixture):
    """Test actual megahit assembly with tiny dataset"""
    # Setup real input files
    # Run actual assembly
    # Verify output exists and is valid
```

#### Category 4: Property-Based Tests

**Modules**: `dedup.py`, `basic_seq_operations.py`, `overlap_graph.py`

**Approach**:
- Use hypothesis library for generating test cases
- Test invariants that should always hold
- Find edge cases automatically

**Example Test Structure**:
```python
from hypothesis import given
from hypothesis.strategies import text, integers

@given(text(alphabet="ACGT", min_size=1, max_size=100))
def test_reverse_complement_involution(seq):
    """RC(RC(x)) should equal x"""
    assert _reverse_complement(_reverse_complement(seq)) == seq
```

### 3.2 Mocking Strategies

#### 3.2.1 Subprocess Mocking

**For modules calling external tools**: `pipeline_steps.py`, `kmer_freq_filter.py`

```python
@pytest.fixture
def mock_subprocess_success(mocker):
    """Mock successful subprocess execution"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="", stderr=""
    )
    return mock_run

@pytest.fixture
def mock_subprocess_failure(mocker):
    """Mock failed subprocess execution"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=[], output="Error message"
    )
    return mock_run
```

#### 3.2.2 File System Mocking

**For modules with heavy file I/O**: `io_helpers.py`, `pipeline.py`

```python
@pytest.fixture
def mock_s3_client(mocker):
    """Mock boto3 S3 client"""
    mock_client = mocker.patch("boto3.client")
    mock_s3 = mocker.Mock()
    mock_client.return_value = mock_s3

    # Configure mock responses
    mock_s3.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "test/file1.fastq.zst"},
            {"Key": "test/file2.fastq.zst"},
        ]
    }
    return mock_s3
```

#### 3.2.3 BioPython Mocking

**For sequence parsing**: Use real BioPython but with small test data

```python
@pytest.fixture
def tiny_fasta_file(tmp_path):
    """Create a tiny FASTA file for testing"""
    fasta_path = tmp_path / "test.fasta"
    fasta_path.write_text(">seq1\nACGTACGT\n>seq2\nTGCATGCA\n")
    return fasta_path
```

### 3.3 Test Data Management

#### 3.3.1 Fixtures for Common Test Data

```python
# tests/conftest.py additions

@pytest.fixture
def valid_config_dict():
    """Minimal valid configuration dictionary"""
    return {
        "assembly": {
            "input_seed_path": "/path/to/seed.fasta",
            "input_dataset_list": "/path/to/dataset.csv",
            "work_dir": "/path/to/work",
            "out_dir": "/path/to/output",
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

@pytest.fixture
def execution_state_fixture(valid_config_dict):
    """Create ExecutionState from valid config"""
    return ExecutionState.from_config(valid_config_dict)

@pytest.fixture
def sample_reads_fasta(tmp_path):
    """Create sample FASTQ files for testing"""
    r1 = tmp_path / "reads_1.fastq"
    r2 = tmp_path / "reads_2.fastq"

    r1.write_text("@read1\nACGTACGT\n+\nIIIIIIII\n")
    r2.write_text("@read1\nTGCATGCA\n+\nIIIIIIII\n")

    return r1, r2

@pytest.fixture
def s3_record_list():
    """Sample S3 record list"""
    return [
        S3Record("s3://bucket/path/file1.fastq.zst", "bucket-path-file1"),
        S3Record("s3://bucket/path/file2.fastq.zst", "bucket-path-file2"),
    ]
```

#### 3.3.2 Test Data Organization

```
tests/
├── data/
│   ├── configs/
│   │   ├── minimal_config.yaml
│   │   ├── full_config.yaml
│   │   └── invalid_configs/
│   │       ├── missing_required.yaml
│   │       ├── invalid_time.yaml
│   │       └── negative_values.yaml
│   ├── sequences/
│   │   ├── tiny_seed.fasta (10bp)
│   │   ├── small_seed.fasta (100bp)
│   │   ├── tiny_reads_1.fastq (10 reads)
│   │   └── tiny_reads_2.fastq (10 reads)
│   └── expected_outputs/
│       ├── commands/
│       │   ├── megahit_standard.txt
│       │   └── bbduk_standard.txt
│       └── metrics/
│           └── sample_metrics.json
```

---

## Part 4: Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal**: Establish test infrastructure and cover critical gaps

**Tasks**:
1. **Enhance test fixtures** (2 days)
   - Add config fixtures (valid, invalid variants)
   - Add sequence data fixtures (FASTA, FASTQ)
   - Add S3 mocking fixtures
   - Add subprocess mocking fixtures

2. **Test `execution_state.py`** (3 days)
   - Config parsing tests (valid, invalid, edge cases)
   - State management tests (updates, limits, serialization)
   - YAML roundtrip tests
   - Target: 90%+ coverage

3. **Test `actions.py` comprehensively** (1 day)
   - Edge cases (negative values, zero, large values)
   - State immutability tests
   - Action composition tests
   - Target: 100% coverage

4. **Test `decision_manager.py` comprehensively** (2 days)
   - Strategy loading (valid, invalid, missing)
   - Automate flag scenarios
   - Error handling
   - Target: 95%+ coverage

**Deliverables**:
- Enhanced `conftest.py` with 10+ new fixtures
- `tests/unit_tests/test_execution_state.py` (~150 LOC)
- Enhanced `tests/unit_tests/test_actions.py` (~80 LOC)
- Enhanced `tests/unit_tests/test_decision_manager.py` (~120 LOC)

### Phase 2: External Tool Integration (Week 3-4)

**Goal**: Test all external tool invocations with mocks

**Tasks**:
1. **Test `pipeline_steps.py` - Part 1: Command Construction** (4 days)
   - `_assemble_contigs` command construction
   - `_prepare_query_seqs` logic
   - `_copy_iteration_reads` file operations
   - `_fasta_longest_total` parsing
   - Mock all subprocess calls
   - Target: 40% coverage of module

2. **Test `kmer_freq_filter.py` - Unit tests** (3 days)
   - `_make_kmer_count_commands` construction
   - `_high_freq_kmers_split_files` orchestration
   - `frequency_filter_reads` workflow
   - Directory validation
   - Mock all subprocess calls
   - Target: 60% coverage

**Deliverables**:
- `tests/unit_tests/test_pipeline_steps_commands.py` (~200 LOC)
- `tests/unit_tests/test_kmer_freq_filter.py` (~180 LOC)

### Phase 3: Pipeline Orchestration (Week 5)

**Goal**: Test main pipeline logic and iteration management

**Tasks**:
1. **Test `pipeline.py` - Unit tests** (3 days)
   - `_compute_iteration_metrics` with various states
   - `_compute_assembly_metrics` edge cases
   - `outward_assembly` parameter validation
   - Error handling and cleanup
   - Mock `_outward_main_loop`
   - Target: 50% coverage

2. **Test `pipeline_steps.py` - Part 2: Integration Points** (2 days)
   - `_subset_contigs` extended scenarios
   - `_choose_best_subiter` logic
   - Batch vs local mode switching
   - Target: 60% coverage of module

**Deliverables**:
- `tests/unit_tests/test_pipeline.py` (~200 LOC)
- Enhanced `tests/unit_tests/test_pipeline_steps_commands.py` (+100 LOC)

### Phase 4: Strategy and Helpers (Week 6)

**Goal**: Complete coverage of smaller modules

**Tasks**:
1. **Test `strategy.py` and `strategy_helper.py`** (2 days)
   - `example_strategy` all branches
   - TypedDict validation
   - Custom strategy scenarios
   - Target: 100% coverage

2. **Complete `io_helpers.py` testing** (2 days)
   - `s3_files_with_prefix` with mocked boto3
   - `get_s3_paths_by_priority` validation
   - `dir_to_s3_paths` logic
   - `load_config` error handling
   - Target: 95% coverage

3. **Add parameterized tests** (1 day)
   - Expand existing tests with more parameter combinations
   - Add hypothesis-based property tests where applicable

**Deliverables**:
- `tests/unit_tests/test_strategy.py` (~80 LOC)
- Enhanced `tests/test_io_helpers.py` (+80 LOC)
- Parameterized test expansions across modules

### Phase 5: Integration and Refinement (Week 7)

**Goal**: Integration tests with small real data, refinement

**Tasks**:
1. **Create integration tests with real tools** (3 days)
   - Small-scale megahit assembly test
   - Small-scale bbduk filtering test
   - KMC counting with tiny dataset
   - Mark as `@pytest.mark.slow`

2. **Code coverage analysis** (1 day)
   - Run pytest with coverage plugin
   - Identify remaining gaps
   - Prioritize critical uncovered lines

3. **Refactor and document tests** (1 day)
   - Add docstrings to complex tests
   - Organize test files
   - Update README with testing instructions

**Deliverables**:
- `tests/integration/test_tools_integration.py` (~150 LOC)
- Coverage report with >80% overall coverage
- Updated documentation

### Phase 6: Documentation and CI/CD (Week 8)

**Goal**: Testing documentation and automation

**Tasks**:
1. **Testing documentation** (2 days)
   - Update CLAUDE.md with testing guidelines
   - Create TESTING.md with instructions
   - Document fixture usage
   - Document mock strategies

2. **CI/CD integration** (2 days)
   - Ensure all tests run in CI
   - Set up fast/slow test separation
   - Configure coverage reporting
   - Add test badges to README

3. **Final review and polish** (1 day)
   - Review all test code
   - Ensure consistency
   - Fix any flaky tests

**Deliverables**:
- TESTING.md documentation
- Updated CI/CD configuration
- Test coverage badge
- Final test suite review

---

## Part 5: Testing Best Practices and Standards

### 5.1 Naming Conventions

**Test Files**:
- Unit tests: `tests/unit_tests/test_<module_name>.py`
- Integration tests: `tests/integration/test_<feature_name>.py`
- Match source module structure

**Test Functions**:
```python
def test_<function_name>_<scenario>():
    """Test that <function> behaves correctly when <scenario>"""
```

**Examples**:
```python
def test_from_config_missing_required_field():
    """Test that from_config raises ValueError when required field is missing"""

def test_assemble_contigs_with_frequency_filtering():
    """Test that _assemble_contigs creates filtered assembly when freq_filter=True"""
```

### 5.2 Test Structure (AAA Pattern)

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

### 5.3 Test Documentation Standards

**Docstrings**:
- Every test function should have a docstring
- Explain WHAT is being tested and WHY
- Explain special setups or edge cases

```python
def test_check_limits_at_exact_iteration_boundary(execution_state_fixture):
    """Test limit checking when current_outer_iterations equals max_outer_iterations.

    This is a boundary condition that should trigger the limit check to return True,
    preventing further iterations. Tests for off-by-one errors.
    """
```

**Comments**:
- Use comments to explain complex test setup
- Explain magic numbers
- Highlight non-obvious assertions

### 5.4 Assertion Best Practices

**Prefer specific assertions**:
```python
# Good
assert result.contig_count == 5
assert output_path.exists()
assert "error" in log_message.lower()

# Less good (too generic)
assert result is not None
assert True
```

**Multiple assertions in sequence**:
```python
# Acceptable for related checks
result = compute_metrics(...)
assert result.total_time > 0
assert result.final_contig_count >= 0
assert result.work_dir == str(workdir)
assert len(result.inner_iterations) == expected_iters
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

### 5.5 Parameterization Guidelines

**Use parametrize for variants of same test**:
```python
@pytest.mark.parametrize("k_value,expected_result", [
    (15, "small_kmer_output"),
    (21, "medium_kmer_output"),
    (31, "large_kmer_output"),
])
def test_kmer_filtering_by_size(k_value, expected_result):
    result = filter_by_kmer(k=k_value)
    assert result == expected_result
```

**Use parametrize for edge cases**:
```python
@pytest.mark.parametrize("invalid_time", [
    "5",           # missing unit
    "hours",       # missing number
    "5 days",      # wrong unit
    "-5 hours",    # negative
    "0 hours",     # zero
])
def test_from_config_invalid_time_format(invalid_time):
    config = valid_config_dict()
    config["decision"]["limits"]["compute_time"] = invalid_time

    with pytest.raises(ValueError):
        ExecutionState.from_config(config)
```

### 5.6 Mock Guidelines

**Mock at the boundary**:
- Mock external calls (subprocess, boto3, file I/O)
- Don't mock internal project code in unit tests
- Mock internal code only in integration tests when isolating components

**Verify mock calls**:
```python
def test_subprocess_called_correctly(mocker):
    mock_run = mocker.patch("subprocess.run")

    execute_external_tool(args=["tool", "--param", "value"])

    # Verify it was called
    mock_run.assert_called_once()

    # Verify the arguments
    call_args = mock_run.call_args[0][0]
    assert call_args == ["tool", "--param", "value"]
```

**Reset mocks between tests**:
- Use pytest-mock's `mocker` fixture (auto-resets)
- Or manually reset in teardown

### 5.7 Test Data Management

**Prefer generated data over checked-in files**:
```python
# Good: Generate in fixture
@pytest.fixture
def sample_fasta(tmp_path):
    fasta = tmp_path / "test.fasta"
    fasta.write_text(">seq1\nACGT\n>seq2\nTGCA\n")
    return fasta

# OK for complex/realistic data: Check in small test files
tests/data/real_megahit_output.fasta
```

**Keep test data small**:
- Use minimal data that exercises the code path
- For large data scenarios, use mocks or marks as slow

**Clean up test artifacts**:
- Use `tmp_path` or `tempfile` for temporary files
- Pytest automatically cleans up `tmp_path`

### 5.8 Coverage Targets

**Overall Target**: 80% line coverage minimum

**Module-Specific Targets**:
- Critical modules (execution_state, pipeline, decision_manager): >90%
- Algorithm modules (dedup, overlap_graph, basic_seq_operations): >85%
- Tool integration (pipeline_steps, kmer_freq_filter): >70% (harder to test)
- Simple modules (actions, strategy_helper): 100%

**What NOT to test**:
- Third-party library code
- Trivial getters/setters (unless they have logic)
- Auto-generated code

**Focus on**:
- Edge cases and boundary conditions
- Error handling paths
- Complex logic and algorithms
- Integration points

---

## Part 6: Specific Test Case Examples

### 6.1 ExecutionState Module

```python
# tests/unit_tests/test_execution_state.py

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from outward_assembly.execution_state import ExecutionState

class TestExecutionStateFromConfig:
    """Tests for ExecutionState.from_config class method"""

    @pytest.fixture
    def minimal_valid_config(self):
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

    def test_from_config_minimal_valid(self, minimal_valid_config):
        """Test that minimal valid config creates ExecutionState successfully"""
        state = ExecutionState.from_config(minimal_valid_config)

        assert state.input_seed_path == "/path/to/seed.fasta"
        assert state.max_outer_iterations == 20
        assert state.max_compute_time == timedelta(hours=5)
        assert state.automate is False
        assert state.current_outer_iterations == 0

    def test_from_config_applies_defaults(self, minimal_valid_config):
        """Test that defaults are applied for optional fields"""
        # Remove optional fields
        del minimal_valid_config["assembly"]["read_subset_k"]
        del minimal_valid_config["assembly"]["dataset_priority"]

        state = ExecutionState.from_config(minimal_valid_config)

        assert state.read_subset_k == 27  # DEFAULT_READ_SUBSET_K
        assert state.dataset_priority == 1  # DEFAULT_DATASET_PRIORITY
        assert state.use_batch is False  # DEFAULT_USE_BATCH

    @pytest.mark.parametrize("invalid_time,error_pattern", [
        ("5", "cannot parse time"),
        ("hours", "cannot parse time"),
        ("5 minutes", "must be in hours"),
        ("-5 hours", "time cannot be negative"),
        ("0 hours", "time must be positive"),
    ])
    def test_from_config_invalid_time_format(self, minimal_valid_config, invalid_time, error_pattern):
        """Test that invalid time formats raise appropriate errors"""
        minimal_valid_config["decision"]["limits"]["compute_time"] = invalid_time

        with pytest.raises(ValueError, match=error_pattern):
            ExecutionState.from_config(minimal_valid_config)

    def test_from_config_automate_without_strategy(self, minimal_valid_config):
        """Test that automate=True without strategy raises error"""
        minimal_valid_config["decision"]["automate"] = True
        minimal_valid_config["decision"]["strategy"] = None

        with pytest.raises(ValueError, match="Strategy must be specified"):
            ExecutionState.from_config(minimal_valid_config)

    def test_from_config_missing_required_assembly_field(self, minimal_valid_config):
        """Test that missing required assembly field raises error"""
        del minimal_valid_config["assembly"]["input_seed_path"]

        with pytest.raises(KeyError):
            ExecutionState.from_config(minimal_valid_config)


class TestExecutionStateLimitChecking:
    """Tests for ExecutionState.check_limits method"""

    def test_check_limits_under_limits(self, execution_state_fixture):
        """Test that check_limits returns False when under all limits"""
        state = execution_state_fixture
        state.current_outer_iterations = 5
        state.max_outer_iterations = 20

        assert state.check_limits() is False

    def test_check_limits_at_iteration_limit(self, execution_state_fixture):
        """Test that check_limits returns True when at iteration limit"""
        state = execution_state_fixture
        state.current_outer_iterations = 20
        state.max_outer_iterations = 20

        assert state.check_limits() is True

    def test_check_limits_one_before_iteration_limit(self, execution_state_fixture):
        """Test that check_limits returns False one iteration before limit"""
        state = execution_state_fixture
        state.current_outer_iterations = 19
        state.max_outer_iterations = 20

        assert state.check_limits() is False

    def test_check_limits_at_time_limit(self, execution_state_fixture, monkeypatch):
        """Test that check_limits returns True when time limit exceeded"""
        state = execution_state_fixture
        state.max_compute_time = timedelta(seconds=10)
        state.start_time = datetime.now() - timedelta(seconds=11)

        assert state.check_limits() is True

    def test_check_limits_just_under_time_limit(self, execution_state_fixture):
        """Test that check_limits returns False just under time limit"""
        state = execution_state_fixture
        state.max_compute_time = timedelta(seconds=10)
        state.start_time = datetime.now() - timedelta(seconds=9)

        assert state.check_limits() is False


class TestExecutionStateYAMLSerialization:
    """Tests for ExecutionState YAML serialization methods"""

    def test_to_yaml_config_structure(self, execution_state_fixture):
        """Test that to_yaml_config produces correct structure"""
        state = execution_state_fixture
        yaml_dict = state.to_yaml_config()

        # Check top-level structure
        assert "assembly" in yaml_dict
        assert "decision" in yaml_dict

        # Check assembly fields
        assert yaml_dict["assembly"]["input_seed_path"] == state.input_seed_path
        assert yaml_dict["assembly"]["read_subset_k"] == state.read_subset_k

        # Check decision fields
        assert yaml_dict["decision"]["automate"] == state.automate
        assert yaml_dict["decision"]["strategy"] == state.strategy

    def test_yaml_roundtrip(self, minimal_valid_config):
        """Test that config -> state -> yaml -> state produces equivalent state"""
        state1 = ExecutionState.from_config(minimal_valid_config)
        yaml_dict = state1.to_yaml_config()
        state2 = ExecutionState.from_config(yaml_dict)

        # Compare key fields (start_time and current_outer_iterations will differ)
        assert state1.input_seed_path == state2.input_seed_path
        assert state1.read_subset_k == state2.read_subset_k
        assert state1.max_outer_iterations == state2.max_outer_iterations
        assert state1.automate == state2.automate

    def test_write_config_creates_file(self, execution_state_fixture, tmp_path):
        """Test that write_config creates a valid YAML file"""
        state = execution_state_fixture
        yaml_path = tmp_path / "test_config.yaml"

        state.write_config(str(yaml_path))

        assert yaml_path.exists()

        # Verify file is valid YAML
        import yaml
        with open(yaml_path) as f:
            loaded = yaml.safe_load(f)

        assert loaded["assembly"]["input_seed_path"] == state.input_seed_path
```

### 6.2 Pipeline Steps Module

```python
# tests/unit_tests/test_pipeline_steps_commands.py

import pytest
from pathlib import Path
from outward_assembly.pipeline_steps import _assemble_contigs, _prepare_query_seqs

class TestAssembleContigs:
    """Tests for _assemble_contigs function"""

    def test_assemble_contigs_without_freq_filter(self, mocker, temp_workdir, sample_reads_fastq):
        """Test that _assemble_contigs generates correct megahit commands without filtering"""
        mock_run = mocker.patch("subprocess.run")

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
        assert "-o" in first_call
        assert "megahit_out_iter1-1" in first_call[-1]

    def test_assemble_contigs_with_freq_filter(self, mocker, temp_workdir):
        """Test that _assemble_contigs generates three assemblies with freq filtering"""
        mock_run = mocker.patch("subprocess.run")

        # Create required input files
        (temp_workdir / "reads_1.fastq").touch()
        (temp_workdir / "reads_2.fastq").touch()
        (temp_workdir / "reads_ff_1.fastq").touch()
        (temp_workdir / "reads_ff_2.fastq").touch()
        (temp_workdir / "log.txt").touch()

        _assemble_contigs(temp_workdir, iter=1, freq_filter=True)

        # Should call subprocess.run three times (filtered + standard + permissive)
        assert mock_run.call_count == 3

        # Check that first call uses filtered reads
        first_call = mock_run.call_args_list[0][0][0]
        assert "reads_ff_1.fastq" in " ".join(first_call)
        assert "reads_ff_2.fastq" in " ".join(first_call)

    def test_assemble_contigs_creates_subdirectories(self, mocker, temp_workdir):
        """Test that _assemble_contigs creates properly named output directories"""
        mock_run = mocker.patch("subprocess.run")

        # Setup
        (temp_workdir / "reads_1.fastq").touch()
        (temp_workdir / "reads_2.fastq").touch()
        (temp_workdir / "log.txt").touch()

        _assemble_contigs(temp_workdir, iter=3, freq_filter=False)

        # Check output directory names in commands
        calls = mock_run.call_args_list
        assert "megahit_out_iter3-1" in " ".join(calls[0][0][0])
        assert "megahit_out_iter3-2" in " ".join(calls[1][0][0])

    def test_assemble_contigs_subprocess_failure(self, mocker, temp_workdir):
        """Test that _assemble_contigs propagates subprocess failures"""
        import subprocess

        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.CalledProcessError(1, "megahit")

        # Setup
        (temp_workdir / "reads_1.fastq").touch()
        (temp_workdir / "reads_2.fastq").touch()
        (temp_workdir / "log.txt").touch()

        with pytest.raises(subprocess.CalledProcessError):
            _assemble_contigs(temp_workdir, iter=1, freq_filter=False)

    def test_assemble_contigs_k_list_parameter(self, mocker, temp_workdir):
        """Test that megahit k-list parameter is correctly set"""
        mock_run = mocker.patch("subprocess.run")

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

### 6.3 K-mer Frequency Filter Module

```python
# tests/unit_tests/test_kmer_freq_filter.py

import pytest
from pathlib import Path
from outward_assembly.kmer_freq_filter import (
    _make_kmer_count_commands,
    _high_freq_kmers_split_files,
)
from outward_assembly.io_helpers import S3Record

class TestMakeKmerCountCommands:
    """Tests for _make_kmer_count_commands function"""

    def test_command_construction_basic(self, tmp_path):
        """Test basic command construction for single file"""
        s3_records = [S3Record("s3://bucket/file.fastq.zst", "bucket-file")]

        commands = _make_kmer_count_commands(
            s3_records, tmp_path, k=31, min_kmer_freq=2000
        )

        assert len(commands) == 1
        cmd = commands[0]

        # Verify command structure
        assert "mkdir -p" in cmd
        assert "aws s3 cp s3://bucket/file.fastq.zst" in cmd
        assert "zstd -d" in cmd
        assert "kmc -k31" in cmd
        assert "-ci2000" in cmd
        assert "-cs4096" in cmd  # Next power of 2 above 2*2000
        assert "kmc_tools transform" in cmd
        assert "rm -rf" in cmd

    def test_command_construction_multiple_files(self, tmp_path):
        """Test that separate commands are generated for multiple files"""
        s3_records = [
            S3Record("s3://bucket/file1.fastq.zst", "bucket-file1"),
            S3Record("s3://bucket/file2.fastq.zst", "bucket-file2"),
        ]

        commands = _make_kmer_count_commands(
            s3_records, tmp_path, k=21, min_kmer_freq=1000
        )

        assert len(commands) == 2
        assert "file1.fastq.zst" in commands[0]
        assert "file2.fastq.zst" in commands[1]

    @pytest.mark.parametrize("min_freq,expected_max_count", [
        (100, 256),    # 2^8
        (1000, 2048),  # 2^11
        (2000, 4096),  # 2^12
        (5000, 16384), # 2^14
    ])
    def test_max_count_calculation(self, tmp_path, min_freq, expected_max_count):
        """Test that max_count is correctly calculated as next power of 2"""
        s3_records = [S3Record("s3://bucket/file.fastq.zst", "bucket-file")]

        commands = _make_kmer_count_commands(
            s3_records, tmp_path, k=31, min_kmer_freq=min_freq
        )

        assert f"-cs{expected_max_count}" in commands[0]

    def test_thread_and_memory_parameters(self, tmp_path):
        """Test that thread and memory parameters are correctly set"""
        s3_records = [S3Record("s3://bucket/file.fastq.zst", "bucket-file")]

        commands = _make_kmer_count_commands(
            s3_records, tmp_path, k=31, min_kmer_freq=1000,
            threads=8, memory_GB=10
        )

        cmd = commands[0]
        assert "-t8" in cmd
        assert "-m10" in cmd


class TestHighFreqKmersSplitFiles:
    """Tests for _high_freq_kmers_split_files function"""

    def test_tmp_directory_rejection(self, tmp_path):
        """Test that /tmp directories are rejected by default"""
        s3_records = [S3Record("s3://bucket/file.fastq.zst", "bucket-file")]
        tmp_workdir = Path("/tmp/test")
        tmp_workdir.mkdir(exist_ok=True)

        with pytest.raises(ValueError, match="/tmp"):
            _high_freq_kmers_split_files(
                s3_records, tmp_workdir, allow_tmp_workdir=False
            )

    def test_tmp_directory_warning(self, tmp_path):
        """Test that /tmp directories raise warning when allowed"""
        s3_records = [S3Record("s3://bucket/file.fastq.zst", "bucket-file")]
        tmp_workdir = Path("/tmp/test")
        tmp_workdir.mkdir(exist_ok=True)

        with pytest.warns(UserWarning, match="memory-backed"):
            _high_freq_kmers_split_files(
                s3_records, tmp_workdir, allow_tmp_workdir=True
            )

    def test_nonexistent_workdir_rejection(self):
        """Test that nonexistent workdir raises error"""
        s3_records = [S3Record("s3://bucket/file.fastq.zst", "bucket-file")]

        with pytest.raises(ValueError, match="does not exist"):
            _high_freq_kmers_split_files(
                s3_records, Path("/nonexistent/path")
            )

    def test_creates_kmers_subdirectory(self, mocker, tmp_path):
        """Test that function creates kmers/ subdirectory"""
        # Mock subprocess to prevent actual execution
        mocker.patch("subprocess.run")

        s3_records = [S3Record("s3://bucket/file.fastq.zst", "bucket-file")]

        _high_freq_kmers_split_files(s3_records, tmp_path)

        assert (tmp_path / "kmers").exists()
        assert (tmp_path / "kmers").is_dir()

    def test_parallel_execution_default(self, mocker, tmp_path):
        """Test that default parallelism is cpu_count // 4"""
        mock_run = mocker.patch("subprocess.run")
        mocker.patch("outward_assembly.kmer_freq_filter.cpu_count", return_value=16)

        s3_records = [S3Record("s3://bucket/file.fastq.zst", "bucket-file")]

        _high_freq_kmers_split_files(s3_records, tmp_path)

        # Check xargs -P parameter
        call_cmd = mock_run.call_args[0][0]
        assert "-P 4" in call_cmd  # 16 // 4 = 4
```

---

## Part 7: Recommended Test Utilities and Helpers

### 7.1 Custom Assertions

```python
# tests/test_utils.py

def assert_fasta_valid(fasta_path):
    """Assert that a FASTA file is valid and parseable"""
    from Bio import SeqIO
    try:
        records = list(SeqIO.parse(fasta_path, "fasta"))
        assert len(records) > 0, "FASTA file is empty"
        for record in records:
            assert len(record.seq) > 0, f"Record {record.id} has empty sequence"
    except Exception as e:
        pytest.fail(f"Invalid FASTA file: {e}")

def assert_fastq_valid(fastq_path):
    """Assert that a FASTQ file is valid"""
    with open(fastq_path) as f:
        lines = f.readlines()

    assert len(lines) % 4 == 0, "FASTQ must have lines divisible by 4"

    for i in range(0, len(lines), 4):
        assert lines[i].startswith("@"), f"Line {i} should start with @"
        assert lines[i+2].startswith("+"), f"Line {i+2} should start with +"

def assert_commands_equivalent(cmd1, cmd2, ignore_order=False):
    """Assert that two shell commands are equivalent"""
    # Split on pipes and whitespace
    # Compare command components
    pass  # Implementation details

def assert_subprocess_called_with_tool(mock_run, tool_name):
    """Assert that subprocess.run was called with specific tool"""
    for call in mock_run.call_args_list:
        cmd = call[0][0]
        if isinstance(cmd, list) and tool_name in cmd:
            return True
    pytest.fail(f"subprocess.run was not called with {tool_name}")
```

### 7.2 Test Data Generators

```python
# tests/test_data_generators.py

import random
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

def generate_random_dna(length, seed=None):
    """Generate random DNA sequence"""
    if seed is not None:
        random.seed(seed)
    return "".join(random.choices("ACGT", k=length))

def generate_fastq_record(read_id, seq_length=100, quality="I", seed=None):
    """Generate a single FASTQ record as string"""
    seq = generate_random_dna(seq_length, seed)
    qual = quality * seq_length
    return f"@{read_id}\n{seq}\n+\n{qual}\n"

def generate_fasta_file(path, num_sequences=10, seq_length=100, seed=None):
    """Generate a FASTA file with random sequences"""
    from Bio import SeqIO

    records = []
    for i in range(num_sequences):
        seq = Seq(generate_random_dna(seq_length, seed=seed + i if seed else None))
        record = SeqRecord(seq, id=f"seq{i}", description="")
        records.append(record)

    SeqIO.write(records, path, "fasta")
    return path

def generate_config_dict(overrides=None):
    """Generate a valid config dict with optional overrides"""
    config = {
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

    if overrides:
        deep_merge(config, overrides)

    return config
```

### 7.3 Mock Builders

```python
# tests/mock_builders.py

class MockSubprocessBuilder:
    """Builder for creating mock subprocess responses"""

    def __init__(self):
        self.returncode = 0
        self.stdout = ""
        self.stderr = ""

    def with_success(self):
        self.returncode = 0
        return self

    def with_failure(self, returncode=1):
        self.returncode = returncode
        return self

    def with_stdout(self, output):
        self.stdout = output
        return self

    def with_stderr(self, output):
        self.stderr = output
        return self

    def build(self):
        import subprocess
        return subprocess.CompletedProcess(
            args=[],
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr
        )

# Usage:
# mock_run.return_value = MockSubprocessBuilder().with_success().with_stdout("output").build()
```

---

## Part 8: Coverage Targets and Metrics

### 8.1 Coverage Targets by Module

| Module | Current Estimate | Target | Priority | Rationale |
|--------|-----------------|--------|----------|-----------|
| `execution_state.py` | 0% | 95% | HIGH | Critical for config management |
| `pipeline.py` | 10% | 85% | HIGH | Main orchestration logic |
| `pipeline_steps.py` | 5% | 75% | HIGH | External tool integration |
| `decision_manager.py` | 30% | 95% | HIGH | Automation correctness |
| `kmer_freq_filter.py` | 5% | 70% | MEDIUM | Complex but has integration test |
| `actions.py` | 60% | 100% | MEDIUM | Simple, should be complete |
| `strategy.py` | 0% | 100% | MEDIUM | User-facing, should be solid |
| `dedup.py` | 95% | 95% | LOW | Already excellent |
| `basic_seq_operations.py` | 85% | 90% | LOW | Already good |
| `io_helpers.py` | 70% | 90% | MEDIUM | Some gaps remain |
| `overlap_graph.py` | 60% | 85% | MEDIUM | Algorithm correctness |
| `strategy_helper.py` | 0% | 100% | LOW | Trivial module |
| **Overall** | **~56%** | **>80%** | - | - |

### 8.2 Coverage Measurement

**Setup pytest-cov**:
```bash
uv add --dev pytest-cov
```

**Run with coverage**:
```bash
# All tests with coverage
uv run pytest tests/ --cov=outward_assembly --cov-report=html --cov-report=term

# Fast tests only
uv run pytest tests/ -m fast --cov=outward_assembly --cov-report=term

# Specific module
uv run pytest tests/unit_tests/test_execution_state.py --cov=outward_assembly.execution_state --cov-report=term-missing
```

**Coverage thresholds in pytest.ini**:
```ini
[pytest]
addopts = --cov-fail-under=80
```

### 8.3 Coverage Analysis Tools

**Generate HTML report**:
```bash
uv run pytest --cov=outward_assembly --cov-report=html
open htmlcov/index.html
```

**Identify uncovered lines**:
```bash
uv run pytest --cov=outward_assembly --cov-report=term-missing
```

**Coverage badge** (for README):
```markdown
![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen)
```

---

## Part 9: Continuous Integration Considerations

### 9.1 Test Categorization for CI

**Fast Tests** (< 1 second each):
- All pure unit tests
- Mocked integration tests
- Run on every commit

**Slow Tests** (1-30 seconds each):
- Tests with real bioinformatics tools
- Small integration tests
- Run on PR, nightly

**Very Slow Tests** (> 30 seconds):
- End-to-end tests
- AWS integration tests
- Run on PR, release

### 9.2 CI Configuration Example

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  fast-tests:
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
      - name: Run fast tests
        run: uv run pytest -m fast --cov=outward_assembly --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v3
      # ... setup steps
      - name: Install bioinformatics tools
        run: |
          # Install megahit, bbduk, etc.
      - name: Run integration tests
        run: uv run pytest -m "integration and not requires_aws"

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request' || github.ref == 'refs/heads/main'
    steps:
      # ... similar setup
      - name: Run E2E tests
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: uv run pytest -m e2e
```

### 9.3 Test Parallelization

**pytest-xdist for parallel execution**:
```bash
uv add --dev pytest-xdist

# Run tests in parallel
uv run pytest -n auto tests/
```

**Considerations**:
- Fast unit tests benefit most from parallelization
- Integration tests may have resource contention
- Use `@pytest.mark.serial` for tests that can't run in parallel

---

## Part 10: Success Metrics

### 10.1 Quantitative Metrics

**Coverage Metrics**:
- [ ] Overall line coverage > 80%
- [ ] Critical modules (execution_state, pipeline, decision_manager) > 90%
- [ ] All modules > 60%
- [ ] No module with 0% coverage

**Test Quantity Metrics**:
- [ ] >100 unit tests
- [ ] >20 integration tests
- [ ] >5 end-to-end tests
- [ ] Test code > 2,500 lines (currently ~1,376)

**Test Quality Metrics**:
- [ ] All tests have docstrings
- [ ] >50% of tests are parameterized
- [ ] >80% of public functions have tests
- [ ] 100% of error handling paths tested

**Performance Metrics**:
- [ ] Fast test suite completes in < 30 seconds
- [ ] Full test suite (excluding e2e) completes in < 5 minutes
- [ ] No flaky tests (0% failure rate on re-runs)

### 10.2 Qualitative Metrics

**Code Quality**:
- [ ] All tests follow AAA pattern
- [ ] Consistent naming conventions
- [ ] Appropriate use of fixtures
- [ ] Clear test isolation

**Documentation**:
- [ ] Testing guidelines in CLAUDE.md
- [ ] TESTING.md created with instructions
- [ ] All complex tests have explanatory comments
- [ ] Examples provided for common test patterns

**Maintainability**:
- [ ] Test code is DRY (fixtures eliminate duplication)
- [ ] Tests are readable by new contributors
- [ ] Mock strategies are well-documented
- [ ] Test data management is clear

### 10.3 Regression Prevention

**Test Suite Should Catch**:
- [ ] Config parsing errors
- [ ] State management bugs
- [ ] Tool invocation errors
- [ ] File I/O failures
- [ ] Edge cases in algorithms
- [ ] Resource limit violations

**Verification**:
- Introduce intentional bugs
- Verify test suite catches them
- Document in test comments

---

## Appendices

### Appendix A: Testing Tools and Libraries

**Required**:
- `pytest` - Test framework
- `pytest-mock` - Mocking support
- `pytest-cov` - Coverage measurement

**Recommended**:
- `pytest-xdist` - Parallel test execution
- `pytest-timeout` - Prevent hanging tests
- `hypothesis` - Property-based testing
- `faker` - Generate test data

**Optional**:
- `pytest-benchmark` - Performance regression testing
- `pytest-randomly` - Randomize test order
- `pytest-repeat` - Repeat tests to find flakiness

### Appendix B: Test Markers Reference

```python
# pytest.ini or pyproject.toml

[tool.pytest.ini_options]
markers = [
    "fast: Quick unit tests (< 1s)",
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow tests (> 1s)",
    "e2e: End-to-end tests",
    "requires_tools: Requires bioinformatics tools",
    "requires_aws: Requires AWS credentials",
    "serial: Tests that must run serially",
]
```

**Usage**:
```bash
# Run only fast tests
pytest -m fast

# Run all except slow tests
pytest -m "not slow"

# Run integration tests that don't require AWS
pytest -m "integration and not requires_aws"
```

### Appendix C: Example Test Template

```python
"""
Unit tests for outward_assembly.<module_name>

This module tests <brief description of what's being tested>.
"""

import pytest
from outward_assembly.<module> import function_under_test


class TestFunctionName:
    """Tests for function_name function

    This test class covers:
    - Normal operation scenarios
    - Edge cases and boundary conditions
    - Error handling
    """

    @pytest.fixture
    def sample_input(self):
        """Sample valid input for function_name"""
        return {"key": "value"}

    @pytest.mark.fast
    @pytest.mark.unit
    def test_function_name_normal_case(self, sample_input):
        """Test that function_name behaves correctly with valid input"""
        # Arrange
        expected_result = "expected"

        # Act
        result = function_under_test(sample_input)

        # Assert
        assert result == expected_result

    @pytest.mark.fast
    @pytest.mark.unit
    def test_function_name_empty_input(self):
        """Test that function_name handles empty input correctly"""
        # Arrange
        empty_input = {}

        # Act & Assert
        with pytest.raises(ValueError, match="cannot be empty"):
            function_under_test(empty_input)

    @pytest.mark.fast
    @pytest.mark.unit
    @pytest.mark.parametrize("invalid_input,expected_error", [
        (None, "cannot be None"),
        ({"bad_key": "value"}, "missing required key"),
        ({"key": ""}, "value cannot be empty"),
    ])
    def test_function_name_invalid_input(self, invalid_input, expected_error):
        """Test that function_name rejects various invalid inputs"""
        with pytest.raises(ValueError, match=expected_error):
            function_under_test(invalid_input)
```

### Appendix D: Common Testing Pitfalls to Avoid

**1. Testing Implementation Instead of Behavior**
```python
# Bad: Tests implementation details
def test_uses_specific_algorithm():
    assert algorithm_used == "quicksort"

# Good: Tests behavior
def test_sorts_correctly():
    result = sort_function([3, 1, 2])
    assert result == [1, 2, 3]
```

**2. Overly Coupled Tests**
```python
# Bad: Test depends on other test state
def test_step_1():
    global state
    state = do_step_1()

def test_step_2():
    result = do_step_2(state)  # Depends on test_step_1

# Good: Each test is independent
def test_step_1():
    state = do_step_1()
    assert state.is_valid()

def test_step_2():
    state = create_test_state()  # Independent setup
    result = do_step_2(state)
```

**3. Unclear Test Failures**
```python
# Bad: Generic assertion
def test_processing():
    result = process_data(input)
    assert result  # What does this even check?

# Good: Specific assertion with message
def test_processing():
    result = process_data(input)
    assert result.status == "success", f"Processing failed: {result.error}"
    assert len(result.records) == 10, "Expected 10 processed records"
```

**4. Not Testing Error Paths**
```python
# Bad: Only test happy path
def test_parse_config():
    config = parse_config("valid_config.yaml")
    assert config["key"] == "value"

# Good: Test both success and failure
def test_parse_config_valid():
    config = parse_config("valid_config.yaml")
    assert config["key"] == "value"

def test_parse_config_missing_file():
    with pytest.raises(FileNotFoundError):
        parse_config("nonexistent.yaml")
```

**5. Ignoring Test Performance**
```python
# Bad: Slow test without marker
def test_large_dataset():
    # Processes 1 million records
    result = process(huge_dataset)

# Good: Marked appropriately
@pytest.mark.slow
def test_large_dataset():
    # Processes 1 million records
    result = process(huge_dataset)
```

---

## Conclusion

This comprehensive testing plan provides a structured approach to achieving >80% test coverage for the outward-assembly pipeline. The phased implementation over 8 weeks balances:

1. **Critical gaps first** - State management and decision logic
2. **External integration** - Tool invocations with proper mocking
3. **Pipeline orchestration** - Main loop and iteration logic
4. **Completeness** - Filling remaining gaps
5. **Quality** - Integration tests and refinement

**Success Criteria**:
- >80% overall line coverage
- >90% coverage on critical modules
- 100+ unit tests, 20+ integration tests
- All public functions tested
- Comprehensive error handling coverage
- Clear, maintainable test code

**Key Deliverables**:
- 1,500+ lines of new test code
- Enhanced fixture library
- Mocking strategies for all external dependencies
- Testing documentation (TESTING.md)
- CI/CD integration for automated testing

This plan transforms the test suite from basic coverage to a comprehensive safety net that enables confident refactoring, rapid development, and reliable releases.

**Next Steps**:
1. Review and approve this plan with the team
2. Set up initial fixtures and test infrastructure (Phase 1, Week 1)
3. Begin implementation following the phased roadmap
4. Track progress with coverage metrics
5. Iterate and refine based on learnings
