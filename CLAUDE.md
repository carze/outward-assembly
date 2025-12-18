# CLAUDE.md - Multi-Agentic Development Workflow Guide

## Project Overview

**Repository**: [carze/outward-assembly](https://github.com/carze/outward-assembly)

**Purpose**: Pipeline for assembling outward from seed sequences in large metagenomic datasets. This tool performs iterative genomic context assembly around seed sequences from large read collections, avoiding expensive full metagenomic joint assemblies.

**Technology Stack**:
- Python (96.9%) - Core logic and tooling
- Nextflow (2.6%) - Workflow orchestration
- Docker (0.5%) - Containerization
- uv - Python dependency management
- Mamba/Conda - Tools environment management

---

## Repository Structure

```
outward-assembly/
├── .github/workflows/     # CI/CD automation
├── docs/                  # Documentation
│   ├── installation.md
│   ├── usage.md
│   └── algorithm_details.md
├── nextflow/              # Nextflow workflow definitions
├── outward_assembly/      # Core Python package
├── readme_images/         # Documentation assets
├── tests/                 # Test suite
├── automate_assembly.py   # Main automation script
├── pyproject.toml         # Python project configuration
├── uv.lock               # Locked Python dependencies
├── oa_tools_env.yml      # Conda environment specification
└── oa_tools_lock.yml     # Locked conda dependencies
```

---

## Multi-Agentic Development Philosophy

When working with Claude on this codebase, treat development as **coordinated specialization** where different "agents" (conversation contexts or sessions) handle distinct aspects:

### Agent Specialization Areas

1. **Architecture Agent** - System design, refactoring, dependency management
2. **Feature Agent** - New capabilities, algorithm improvements
3. **Testing Agent** - Test coverage, integration tests, CI/CD
4. **Documentation Agent** - README, API docs, usage examples
5. **Performance Agent** - Optimization, profiling, scalability
6. **DevOps Agent** - Containerization, deployment, environment management

---

## Key Upgrade Priorities

### 1. Dependency Management
**Current State**: Using uv (modern) and mamba (established)
- Python packages managed via `pyproject.toml` and `uv.lock`
- System tools via `oa_tools_env.yml` and `oa_tools_lock.yml`

**Upgrade Considerations**:
- Ensure compatibility with latest uv releases
- Review Python version constraints (check pyproject.toml)
- Audit bioinformatics tool versions in conda env
- Consider migrating to pixi for unified environment management

### 2. Python Code Modernization
**Target Modern Python Practices**:
- Type hints (use `typing` or `typing_extensions`)
- Dataclasses or Pydantic models for configuration
- Async/await for I/O-bound operations (if applicable)
- Match statements (Python 3.10+)
- Pathlib instead of os.path

### 3. Algorithm & Performance
**Core Assembly Logic**:
- Iterative contig growth from seed sequences
- K-mer matching for read pair identification
- Assembly filtering and convergence detection

**Optimization Opportunities**:
- Profile k-mer matching bottlenecks
- Consider Rust extensions for hot paths
- Evaluate parallel processing strategies
- Memory-mapped file handling for large datasets

### 4. Nextflow Pipeline
**Current**: Nextflow workflows for orchestration
**Upgrades**:
- DSL2 syntax (if not already using)
- Process directives optimization
- Container strategies (Docker/Singularity/Conda)
- Resource allocation tuning

### 5. Testing Infrastructure
**Expand Coverage**:
- Unit tests for core assembly logic
- Integration tests for full pipeline
- Parameterized tests for various seed/read scenarios
- Performance regression tests

### 6. Cloud-Agnostic Filesystem
**Current State**: Abstraction layer supporting S3, GCS, and local filesystems
- Unified interface via `FilesystemAbstraction` class
- Automatic s5cmd detection for high-performance streaming
- Smart fallback to smart_open library

**Key Features**:
- Transparent path handling: `s3://`, `gs://`, or local paths work interchangeably
- Performance optimization: Uses native s5cmd when available (2-3x faster than smart_open)
- Zero-config fallback: Works without s5cmd for basic operations
- Thread-safe operations for parallel processing

**Testing Strategy**:
- Unit tests verify abstraction behavior (always run)
- Integration tests validate cloud operations (manual trigger via `workflow_dispatch`)
- Benchmarks track performance regressions

---

## Working with Claude: Best Practices

### Starting a New Development Session

**Initial Context Setting**:
```markdown
I'm working on the outward-assembly bioinformatics pipeline 
(https://github.com/carze/outward-assembly). This session focuses on [SPECIFIC_AREA].

Current state: [BRIEF_STATUS]
Goal: [CLEAR_OBJECTIVE]

Please review CLAUDE.md for project context before we begin.
```

### Effective Task Decomposition

**Good**: "Let's modernize the configuration system. First, show me the current config handling, then propose a Pydantic-based design."

**Less Good**: "Upgrade everything to be more modern."

### Requesting Code Reviews

**Prompt Template**:
```markdown
Review this [FILE/MODULE] for:
1. Type safety issues
2. Performance bottlenecks
3. Error handling gaps
4. Documentation completeness
5. Test coverage needs

File: [PATH]
Context: [WHAT_IT_DOES]
```

### Iterative Refinement Pattern

1. **Analyze** - Understand current implementation
2. **Propose** - Design improvement approach
3. **Implement** - Generate code changes
4. **Test** - Create/update tests
5. **Document** - Update relevant docs
6. **Review** - Iterate on feedback

---

## Domain-Specific Context

### Bioinformatics Concepts

**K-mers**: Substrings of length k from DNA sequences
- Used for efficient similarity searches
- Trade-off between specificity (longer) and sensitivity (shorter)

**Metagenomic Assembly**: Reconstructing genomes from mixed community samples
- Challenges: repeat regions, strain variation, coverage depth
- Outward assembly: targeted approach vs. full joint assembly

**Seed Sequences**: Starting points for assembly
- Could be chimeric junctions, flagged kmers, etc.
- Quality of seed affects final assembly quality

**Convergence**: Assembly stops making progress
- Key termination condition
- May indicate complete context capture or assembly limitations

### Bioinformatics Tools Context

This pipeline likely integrates:
- **Assembly tools**: SPAdes, MEGAHIT, etc.
- **Read processing**: BBTools, Trimmomatic
- **K-mer operations**: Jellyfish, KMC, custom implementations
- **Alignment**: BWA, Bowtie2

When upgrading, maintain compatibility or provide migration paths.

---

## Development Workflow

### Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/carze/outward-assembly.git
cd outward-assembly

# 2. Install Python dependencies
uv sync --extra dev

# 3. Create tools environment
mamba env create -n oa-tools -f oa_tools_env.yml --channel-priority flexible

# 4. Activate environment
mamba activate oa-tools

# 5. Run tests
uv run pytest tests/

# 6. Run main automation
uv run python automate_assembly.py [ARGS]
```

### Making Changes

1. **Create feature branch**: `git checkout -b feature/description`
2. **Make changes** with tests
3. **Run test suite**: `uv run pytest tests/ -v`
4. **Update documentation** if needed
5. **Commit with clear messages**: Follow conventional commits
6. **Push and create PR**

### CI/CD Integration

Check `.github/workflows/` for:
- Automated testing on push/PR
- Code quality checks (linting, type checking)
- Docker image builds
- Release automation

---

## Asking Claude for Help

### Architecture Decisions

**Example**:
```markdown
I need to decide between:
A) In-memory k-mer index (fast, memory-intensive)
B) On-disk k-mer database (slower, scalable)

