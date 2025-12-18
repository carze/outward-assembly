"""
Cloud Integration Tests for Filesystem Abstraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Integration tests for S3 and GCS functionality using the cloud-agnostic
filesystem abstraction layer. These tests require actual cloud credentials
and will be skipped if the necessary environment variables are not set.

Required environment variables:
- S3_TEST_BUCKET: S3 bucket name for testing (e.g., "my-test-bucket")
- GCS_TEST_BUCKET: GCS bucket name for testing (e.g., "my-test-bucket")

Tests verify:
- Round-trip read/write operations to cloud storage
- Performance characteristics of different streaming methods
- Integration with full assembly pipeline using cloud inputs

Author: Generated via Claude Code
License: MIT
"""

import os
import shutil
import time
from pathlib import Path

import pytest

from outward_assembly.fs_abstraction import get_filesystem


@pytest.fixture(scope="module")
def s3_test_bucket() -> str:
    """S3 bucket for integration testing."""
    bucket = os.getenv("S3_TEST_BUCKET")
    if not bucket:
        pytest.skip("S3_TEST_BUCKET not set")
    return bucket


@pytest.fixture(scope="module")
def gcs_test_bucket() -> str:
    """GCS bucket for integration testing."""
    bucket = os.getenv("GCS_TEST_BUCKET")
    if not bucket:
        pytest.skip("GCS_TEST_BUCKET not set")
    return bucket


@pytest.mark.integration
@pytest.mark.requires_cloud
def test_s3_file_roundtrip(s3_test_bucket: str, tmp_path: Path) -> None:
    """Test reading and writing to S3."""
    fs = get_filesystem()

    test_content = "Integration test content\n" * 1000
    s3_path = f"s3://{s3_test_bucket}/test/roundtrip.txt"
    local_path = tmp_path / "local.txt"

    # Write to S3
    with fs.open(s3_path, 'w') as f:
        f.write(test_content)

    # Read from S3
    with fs.open(s3_path, 'r') as f:
        read_content = f.read()

    assert read_content == test_content

    # Copy S3 -> local
    fs.copy(s3_path, local_path)
    assert local_path.read_text() == test_content


@pytest.mark.integration
@pytest.mark.requires_cloud
@pytest.mark.slow
def test_s5cmd_streaming_performance(s3_test_bucket: str, tmp_path: Path) -> None:
    """Benchmark s5cmd streaming vs smart_open."""
    if not shutil.which('s5cmd'):
        pytest.skip("s5cmd not installed")

    fs = get_filesystem()

    # Create 100MB test file
    test_data = b"x" * (100 * 1024 * 1024)
    s3_path = f"s3://{s3_test_bucket}/test/100mb.dat"

    with fs.open(s3_path, 'wb') as f:
        f.write(test_data)

    # Test s5cmd streaming
    fs_s5cmd = get_filesystem(prefer_native_tools=True)
    start = time.time()
    with fs_s5cmd.open(s3_path, 'rb') as f:
        _ = f.read()
    s5cmd_time = time.time() - start

    # Test smart_open fallback
    fs_smart = get_filesystem(prefer_native_tools=False)
    start = time.time()
    with fs_smart.open(s3_path, 'rb') as f:
        _ = f.read()
    smart_time = time.time() - start

    print(f"\ns5cmd: {s5cmd_time:.2f}s")
    print(f"smart_open: {smart_time:.2f}s")
    print(f"Speedup: {smart_time/s5cmd_time:.1f}x")

    # s5cmd should be faster
    assert s5cmd_time < smart_time


@pytest.mark.integration
@pytest.mark.requires_cloud
@pytest.mark.requires_tools
@pytest.mark.slow
@pytest.mark.skip(reason="Full assembly test implementation pending - requires test data fixtures")
def test_full_assembly_s3_inputs(s3_test_bucket: str, tmp_path: Path) -> None:
    """
    Test full assembly pipeline with S3 inputs.

    This is the ultimate integration test - runs actual outward_assembly
    with cloud storage for inputs and outputs.
    """
    # Setup: upload test data to S3
    # ... (implementation)
