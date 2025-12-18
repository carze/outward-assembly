"""Tests for filesystem abstraction layer."""

import pytest
from pathlib import Path
from io import BytesIO, StringIO
from unittest.mock import Mock, patch, MagicMock, call
import subprocess

from outward_assembly.fs_abstraction import (
    FilesystemAbstraction,
    FilesystemError,
    FilesystemNotFoundError,
    get_filesystem,
)


@pytest.fixture
def fs():
    """Create filesystem abstraction instance."""
    return FilesystemAbstraction()


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content\n")
    return test_file


@pytest.mark.unit
@pytest.mark.fast
def test_is_remote_detection(fs):
    """Test remote path detection."""
    assert fs._is_remote("s3://bucket/key")
    assert fs._is_remote("gs://bucket/key")
    assert fs._is_remote("azure://container/blob")
    assert not fs._is_remote("/local/path")
    assert not fs._is_remote("relative/path")


@pytest.mark.unit
@pytest.mark.fast
def test_is_s3(fs):
    """Test S3 path detection."""
    assert fs._is_s3("s3://bucket/key")
    assert not fs._is_s3("gs://bucket/key")
    assert not fs._is_s3("/local/path")


@pytest.mark.unit
@pytest.mark.fast
def test_is_gcs(fs):
    """Test GCS path detection."""
    assert fs._is_gcs("gs://bucket/key")
    assert not fs._is_gcs("s3://bucket/key")
    assert not fs._is_gcs("/local/path")


@pytest.mark.unit
@pytest.mark.fast
def test_open_local_file_read(fs, temp_file):
    """Test opening local file for reading."""
    with fs.open(temp_file, 'r') as f:
        content = f.read()
    assert content == "test content\n"


@pytest.mark.unit
@pytest.mark.fast
def test_open_local_file_write(fs, tmp_path):
    """Test opening local file for writing."""
    test_file = tmp_path / "output.txt"
    with fs.open(test_file, 'w') as f:
        f.write("new content")

    assert test_file.read_text() == "new content"


@pytest.mark.unit
@pytest.mark.fast
def test_exists_local_file(fs, temp_file):
    """Test checking if local file exists."""
    assert fs.exists(temp_file)
    assert not fs.exists(temp_file.parent / "nonexistent.txt")


@pytest.mark.unit
@pytest.mark.fast
def test_copy_local_to_local(fs, temp_file, tmp_path):
    """Test copying between local paths."""
    dest = tmp_path / "copy.txt"
    fs.copy(temp_file, dest)
    assert dest.exists()
    assert dest.read_text() == "test content\n"


@pytest.mark.unit
@pytest.mark.fast
def test_list_local_files(fs, tmp_path):
    """Test listing local files."""
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.txt").touch()
    (tmp_path / "file3.dat").touch()

    all_files = fs.list_files(tmp_path)
    assert len(all_files) == 3

    txt_files = fs.list_files(tmp_path, pattern="*.txt")
    assert len(txt_files) == 2


@pytest.mark.unit
@pytest.mark.fast
def test_stream_download_local(fs, temp_file):
    """Test streaming download from local file."""
    chunks = list(fs.stream_download(temp_file, chunk_size=4))
    content = b''.join(chunks)
    assert content == b"test content\n"


@pytest.mark.unit
@pytest.mark.fast
def test_file_not_found_error(fs):
    """Test proper exception when file not found."""
    with pytest.raises(FilesystemNotFoundError):
        fs.open("/nonexistent/file.txt", 'r')


@pytest.mark.unit
def test_s5cmd_used_for_s3_when_available(monkeypatch):
    """s5cmd should be used for S3 URIs when available."""
    monkeypatch.setattr('shutil.which', lambda cmd: '/usr/bin/s5cmd' if cmd == 's5cmd' else None)

    fs = FilesystemAbstraction()

    with patch('subprocess.Popen') as mock_popen:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b''
        mock_popen.return_value = mock_proc

        fs.stream_to_process("s3://bucket/file.fastq", ["cat"])

        # Verify s5cmd was called
        calls = [str(call) for call in mock_popen.call_args_list]
        assert any('s5cmd' in call for call in calls)