Project context: Processing datasets with 10-100 billion reads
Hardware: Typically 128GB-512GB RAM

What are the trade-offs and which would you recommend?
```

### Code Implementation

**Example**:
```markdown
Implement a k-mer matching function with:
- Input: seed sequence (str), reads file (Path), k (int)
- Output: list of matching read pair IDs
- Requirements: memory-efficient, handles 1B+ reads
- Use type hints and docstrings

Consider using a bloom filter for first-pass filtering.
```

### Debugging

**Example**:
```markdown
The assembly convergence check is failing for edge cases.

Current code: [PASTE CODE]
Issue: Sometimes converges prematurely when progress is still possible
Test case that fails: [DESCRIBE]

Help me identify the bug and propose a fix.
```

### Testing Strategy

**Example**:
```markdown
I need comprehensive tests for the automated assembly module.

Current coverage: [X]%
Gaps: [LIST AREAS]

Generate a testing strategy with:
1. Unit tests for core functions
2. Integration tests for full workflows  
3. Edge cases and error conditions
4. Parameterized tests for various configurations
```

---

## Common Upgrade Patterns

### Pattern 1: Modernizing Configuration

**Before** (dict-based):
```python
def run_assembly(config: dict) -> None:
    k = config.get('kmer_size', 31)
    max_iter = config.get('max_iterations', 10)
    # ... more config extraction
