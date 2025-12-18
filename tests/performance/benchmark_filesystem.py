"""
Performance benchmarks for filesystem operations.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Benchmarks for filesystem abstraction layer to detect performance regressions
and compare local vs cloud operations. Uses pytest-benchmark for accurate timing.

Benchmarks:
- Local file read: Baseline 10MB read performance through abstraction layer
- (Future) S3 read: Compare s5cmd vs smart_open streaming
- (Future) GCS read: Verify GCS performance characteristics

Usage:
    pytest tests/performance/ -v -m benchmark --benchmark-only
    pytest tests/performance/ --benchmark-compare

Expected: <1s for 10MB local reads. Slowdowns indicate abstraction overhead.
Thread safety: Individual benchmarks are isolated; safe for concurrent runs.
"""

import pytest
from outward_assembly.fs_abstraction import get_filesystem


@pytest.mark.benchmark
def test_benchmark_local_read(benchmark, tmp_path):
    """Benchmark local file reading."""
    test_file = tmp_path / "bench.txt"
    test_file.write_bytes(b"x" * 10_000_000)  # 10MB

    fs = get_filesystem()

    def read_file():
        with fs.open(test_file, 'rb') as f:
            return f.read()

    result = benchmark(read_file)
    assert len(result) == 10_000_000