@pytest.mark.unit
def test_s5cmd_with_gcs_endpoint(monkeypatch):
    """s5cmd should be called with --endpoint-url for GCS."""
    monkeypatch.setattr('shutil.which', lambda cmd: '/usr/bin/s5cmd' if cmd == 's5cmd' else None)

    fs = FilesystemAbstraction()

    with patch('subprocess.Popen') as mock_popen:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.wait.return_value = 0
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b''
        mock_popen.return_value = mock_proc

        fs.stream_to_process("gs://bucket/file.fastq", ["cat"])

        # Verify s5cmd was called with GCS endpoint
        first_call = mock_popen.call_args_list[0]
        cmd = first_call[0][0]

        assert 's5cmd' in cmd
        assert '--endpoint-url' in cmd
        assert 'https://storage.googleapis.com' in cmd


@pytest.mark.unit
def test_smart_open_used_for_local_files(monkeypatch):
    """smart_open should be used for local files (s5cmd can't stream them)."""
    monkeypatch.setattr('shutil.which', lambda cmd: '/usr/bin/s5cmd' if cmd == 's5cmd' else None)

    fs = FilesystemAbstraction()

    with patch('smart_open.open') as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b''
        mock_open.return_value = mock_file

        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            fs.stream_to_process("/local/file.fastq", ["cat"])

            # Verify smart_open was used, NOT s5cmd
            mock_open.assert_called()


@pytest.mark.unit
def test_fallback_to_smart_open_when_no_s5cmd():
    """smart_open should be used for S3 when s5cmd unavailable."""
    fs = FilesystemAbstraction(prefer_native_tools=False)

    with patch('smart_open.open') as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b''
        mock_open.return_value = mock_file

        with patch('subprocess.Popen') as mock_popen:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            fs.stream_to_process("s3://bucket/file.fastq", ["cat"])

            # Verify smart_open was used for S3
            mock_open.assert_called()


@pytest.mark.unit
@patch('outward_assembly.fs_abstraction.boto3_client')
def test_list_s3_files_mocked(mock_boto, fs):
    """Test listing S3 files (mocked)."""
    mock_s3 = Mock()
    mock_paginator = Mock()
    mock_s3.get_paginator.return_value = mock_paginator
    mock_boto.return_value = mock_s3

    mock_paginator.paginate.return_value = [
        {
            'Contents': [
                {'Key': 'prefix/file1.fastq.zst'},
                {'Key': 'prefix/file2.fastq.zst'},
            ]
        }
    ]

    files = fs.list_files("s3://bucket/prefix/", pattern="*.fastq.zst")
    assert len(files) == 2
    assert all(f.startswith("s3://bucket/") for f in files)


@pytest.mark.unit
@pytest.mark.fast
def test_is_azure(fs):
    """Test Azure URI detection."""
    assert fs._is_azure("azure://container/blob")
    assert not fs._is_azure("s3://bucket/key")
    assert not fs._is_azure("gs://bucket/key")
    assert not fs._is_azure("/local/path")


@pytest.mark.unit
@pytest.mark.fast
def test_open_permission_error(fs, tmp_path):
    """Test PermissionError wrapping."""
    from outward_assembly.fs_abstraction import FilesystemPermissionError

    # Create a file with no read permissions
    restricted_file = tmp_path / "restricted.txt"
    restricted_file.write_text("content")
    restricted_file.chmod(0o000)

    try:
        with pytest.raises(FilesystemPermissionError):
            fs.open(restricted_file, 'r')
    finally:
        # Cleanup: restore permissions
        restricted_file.chmod(0o644)


@pytest.mark.unit
@pytest.mark.fast
def test_open_generic_error(fs):
    """Test generic exception wrapping."""
    with patch('smart_open.open', side_effect=ValueError("Invalid mode")):
        with pytest.raises(FilesystemError):
            fs.open("s3://bucket/key", 'invalid_mode')


@pytest.mark.unit
def test_exists_remote_file(fs):
    """Test exists() for remote URIs with mocking."""
    with patch.object(fs, 'open') as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b'data'
        mock_open.return_value = mock_file

        assert fs.exists("s3://bucket/existing.txt")
        mock_open.assert_called_with("s3://bucket/existing.txt", 'rb')