```

**After** (Pydantic):
```python
from pydantic import BaseModel, Field

class AssemblyConfig(BaseModel):
    kmer_size: int = Field(default=31, ge=15, le=127)
    max_iterations: int = Field(default=10, ge=1, le=100)
    # ... type-safe, validated config

def run_assembly(config: AssemblyConfig) -> None:
    k = config.kmer_size
    # ... use config directly
```

### Pattern 2: Adding Type Hints

**Before**:
```python
def find_matching_reads(seed, reads_file, k):
    # ...
    return matches
```

**After**:
```python
from pathlib import Path
from typing import List, Tuple

def find_matching_reads(
    seed: str,
    reads_file: Path,
    k: int
) -> List[Tuple[str, str]]:
    """Find read pairs matching k-mers from seed sequence.
    
    Args:
        seed: DNA sequence to match against
        reads_file: Path to FASTQ file
        k: K-mer size for matching
        
    Returns:
        List of (read_id, read_sequence) tuples
    """
    # ...
    return matches
```

### Pattern 3: Error Handling

**Before**:
```python
def process_reads(file_path):
    with open(file_path) as f:
        data = f.read()
    return parse(data)
```

**After**:
```python
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ReadProcessingError(Exception):
    """Raised when read processing fails."""
    pass

def process_reads(file_path: Path) -> Optional[ParsedReads]:
    """Process reads with comprehensive error handling."""
    if not file_path.exists():
        raise FileNotFoundError(f"Reads file not found: {file_path}")
    
    try:
        with open(file_path) as f:
            data = f.read()
        return parse(data)
    except IOError as e:
        logger.error(f"Failed to read {file_path}: {e}")
        raise ReadProcessingError(f"Cannot read file: {e}") from e
    except ParseError as e:
        logger.error(f"Failed to parse {file_path}: {e}")
        return None
```

---

## Performance Optimization Guide

### Profiling Strategy

1. **Identify bottlenecks**:
```bash
uv run python -m cProfile -o profile.stats automate_assembly.py [args]
uv run python -m pstats profile.stats
```

2. **Memory profiling**:
```bash
uv run mprof run automate_assembly.py [args]
uv run mprof plot
```

3. **Line-by-line profiling**:
```python
from line_profiler import profile

@profile
def hotpath_function():
    # ...
