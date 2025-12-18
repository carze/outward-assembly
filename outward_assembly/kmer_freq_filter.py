import logging
import math
import os
import shutil
import subprocess
import warnings
from functools import partial
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Optional

from .fs_abstraction import FilesystemAbstraction, get_filesystem
from .io_helpers import PathLike, S3Files

# kmc and kmc_tools are expected to be available on PATH via the oa-tools conda environment


def _count_kmers_single_file(
    rec,
    kmers_dir: Path,
    k: int,
    min_kmer_freq: int,
    fs: FilesystemAbstraction,
    memory_GB: int = 5,
    threads: int = 4,
) -> None:
    """Count k-mers from cloud/local file.

    Note: KMC requires a file path (doesn't support stdin),
    so we stream to a temp file only for KMC's input.
    Streaming download means we don't need full disk space.

    Args:
        rec: S3Record with file info
        kmers_dir: Directory for kmer counting output
        k: Kmer size
        min_kmer_freq: Minimum frequency threshold
        fs: Filesystem abstraction instance
        memory_GB: Memory limit for KMC in GB
        threads: Number of threads per KMC process
    """
    tmp_dir = Path(kmers_dir) / f"tmp_{rec.filename}"
    tmp_fastq = tmp_dir / "reads.fastq"
    kmc_tmp_dir = tmp_dir / "kmc_tmp"
    kmc_out_prefix = tmp_dir / "kmers"
    high_freq_out = Path(kmers_dir) / f"hfq_{rec.filename}.txt"

    tmp_dir.mkdir(parents=True, exist_ok=True)
    kmc_tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Stream from S3/GCS/local → decompress → temp file
        with fs.open(rec.s3_path, "rb", compression="infer") as src:
            with open(tmp_fastq, "wb") as dst:
                for chunk in iter(lambda: src.read(8 * 1024 * 1024), b""):
                    dst.write(chunk)

        # Run KMC on temp file
        max_count = 2 ** math.ceil(math.log2(2 * min_kmer_freq))
        subprocess.run(
            [
                "kmc",
                f"-k{k}",
                f"-cs{max_count}",
                f"-ci{min_kmer_freq}",
                f"-t{threads}",
                f"-m{memory_GB}",
                str(tmp_fastq),
                str(kmc_out_prefix),
                str(kmc_tmp_dir),
            ],
            check=True,
            capture_output=True,
        )

        # Dump KMC results
        subprocess.run(
            [
                "kmc_tools",
                "transform",
                str(kmc_out_prefix),
                "dump",
                str(high_freq_out),
            ],
            check=True,
            capture_output=True,
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _high_freq_kmers_split_files(
    s3_records: S3Files,
    workdir: PathLike,
    *,
    num_parallel: Optional[int] = None,
    min_kmer_freq: int = 2000,
    k: int = 31,
    allow_tmp_workdir: bool = True,
) -> Path:
    """Get list of kmers that appear at least min_kmer_freq times in any single input file.

    Uses KMC3 for kmer counting and operates in parallel while managing disk space usage.
    All work is done in workdir/kmers/. Returns the path to a fasta of high frequency kmers.

    Args:
        s3_records: Files to count kmers in
        workdir: Working directory for temporary files
        num_parallel: Number of parallel processes (defaults to max(1, cpu_count()//4))
        min_kmer_freq: Minimum frequency threshold for high-frequency kmers
        k: Kmer size
        allow_tmp_workdir: allow a /tmp backed working directory (with warning)

    Returns:
        Path to fasta file containing high-frequency kmers

    Raises:
        ValueError: If workdir starts with /tmp or doesn't exist
    """
    workdir = Path(workdir)

    # Input validation
    if not workdir.exists():
        raise ValueError(f"Working directory {workdir} does not exist")
    if str(workdir).startswith("/tmp"):
        if not allow_tmp_workdir:
            raise ValueError(
                f"Working directory {workdir} starts with /tmp which may be memory-backed"
            )
        else:
            warnings.warn(
                "workdir is in /tmp which is typically memory-backed. "
                "Large read/kmer files here could consume system memory and potentially cause crashes. "
                "If this is not intentional, consider using a disk-backed location instead."
            )

    # Set default num_parallel if not provided
    if num_parallel is None:
        num_parallel = max(1, cpu_count() // 4)

    # Create kmers subdir - error if it exists as it may contain stale data
    kmers_dir = workdir / "kmers"
    kmers_dir.mkdir()

    # Get filesystem abstraction
    fs = get_filesystem()

    # Run kmer counting in parallel using multiprocessing.Pool
    logging.debug(f"Running KMC commands in parallel with {num_parallel} processes")
    count_func = partial(
        _count_kmers_single_file,
        kmers_dir=kmers_dir,
        k=k,
        min_kmer_freq=min_kmer_freq,
        fs=fs,
    )

    with Pool(processes=num_parallel) as pool:
        pool.map(count_func, s3_records)

    # Merge results
    result_path = kmers_dir / "high_freq_kmers.fasta"
    high_freq_files = [
        f for f in os.listdir(kmers_dir) if f.startswith("hfq_") and f.endswith(".txt")
    ]

    if high_freq_files:
        # Process high frequency kmers
        kmer_counts = {}
        for hff in high_freq_files:
            with open(kmers_dir / hff) as f:
                for line in f:
                    # Each line is <kmer> <whitespace> <count>
                    kmer, count = line.strip().split()
                    # Store max count seen for this kmer across all input files
                    kmer_counts[kmer] = max(kmer_counts.get(kmer, 0), int(count))

        # Write merged results
        with open(result_path, "w") as f:
            for kmer, count in kmer_counts.items():
                f.write(f">kmer_max_{count}_obs\n{kmer}\n")

        # Clean up individual kmer files
        for f in high_freq_files:
            (kmers_dir / f).unlink()
    else:
        logging.warning("No high-frequency kmers found in any input file")
        result_path.touch()

    return result_path


def _filter_single_file_bbduk(
    rec,
    high_freq_kmers_path: Path,
    out_dir: Path,
    k: int,
    fs: FilesystemAbstraction,
) -> None:
    """Filter single file through BBDuk (stream cloud/local → BBDuk → compressed output).

    Args:
        rec: S3Record with file info
        high_freq_kmers_path: Path to high-frequency kmers fasta
        out_dir: Output directory for filtered reads
        k: Kmer size
        fs: Filesystem abstraction instance
    """
    out_path = out_dir / Path(rec.s3_path).parts[-1]

    # Build BBDuk command (reads from stdin, writes to stdout)
    bbduk_cmd = [
        "bbduk.sh",
        "in=stdin.fq",
        "out=stdout.fq",
        f"ref={high_freq_kmers_path}",
        f"k={k}",
        "rcomp=t",
        "minkmerhits=1",
        "mm=f",
        "interleaved=t",
        "threads=3",
        "-Xmx2g",
    ]

    # Stream: cloud/local → decompress → BBDuk → compress → output
    # Opens input with automatic decompression
    with fs.open(rec.s3_path, "rb", compression="infer") as src:
        # Start BBDuk process
        bbduk_proc = subprocess.Popen(
            bbduk_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Start zstd compression process
        zstd_proc = subprocess.Popen(
            ["zstd", "-q", "-T3", "-o", str(out_path)],
            stdin=bbduk_proc.stdout,
            stderr=subprocess.PIPE,
        )

        # Stream data through the pipeline
        try:
            for chunk in iter(lambda: src.read(8 * 1024 * 1024), b""):
                bbduk_proc.stdin.write(chunk)
            bbduk_proc.stdin.close()

            # Wait for completion
            bbduk_proc.wait()
            zstd_proc.wait()

            if bbduk_proc.returncode != 0:
                stderr = bbduk_proc.stderr.read().decode()
                raise subprocess.CalledProcessError(
                    bbduk_proc.returncode, bbduk_cmd, stderr=stderr
                )

            if zstd_proc.returncode != 0:
                stderr = zstd_proc.stderr.read().decode()
                raise subprocess.CalledProcessError(
                    zstd_proc.returncode, ["zstd"], stderr=stderr
                )

        finally:
            bbduk_proc.stdout.close()
            bbduk_proc.stderr.close()
            zstd_proc.stderr.close()


def frequency_filter_reads(
    s3_records: S3Files,
    workdir: PathLike,
    out_dir: PathLike,
    *,
    num_parallel: Optional[int] = None,
    min_kmer_freq: int = 2000,
    k: int = 31,
) -> None:
    """Filter out reads containing high-frequency kmers from split interleaved reads.

    Takes zstd-compressed fastq files named reads_il_divXXXX.fastq.zst from reads_dir,
    identifies kmers appearing >= min_kmer_freq times in any single file, and outputs
    filtered reads (excluding those with high-freq kmers) to out_dir with same naming scheme.

    Args:
        s3_records: Files to count kmers in
        workdir: Working directory for temporary files
        out_dir: Output directory (presently may not be S3)
        num_parallel: Number of parallel processes (defaults to max(1, cpu_count()//4))
            Note that disk space required is on the order of <input file size> * num_parallel
        min_kmer_freq: Minimum frequency threshold for high-frequency kmers
        k: Kmer size

    To-do:
        Allow outputting to S3
    """
    workdir = Path(workdir)
    out_dir = Path(out_dir)
    if out_dir.exists():
        logging.warning(
            f"Output directory {out_dir} already exists - skipping frequency filtering"
        )
        return
    out_dir.mkdir(parents=True, exist_ok=False)

    # Set default num_parallel if not provided
    if num_parallel is None:
        num_parallel = max(1, cpu_count() // 4)

    # Get high-frequency kmers
    high_freq_kmers_path = _high_freq_kmers_split_files(
        s3_records, workdir, num_parallel=num_parallel, min_kmer_freq=min_kmer_freq, k=k
    )

    # Get filesystem abstraction
    fs = get_filesystem()

    # Run BBDuk filtering in parallel using multiprocessing.Pool
    logging.debug(f"Running BBDuk filtering in parallel with {num_parallel} processes")
    filter_func = partial(
        _filter_single_file_bbduk,
        high_freq_kmers_path=high_freq_kmers_path,
        out_dir=out_dir,
        k=k,
        fs=fs,
    )

    with Pool(processes=num_parallel) as pool:
        pool.map(filter_func, s3_records)

    logging.debug("BBDuk filtering complete")