@pytest.mark.unit
def test_stream_to_process_with_output_s5cmd(monkeypatch, tmp_path):
    """Test s5cmd with output file."""
    monkeypatch.setattr('shutil.which', lambda cmd: '/usr/bin/s5cmd' if cmd == 's5cmd' else None)

    fs = FilesystemAbstraction()
    output_file = tmp_path / "output.txt"

    with patch('subprocess.Popen') as mock_popen:
        # Mock s5cmd process
        mock_s5cmd = MagicMock()
        mock_s5cmd.returncode = 0
        mock_s5cmd.wait.return_value = 0
        mock_s5cmd.stdout = MagicMock()
        mock_s5cmd.stderr = MagicMock()
        mock_s5cmd.stderr.read.return_value = b''

        # Mock target process
        mock_target = MagicMock()
        mock_target.returncode = 0
        mock_target.wait.return_value = 0
        mock_target.stderr = MagicMock()
        mock_target.stderr.read.return_value = b''

        mock_popen.side_effect = [mock_s5cmd, mock_target]

        fs.stream_to_process("s3://bucket/file.fastq", ["cat"], output_path=output_file)

        assert mock_popen.call_count == 2


@pytest.mark.unit
def test_stream_to_process_with_output_smart_open(fs, tmp_path):
    """Test smart_open with output file."""
    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"test data")
    output_file = tmp_path / "output.txt"

    with patch('subprocess.Popen') as mock_popen:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdin = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b''
        mock_proc.wait.return_value = 0
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        fs.stream_to_process(input_file, ["cat"], output_path=output_file)

        assert mock_popen.called


@pytest.mark.unit
def test_stream_to_process_failure_s5cmd(monkeypatch):
    """Test target process failure."""
    monkeypatch.setattr('shutil.which', lambda cmd: '/usr/bin/s5cmd' if cmd == 's5cmd' else None)

    fs = FilesystemAbstraction()

    with patch('subprocess.Popen') as mock_popen:
        mock_s5cmd = MagicMock()
        mock_s5cmd.returncode = 0
        mock_s5cmd.stdout = MagicMock()
        mock_s5cmd.stderr = MagicMock()
        mock_s5cmd.stderr.read.return_value = b''

        mock_target = MagicMock()
        mock_target.returncode = 1
        mock_target.stderr = MagicMock()
        mock_target.stderr.read.return_value = b'Process error'

        mock_popen.side_effect = [mock_s5cmd, mock_target]

        with pytest.raises(FilesystemError, match="Process failed"):
            fs.stream_to_process("s3://bucket/file.fastq", ["false"])


@pytest.mark.unit
def test_stream_to_process_s5cmd_failure(monkeypatch):
    """Test s5cmd command failure."""
    monkeypatch.setattr('shutil.which', lambda cmd: '/usr/bin/s5cmd' if cmd == 's5cmd' else None)

    fs = FilesystemAbstraction()

    with patch('subprocess.Popen') as mock_popen:
        mock_s5cmd = MagicMock()
        mock_s5cmd.returncode = 1
        mock_s5cmd.stdout = MagicMock()
        mock_s5cmd.stderr = MagicMock()
        mock_s5cmd.stderr.read.return_value = b's5cmd error: file not found'

        mock_target = MagicMock()
        mock_target.returncode = 0
        mock_target.stderr = MagicMock()
        mock_target.stderr.read.return_value = b''

        mock_popen.side_effect = [mock_s5cmd, mock_target]

        with pytest.raises(FilesystemError, match="s5cmd failed"):
            fs.stream_to_process("s3://bucket/nonexistent.fastq", ["cat"])


@pytest.mark.unit
def test_stream_to_process_smart_open_failure(fs, tmp_path):
    """Test smart_open process failure."""
    input_file = tmp_path / "input.txt"
    input_file.write_bytes(b"test data")

    with patch('subprocess.Popen') as mock_popen:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdin = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.stderr.read.return_value = b'Command failed'
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        with pytest.raises(FilesystemError, match="Process failed"):
            fs.stream_to_process(input_file, ["false"])