```

### Common Optimization Targets

1. **K-mer operations** - Often the bottleneck
   - Use efficient data structures (sets, bloom filters)
   - Consider parallelization
   - Batch operations when possible

2. **File I/O** - Can dominate runtime
   - Stream processing for large files
   - Use memory-mapped files
   - Compress intermediate results

3. **Assembly steps** - Externally called tools
   - Optimize tool parameters
   - Use faster assemblers when appropriate
   - Parallelize independent assemblies

---

## Documentation Standards

### Code Documentation

**Module docstrings**:
```python
"""
outward_assembly.core
~~~~~~~~~~~~~~~~~~~~~

Core assembly logic for iterative contig growth.

This module implements the main assembly algorithm:
1. K-mer matching to find relevant reads
2. Assembly of matched reads
3. Filtering and convergence detection

Author: [Name]
License: MIT
"""
```

**Function docstrings** (Google style):
```python
def grow_contig(
    seed: str,
    reads: List[ReadPair],
    config: AssemblyConfig
) -> AssemblyResult:
    """Grow a contig outward from seed sequence.
    
    Iteratively finds read pairs sharing k-mers with current contig,
    assembles them, and extends the contig until convergence.
    
    Args:
        seed: Initial DNA sequence to grow from
        reads: Collection of read pairs to assemble
        config: Assembly configuration parameters
        
    Returns:
        AssemblyResult containing final contig and metadata
        
    Raises:
        AssemblyError: If assembly fails or produces invalid results
        
    Example:
        >>> config = AssemblyConfig(kmer_size=31)
        >>> result = grow_contig(seed_seq, read_pairs, config)
        >>> print(f"Final contig length: {len(result.contig)}")
    """
```

### README Updates

When adding features, update README with:
- Feature description
- Usage examples
- Parameter explanations
- Performance implications

---

## Testing Guidelines

### Test Organization

```
tests/
├── unit_tests/        # Fast, isolated tests
│   ├── test_*.py      # Unit tests for core modules
├── integration/       # Full pipeline tests
│   ├── test_automation.py
│   ├── test_cloud_operations.py  # S3/GCS integration tests
│   └── test_workflows.py
├── performance/       # Performance benchmarks
│   └── benchmark_filesystem.py
├── fixtures/          # Test data
│   ├── sample_reads.fastq
│   └── seed_sequences.fasta
└── conftest.py        # Shared fixtures
```

### Test Markers

Tests use pytest markers for selective execution:

- `unit`: Fast unit tests (always run in CI)
- `fast`: Very fast tests (<1s)
- `integration`: Integration tests (may be slow)
- `requires_cloud`: Requires cloud credentials (S3_TEST_BUCKET, GCS_TEST_BUCKET)
- `requires_tools`: Requires bioinformatics tools (BBDuk, KMC, MEGAHIT)
- `slow`: Slow tests (>10s)
- `benchmark`: Performance benchmarks (use --benchmark-only)

### Test Examples

**Unit test**:
```python
import pytest
from outward_assembly.core import extract_kmers

def test_extract_kmers_basic():
    sequence = "ATCGATCG"
    k = 3
    expected = ["ATC", "TCG", "CGA", "GAT", "ATC", "TCG"]
    assert extract_kmers(sequence, k) == expected

def test_extract_kmers_edge_cases():
    # Sequence shorter than k
    with pytest.raises(ValueError):
        extract_kmers("AT", 3)
    
    # Empty sequence
    assert extract_kmers("", 3) == []
    
    # k = 1
    assert extract_kmers("ACG", 1) == ["A", "C", "G"]
```

**Integration test**:
```python
from pathlib import Path
import pytest
from outward_assembly.automation import run_automated_assembly

@pytest.fixture
def sample_data(tmp_path):
    """Create sample test data."""
    seed_file = tmp_path / "seed.fasta"
    seed_file.write_text(">seed\nATCGATCGATCG\n")
    
    reads_file = tmp_path / "reads.fastq"
    reads_file.write_text("@read1\nATCGATCG\n+\nIIIIIIII\n")
    
    return seed_file, reads_file

def test_automated_assembly_end_to_end(sample_data, tmp_path):
    """Test full automated assembly workflow."""
    seed_file, reads_file = sample_data
    output_dir = tmp_path / "output"
    
    result = run_automated_assembly(
        seed_file=seed_file,
        reads_file=reads_file,
        output_dir=output_dir,
        config=default_config()
    )
    
    assert result.success
    assert (output_dir / "final_contigs.fasta").exists()
    assert result.iterations > 0
