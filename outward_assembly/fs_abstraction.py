"""
Cloud-agnostic filesystem abstraction using s5cmd and smart_open.

This module provides a unified interface for file operations across:
- Local filesystem
- AWS S3 (s3://) - via s5cmd (fast) or smart_open (fallback)
- Google Cloud Storage (gs://) - via s5cmd (fast) or smart_open (fallback)
- Azure Blob Storage (azure://) - via smart_open

Streaming Strategy:
- s5cmd for S3/GCS: 1-2 GB/s (if available)
- smart_open for local/Azure/fallback: 200-400 MB/s

All operations support true streaming to minimize memory usage and handle
terabyte-scale data without requiring disk space for temporary files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Iterator, List, Optional, Union
from urllib.parse import urlparse

import smart_open
from boto3 import client as boto3_client

# Type alias for path-like objects
PathLike = Union[str, Path]


class FilesystemError(Exception):
    """Base exception for filesystem operations."""
    pass


class FilesystemNotFoundError(FilesystemError):
    """Raised when a file or directory is not found."""
    pass


class FilesystemPermissionError(FilesystemError):
    """Raised when permission is denied for an operation."""
    pass


class FilesystemAbstraction:
    """
    Unified filesystem abstraction supporting local and cloud storage.

    This class provides cloud-agnostic file operations using s5cmd for
    high-performance cloud streaming and smart_open for universal compatibility.

    Configuration:
        Cloud credentials are read from environment variables or standard
        credential files (~/.aws/credentials, ~/.config/gcloud/, etc.)
        following each cloud provider's standard credential chain.

    Example:
        >>> fs = FilesystemAbstraction()

        # High-performance cloud streaming (uses s5cmd if available)
        >>> fs.stream_to_process(
        ...     "s3://bucket/reads.fastq.zst",
        ...     ["bbduk.sh", "in=stdin.fq", "out=filtered.fq"]
        ... )

        # Works identically for GCS
        >>> fs.stream_to_process(
        ...     "gs://bucket/reads.fastq.zst",
        ...     ["bbduk.sh", "in=stdin.fq", "out=filtered.fq"]
        ... )

        # And local files
        >>> fs.stream_to_process(
        ...     "/local/reads.fastq.zst",
        ...     ["bbduk.sh", "in=stdin.fq", "out=filtered.fq"]
        ... )
    """

    def __init__(
        self,
        transport_params: Optional[dict] = None,
        default_compression: Optional[str] = None,
        prefer_native_tools: bool = True
    ):
        """
        Initialize filesystem abstraction.

        Args:
            transport_params: Optional parameters passed to smart_open
                (e.g., {'client': boto3_client('s3')})
            default_compression: Default compression to apply
                (e.g., 'gzip', 'zstd', 'infer_from_extension')
            prefer_native_tools: Use s5cmd for S3/GCS when available
                (set False for pure Python mode in testing)
        """
        self.transport_params = transport_params or {}
        self.default_compression = default_compression
        self.prefer_native_tools = prefer_native_tools

        # Detect s5cmd availability
        self._has_s5cmd = shutil.which('s5cmd') is not None

        # GCS endpoint for s5cmd
        self._gcs_endpoint = "https://storage.googleapis.com"

    def _is_remote(self, path: PathLike) -> bool:
        """Check if path is a remote URI (s3://, gs://, etc.)."""
        path_str = str(path)
        parsed = urlparse(path_str)
        return parsed.scheme in ('s3', 'gs', 'azure', 'hdfs', 'http', 'https')

    def _is_s3(self, path: PathLike) -> bool:
        """Check if path is S3 URI."""
        return str(path).startswith('s3://')

    def _is_gcs(self, path: PathLike) -> bool:
        """Check if path is GCS URI."""
        return str(path).startswith('gs://')

    def _is_azure(self, path: PathLike) -> bool:
        """Check if path is Azure URI."""
        path_str = str(path)
        return path_str.startswith('azure://') or path_str.startswith('az://')

    def open(
        self,
        path: PathLike,
        mode: str = "r",
        compression: Optional[str] = None,
        **kwargs
    ):
        """
        Open file for reading or writing (cloud or local).

        Returns a file-like object compatible with standard Python I/O.
        For remote paths, uses smart_open. For local paths, uses built-in open
        or smart_open (if compression needed).

        Args:
            path: Local path or remote URI (s3://bucket/key, gs://bucket/key)
            mode: File open mode ('r', 'w', 'rb', 'wb', etc.)
            compression: Compression type ('gzip', 'zstd', 'infer_from_extension', None)
            **kwargs: Additional arguments passed to smart_open or open

        Returns:
            File-like object (TextIO or BinaryIO)

        Raises:
            FilesystemNotFoundError: If file doesn't exist (mode='r')
            FilesystemPermissionError: If permission denied
            FilesystemError: For other I/O errors

        Example:
            >>> with fs.open("s3://bucket/reads.fastq.zst", "rb") as f:
            ...     for line in f:
            ...         process(line)
        """
        compression = compression or self.default_compression

        try:
            if self._is_remote(path):
                # Use smart_open for cloud paths
                return smart_open.open(
                    str(path),
                    mode=mode,
                    compression=compression,
                    transport_params=self.transport_params,
                    **kwargs
                )
            else:
                # Local file
                local_path = Path(path)

                # Use smart_open if compression needed, otherwise standard open
                if compression and compression != 'disable':
                    return smart_open.open(
                        str(path),
                        mode=mode,
                        compression=compression,
                        **kwargs
                    )
                else:
                    return open(local_path, mode=mode, **kwargs)

        except FileNotFoundError as e:
            raise FilesystemNotFoundError(f"File not found: {path}") from e
        except PermissionError as e:
            raise FilesystemPermissionError(f"Permission denied: {path}") from e
        except Exception as e:
            raise FilesystemError(f"Error opening {path}: {e}") from e

    def exists(self, path: PathLike) -> bool:
        """
        Check if file or directory exists.

        Args:
            path: Local path or remote URI

        Returns:
            True if exists, False otherwise
        """
        if self._is_remote(path):
            # For cloud, try to open and catch exception
            try:
                with self.open(path, 'rb') as f:
                    f.read(1)
                return True
            except FilesystemNotFoundError:
                return False
            except Exception:
                return False  # Other errors indicate file doesn't exist or can't be accessed
        else:
            return Path(path).exists()

    def stream_to_process(
        self,
        path: PathLike,
        process_cmd: List[str],
        output_path: Optional[PathLike] = None
    ) -> None:
        """
        Stream file to subprocess stdin (replaces 'aws s3 cp - | tool').

        This is the PRIMARY method for bioinformatics tool integration.
        Automatically selects optimal streaming method:
        - s5cmd for S3/GCS (if available): 1-2 GB/s
        - smart_open for local/Azure/fallback: 200-400 MB/s

        Handles:
        - Cloud streaming (S3/GCS via s5cmd or smart_open)
        - Automatic decompression (.zst, .gz, .bz2)
        - Local file streaming
        - No temp files (true end-to-end streaming)

        Args:
            path: Source path/URI (s3://, gs://, /local, etc.)
            process_cmd: Command to run (e.g., ['bbduk.sh', 'in=stdin.fq', ...])
            output_path: Optional path to write process output

        Raises:
            FilesystemNotFoundError: If source doesn't exist
            FilesystemError: On streaming or process failure

        Example:
            >>> # Stream S3 file through BBDuk (no temp files!)
            >>> fs.stream_to_process(
            ...     "s3://bucket/reads.fastq.zst",
            ...     ["bbduk.sh", "in=stdin.fq", "out=filtered.fq"]
            ... )

            >>> # Works identically for GCS
            >>> fs.stream_to_process(
            ...     "gs://bucket/reads.fastq.zst",
            ...     ["bbduk.sh", "in=stdin.fq", "out=filtered.fq"]
            ... )

            >>> # And local files
            >>> fs.stream_to_process(
            ...     "/local/reads.fastq.zst",
            ...     ["bbduk.sh", "in=stdin.fq", "out=filtered.fq"]
            ... )
        """

        # Use s5cmd for cloud objects (S3/GCS) when available
        if self.prefer_native_tools and self._has_s5cmd:
            if self._is_s3(path) or self._is_gcs(path):
                return self._stream_via_s5cmd(path, process_cmd, output_path)

        # Fallback to smart_open for local files and other cases
        return self._stream_via_smart_open(path, process_cmd, output_path)

    def _stream_via_s5cmd(
        self,
        cloud_path: str,
        process_cmd: List[str],
        output_path: Optional[PathLike] = None
    ) -> None:
        """
        Stream S3/GCS object using s5cmd.

        Note: Only works for remote objects (s3://, gs://), not local files.
        s5cmd cat returns error for local paths.
        """

        s5cmd_cmd = ['s5cmd']

        # Add GCS endpoint if needed
        if self._is_gcs(cloud_path):
            s5cmd_cmd.extend(['--endpoint-url', self._gcs_endpoint])

        s5cmd_cmd.extend(['cat', cloud_path])

        # Start s5cmd streaming to stdout
        s5cmd_proc = subprocess.Popen(
            s5cmd_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        try:
            if output_path:
                # Stream: s5cmd stdout → process → output file
                with self.open(output_path, 'wb') as outfile:
                    target_proc = subprocess.Popen(
                        process_cmd,
                        stdin=s5cmd_proc.stdout,
                        stdout=outfile,
                        stderr=subprocess.PIPE
                    )
                    s5cmd_proc.stdout.close()  # Allow SIGPIPE if target exits
                    target_proc.wait()
                    s5cmd_proc.wait()

                    if target_proc.returncode != 0:
                        stderr = target_proc.stderr.read().decode()
                        raise FilesystemError(
                            f"Process failed: {stderr}"
                        )
            else:
                # Stream: s5cmd stdout → process stdin
                target_proc = subprocess.Popen(
                    process_cmd,
                    stdin=s5cmd_proc.stdout,
                    stderr=subprocess.PIPE
                )
                s5cmd_proc.stdout.close()  # Allow SIGPIPE
                target_proc.wait()
                s5cmd_proc.wait()

                if target_proc.returncode != 0:
                    stderr = target_proc.stderr.read().decode()
                    raise FilesystemError(
                        f"Process failed: {stderr}"
                    )

            # Check s5cmd didn't fail
            if s5cmd_proc.returncode != 0:
                stderr = s5cmd_proc.stderr.read().decode()
                raise FilesystemError(f"s5cmd failed: {stderr}")

        except Exception:
            # Cleanup on error
            if s5cmd_proc.poll() is None:
                s5cmd_proc.kill()
            raise

    def _stream_via_smart_open(
        self,
        path: PathLike,
        process_cmd: List[str],
        output_path: Optional[PathLike] = None
    ) -> None:
        """
        Stream file using smart_open.

        Works for:
        - Local files (/path/to/file)
        - S3 (s3://bucket/key) - fallback when s5cmd unavailable
        - GCS (gs://bucket/key) - fallback when s5cmd unavailable
        - Azure (azure://container/blob)

        Handles compression automatically (.gz, .zst, .bz2)
        """
        with self.open(path, 'rb', compression='infer_from_extension') as infile:
            if output_path:
                # Stream: input → process → output file
                with self.open(output_path, 'wb') as outfile:
                    proc = subprocess.Popen(
                        process_cmd,
                        stdin=subprocess.PIPE,
                        stdout=outfile,
                        stderr=subprocess.PIPE
                    )

                    try:
                        # Pump data in 8MB chunks
                        for chunk in iter(lambda: infile.read(8*1024*1024), b''):
                            proc.stdin.write(chunk)
                        proc.stdin.close()
                        proc.wait()

                        if proc.returncode != 0:
                            stderr = proc.stderr.read().decode()
                            raise FilesystemError(
                                f"Process failed: {stderr}"
                            )
                    finally:
                        if proc.poll() is None:
                            proc.kill()
            else:
                # Stream: input → process stdin
                proc = subprocess.Popen(
                    process_cmd,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                try:
                    for chunk in iter(lambda: infile.read(8*1024*1024), b''):
                        proc.stdin.write(chunk)
                    proc.stdin.close()
                    proc.wait()

                    if proc.returncode != 0:
                        stderr = proc.stderr.read().decode()
                        raise FilesystemError(
                            f"Process failed: {stderr}"
                        )
                finally:
                    if proc.poll() is None:
                        proc.kill()

    def copy(self, src: PathLike, dst: PathLike, **kwargs) -> None:
        """
        Copy file from src to dst (any combination of local/cloud).

        For local-to-local copies, uses shutil for efficiency.
        For cloud operations, uses streaming copy.

        Args:
            src: Source path/URI
            dst: Destination path/URI
            **kwargs: Additional arguments (e.g., buffer_size)

        Raises:
            FilesystemNotFoundError: If source doesn't exist
            FilesystemError: On copy failure

        Example:
            >>> fs.copy("s3://bucket/file.txt", "/local/file.txt")
            >>> fs.copy("/local/file.txt", "gs://bucket/file.txt")
        """
        buffer_size = kwargs.get('buffer_size', 8 * 1024 * 1024)  # 8MB

        try:
            # Local-to-local: use shutil for efficiency
            if not self._is_remote(src) and not self._is_remote(dst):
                shutil.copy2(str(src), str(dst))
                return

            # Any cloud operation: use streaming copy
            with self.open(src, 'rb') as src_file:
                with self.open(dst, 'wb') as dst_file:
                    while True:
                        chunk = src_file.read(buffer_size)
                        if not chunk:
                            break
                        dst_file.write(chunk)

        except FilesystemNotFoundError:
            raise
        except Exception as e:
            raise FilesystemError(f"Error copying {src} to {dst}: {e}") from e

    def list_files(
        self,
        path: PathLike,
        pattern: Optional[str] = None,
        recursive: bool = False
    ) -> List[str]:
        """
        List files in a directory or matching a cloud prefix.

        Args:
            path: Local directory or cloud URI prefix
            pattern: Glob pattern to filter results (e.g., "*.fastq.zst")
            recursive: Whether to recurse into subdirectories

        Returns:
            List of file paths/URIs

        Example:
            >>> fs.list_files("s3://bucket/reads/", pattern="*.fastq.zst")
            ['s3://bucket/reads/sample1.fastq.zst', ...]
        """
        if self._is_remote(path):
            return self._list_cloud_files(path, pattern, recursive)
        else:
            return self._list_local_files(path, pattern, recursive)

    def _list_local_files(
        self,
        path: PathLike,
        pattern: Optional[str],
        recursive: bool
    ) -> List[str]:
        """List files in local directory."""
        local_path = Path(path)
        if not local_path.is_dir():
            return []

        if recursive:
            glob_pattern = f"**/{pattern or '*'}"
            files = local_path.glob(glob_pattern)
        else:
            glob_pattern = pattern or '*'
            files = local_path.glob(glob_pattern)

        return [str(f) for f in files if f.is_file()]

    def _list_cloud_files(
        self,
        path: PathLike,
        pattern: Optional[str],
        recursive: bool
    ) -> List[str]:
        """List files matching cloud prefix."""
        path_str = str(path)
        parsed = urlparse(path_str)

        if parsed.scheme == 's3':
            return self._list_s3_files(
                parsed.netloc,
                parsed.path.lstrip('/'),
                pattern,
                recursive
            )
        elif parsed.scheme == 'gs':
            return self._list_gcs_files(
                parsed.netloc,
                parsed.path.lstrip('/'),
                pattern,
                recursive
            )
        else:
            raise FilesystemError(
                f"Listing not supported for scheme: {parsed.scheme}"
            )

    def _list_s3_files(
        self,
        bucket: str,
        prefix: str,
        pattern: Optional[str],
        recursive: bool
    ) -> List[str]:
        """List files in S3 bucket."""
        s3 = boto3_client('s3')
        paginator = s3.get_paginator('list_objects_v2')

        results = []
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']

                # Filter by pattern if provided
                if pattern and not self._matches_pattern(key, pattern):
                    continue

                # Filter by recursive setting
                if not recursive and '/' in key[len(prefix):].lstrip('/'):
                    continue

                results.append(f"s3://{bucket}/{key}")

        return results

    def _list_gcs_files(
        self,
        bucket: str,
        prefix: str,
        pattern: Optional[str],
        recursive: bool
    ) -> List[str]:
        """List files in GCS bucket."""
        try:
            from google.cloud import storage
        except ImportError:
            raise FilesystemError(
                "google-cloud-storage not installed. "
                "Install with: pip install google-cloud-storage"
            )

        client = storage.Client()
        bucket_obj = client.bucket(bucket)
        blobs = bucket_obj.list_blobs(prefix=prefix)

        results = []
        for blob in blobs:
            # Filter by pattern if provided
            if pattern and not self._matches_pattern(blob.name, pattern):
                continue

            # Filter by recursive setting
            if not recursive and '/' in blob.name[len(prefix):].lstrip('/'):
                continue

            results.append(f"gs://{bucket}/{blob.name}")

        return results

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Simple glob pattern matching for filenames."""
        import fnmatch
        basename = os.path.basename(filename)
        return fnmatch.fnmatch(basename, pattern)

    def stream_download(
        self,
        path: PathLike,
        chunk_size: int = 8 * 1024 * 1024
    ) -> Iterator[bytes]:
        """
        Stream file content in chunks (memory-efficient for large files).

        Args:
            path: Path/URI to file
            chunk_size: Size of chunks to yield (default 8MB)

        Yields:
            Chunks of file content as bytes

        Example:
            >>> for chunk in fs.stream_download("s3://bucket/huge.fastq"):
            ...     process(chunk)
        """
        with self.open(path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk


# Global instance for convenience
_default_fs = None


def get_filesystem(
    transport_params: Optional[dict] = None,
    default_compression: Optional[str] = None,
    prefer_native_tools: bool = True
) -> FilesystemAbstraction:
    """
    Get or create the default filesystem instance.

    This allows for dependency injection in tests while providing
    a convenient default for production code.

    Args:
        transport_params: Optional smart_open transport parameters
        default_compression: Default compression ('infer_from_extension', 'gzip', 'zstd', etc.)
        prefer_native_tools: Use s5cmd when available (set False for pure Python)

    Returns:
        FilesystemAbstraction instance
    """
    global _default_fs
    if _default_fs is None or transport_params or default_compression is not None:
        _default_fs = FilesystemAbstraction(
            transport_params=transport_params,
            default_compression=default_compression,
            prefer_native_tools=prefer_native_tools
        )
    return _default_fs


def set_filesystem(fs: FilesystemAbstraction) -> None:
    """
    Override global filesystem instance (primarily for testing).

    Args:
        fs: FilesystemAbstraction instance to use globally
    """
    global _default_fs
    _default_fs = fs