@pytest.mark.unit
def test_copy_cloud_to_local(fs):
    """Test S3 to local copy."""
    with patch.object(fs, 'open') as mock_open:
        mock_src = MagicMock()
        mock_dst = MagicMock()

        mock_src.__enter__.return_value.read.side_effect = [b'data chunk', b'']
        mock_dst.__enter__.return_value = MagicMock()

        mock_open.side_effect = [mock_src, mock_dst]

        fs.copy("s3://bucket/file.txt", "/local/file.txt")

        assert mock_open.call_count == 2
        mock_dst.__enter__.return_value.write.assert_called_with(b'data chunk')


@pytest.mark.unit
def test_copy_local_to_cloud(fs, tmp_path):
    """Test local to S3 copy."""
    src_file = tmp_path / "source.txt"
    src_file.write_bytes(b"test content")

    # Mock only the cloud file opening, not local files
    original_open = fs.open

    with patch.object(fs, 'open') as mock_open:
        mock_cloud_file = MagicMock()
        mock_cloud_file.__enter__.return_value = MagicMock()

        def open_side_effect(path, mode, **kwargs):
            if str(path).startswith("s3://"):
                return mock_cloud_file
            # For local files, call the original method
            return original_open(path, mode, **kwargs)

        mock_open.side_effect = open_side_effect

        fs.copy(src_file, "s3://bucket/destination.txt")

        mock_cloud_file.__enter__.return_value.write.assert_called()


@pytest.mark.unit
def test_open_remote_file_with_smart_open(fs):
    """Test remote file opening."""
    with patch('smart_open.open') as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b'remote content'
        mock_open.return_value = mock_file

        with fs.open("s3://bucket/file.txt", 'rb') as f:
            content = f.read()

        mock_open.assert_called_once()
        assert content == b'remote content'


@pytest.mark.unit
def test_open_local_with_compression(fs, tmp_path):
    """Test opening local file with compression."""
    test_file = tmp_path / "compressed.txt"

    with patch('smart_open.open') as mock_open:
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = b'compressed content'
        mock_open.return_value = mock_file

        with fs.open(test_file, 'rb', compression='gzip') as f:
            content = f.read()

        mock_open.assert_called_once()
        assert content == b'compressed content'


@pytest.mark.unit
@pytest.mark.fast
def test_is_azure(fs):
    """Test Azure path detection."""
    assert fs._is_azure("azure://container/blob")
    assert fs._is_azure("az://container/blob")
    assert not fs._is_azure("s3://bucket/key")
    assert not fs._is_azure("gs://bucket/key")
    assert not fs._is_azure("/local/path")


@pytest.mark.unit
@pytest.mark.fast
def test_open_permission_error(fs, tmp_path):
    """Test handling of permission errors when opening files."""
    test_file = tmp_path / "readonly.txt"
    test_file.write_text("content")
    test_file.chmod(0o000)

    try:
        with pytest.raises(FilesystemError):
            fs.open(test_file, 'r')
    finally:
        test_file.chmod(0o644)


@pytest.mark.unit
@pytest.mark.fast
def test_open_generic_error(fs):
    """Test handling of generic errors when opening files."""
    with patch('pathlib.Path.open', side_effect=IOError("Generic error")):
        with pytest.raises(FilesystemError):
            fs.open("/some/path.txt", 'r')


@pytest.mark.unit
def test_exists_remote_file(fs):
    """Test checking existence of remote files."""
    with patch('smart_open.open') as mock_open:
        mock_open.return_value.__enter__.return_value = BytesIO(b"data")
        assert fs.exists("s3://bucket/key")

    with patch('smart_open.open', side_effect=Exception("Not found")):
        assert not fs.exists("s3://bucket/nonexistent")


@pytest.mark.unit
def test_list_gcs_files_mocked(fs):
    """Test listing GCS files (mocked)."""
    # Mock the google.cloud.storage module
    with patch('google.cloud.storage.Client') as mock_client_class:
        mock_client = Mock()
        mock_bucket = Mock()
        mock_client_class.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket

        mock_blob1 = Mock()
        mock_blob1.name = 'prefix/file1.fastq.zst'
        mock_blob2 = Mock()
        mock_blob2.name = 'prefix/file2.fastq.zst'

        mock_bucket.list_blobs.return_value = [mock_blob1, mock_blob2]

        files = fs.list_files("gs://bucket/prefix/", pattern="*.fastq.zst")
        assert len(files) == 2
        assert all(f.startswith("gs://bucket/") for f in files)