```

---

## Troubleshooting Common Issues

### Issue 1: Environment Setup Failures

**Symptom**: Mamba environment creation fails
**Solutions**:
- Check channel priorities: `mamba config --show channels`
- Try `mamba clean --all` to clear cache
- Use `--channel-priority flexible` flag
- Check for platform-specific package availability

### Issue 2: Memory Issues with Large Datasets

**Symptom**: Out of memory errors during assembly
**Solutions**:
- Implement streaming/chunked processing
- Use memory-mapped files
- Adjust k-mer size (smaller k = less memory)
- Process data in batches
- Consider using Rust extensions for critical paths

### Issue 3: Slow Assembly Convergence

**Symptom**: Assembly runs for many iterations without converging
**Solutions**:
- Adjust k-mer size
- Implement better convergence criteria
- Add early stopping based on marginal improvement
- Profile to identify specific bottlenecks

### Issue 4: Nextflow Pipeline Failures

**Symptom**: Workflow fails at specific process
**Solutions**:
- Check `.nextflow.log` for details
- Verify container/conda environment has all tools
- Check resource allocation (memory, CPUs)
- Test process in isolation

---

## Version Control Best Practices

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(assembly): add adaptive k-mer size selection

Implements dynamic k-mer sizing based on coverage depth and 
sequence complexity. Improves convergence rate by ~30% on 
complex metagenomic samples.

Closes #123
```

```
fix(automation): handle edge case in convergence detection

Fixed issue where convergence was detected prematurely when
assembly made minimal but meaningful progress.

Fixes #456
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `perf/description` - Performance improvements

---

## Claude Interaction Templates

### 1. Feature Development

```markdown
**Context**: I want to add [FEATURE_NAME] to outward-assembly.

**Current State**: [DESCRIBE CURRENT IMPLEMENTATION]

**Desired Outcome**: [SPECIFIC GOAL]

**Constraints**:
- Must maintain backward compatibility with existing configs
- Should handle datasets up to [SIZE]
- Must integrate with existing Nextflow workflows

**Request**: 
1. Review current architecture at [FILE_PATH]
2. Propose design for [FEATURE_NAME]
3. Identify files that need modification
4. Provide implementation with tests
```

### 2. Code Review

```markdown
**Review Request**: [MODULE/FILE NAME]

**Context**: [WHAT DOES THIS CODE DO]

**Focus Areas**:
- [ ] Type safety and error handling
- [ ] Performance considerations
- [ ] Memory efficiency for large datasets
- [ ] Code organization and readability
- [ ] Test coverage

**Specific Concerns**: [ANY PARTICULAR ISSUES]

Code: [PASTE CODE OR FILE PATH]
```

### 3. Debugging Session

```markdown
**Bug Report**: [BRIEF DESCRIPTION]

**Environment**:
- Python version: [VERSION]
- uv version: [VERSION]
- OS: [OS_INFO]

**Steps to Reproduce**:
1. [STEP 1]
2. [STEP 2]
3. [STEP 3]

**Expected**: [WHAT SHOULD HAPPEN]

**Actual**: [WHAT ACTUALLY HAPPENS]

**Relevant Code**: [PASTE CODE SECTION]

**Error Message**: 
```
[PASTE FULL ERROR TRACEBACK]
```

**Already Tried**: [WHAT YOU'VE ATTEMPTED]
```

### 4. Performance Optimization

```markdown
**Performance Issue**: [DESCRIPTION]

**Profiling Data**:
```
[PASTE PROFILER OUTPUT]
```

**Current Performance**: [METRICS]
**Target Performance**: [GOALS]

**Constraints**:
- Available memory: [AMOUNT]
- CPU cores: [COUNT]
- Dataset size: [SIZE]

**Request**: Analyze bottlenecks and propose optimizations
```

### 5. Architecture Planning

```markdown
**Planning Session**: [PROJECT AREA]

**Background**: [CONTEXT]

**Requirements**:
1. [REQ 1]
2. [REQ 2]
3. [REQ 3]

**Trade-offs to Consider**:
- Performance vs. Memory
- Simplicity vs. Flexibility
- Compatibility vs. Modernization

**Request**: Help design architecture that balances these concerns
```

---

## Continuous Improvement Checklist

When working on upgrades, systematically address:

- [ ] **Dependencies**: Update to latest stable versions
- [ ] **Type Hints**: Add type annotations throughout
- [ ] **Error Handling**: Comprehensive exception handling
- [ ] **Logging**: Structured logging with appropriate levels
- [ ] **Tests**: Increase coverage, add edge cases
- [ ] **Documentation**: Update docstrings, README, usage guides
- [ ] **Performance**: Profile and optimize hot paths
- [ ] **Code Quality**: Run linters (ruff, mypy, black)
- [ ] **Security**: Audit dependencies for vulnerabilities
- [ ] **CI/CD**: Ensure all checks pass
- [ ] **Backward Compatibility**: Maintain or document breaking changes

---

## Resources

### Official Documentation
- [Project Docs](https://github.com/carze/outward-assembly/tree/main/docs)
- [Installation Guide](https://github.com/carze/outward-assembly/blob/main/docs/installation.md)
- [Usage Guide](https://github.com/carze/outward-assembly/blob/main/docs/usage.md)
- [Algorithm Details](https://github.com/carze/outward-assembly/blob/main/docs/algorithm_details.md)

### Development Tools
- [uv Documentation](https://docs.astral.sh/uv/)
- [Nextflow Documentation](https://www.nextflow.io/docs/latest/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)

### Bioinformatics Resources
- [BioPython](https://biopython.org/)
- [Sequence Assembly Algorithms](https://en.wikipedia.org/wiki/Sequence_assembly)
- [K-mer Analysis](https://en.wikipedia.org/wiki/K-mer)

---

## Quick Reference Commands

```bash
# Development
uv sync --extra dev                    # Install dependencies
uv run pytest tests/ -v                # Run tests
uv run python automate_assembly.py     # Run main script
uv add <package>                       # Add new dependency

# Environment
mamba activate oa-tools                # Activate tools env
mamba env update -f oa_tools_env.yml   # Update tools env
mamba list                             # List installed packages

# Code Quality
uv run ruff check .                    # Lint code
uv run ruff format .                   # Format code
uv run mypy outward_assembly/          # Type checking

# Testing
pixi run --environment dev pytest tests/ -v                              # Run all tests
pixi run --environment dev pytest tests/ -v -m "not requires_cloud"      # Skip cloud tests
pixi run --environment dev pytest tests/integration/ -v -m "requires_cloud"  # Cloud tests only
pixi run --environment dev pytest tests/performance/ --benchmark-only    # Run benchmarks
pixi run --environment dev pytest tests/ -k test_name                    # Run specific test
pixi run --environment dev pytest tests/ -x                              # Stop on first failure
pixi run --environment dev pytest tests/ --cov                           # Test with coverage

# Git
git checkout -b feature/name           # Create feature branch
git commit -m "type(scope): message"   # Commit with convention
git push origin feature/name           # Push branch
```

---

## Contact & Support

For questions or issues:
1. Check existing [GitHub Issues](https://github.com/carze/outward-assembly/issues)
2. Review [documentation](https://github.com/carze/outward-assembly/tree/main/docs)
3. Create a new issue with detailed information

When working with Claude:
- Reference this CLAUDE.md for context
- Be specific about your goals and constraints
- Provide code snippets and error messages
- Ask for incremental steps rather than complete rewrites

---

**Last Updated**: December 2024  
**Maintainer**: [Your Name]  
**License**: MIT
