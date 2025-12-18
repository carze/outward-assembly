import csv
import itertools
import os
import re
from pathlib import Path
from typing import Iterable, List, NamedTuple

import yaml

PathLike = str | Path


class S3Record(NamedTuple):
    """Record for storing file path and derived filename.

    Note: Despite the name S3Record, this supports local, S3, and GCS paths.
    The name is kept for backward compatibility.
    """
    s3_path: str  # Can be local path, s3://, or gs:// path
    filename: str  # filename stem, no extension


S3Files = List[S3Record]


def process_s3_paths(paths: Iterable[str]) -> S3Files:
    """Process a list of file paths (local, s3://, or gs://) for assembly.

    Validates that all inputs are valid paths and returns S3Files records.
    Despite the function name, this supports local paths, S3 paths (s3://),
    and GCS paths (gs://). The name is kept for backward compatibility.

    Args:
        paths: Iterable of file paths (local, s3://, or gs://)

    Returns:
        S3Files: List of S3Record objects with path and derived filename

    Raises:
        ValueError: If paths are not unique, don't end with .fastq.zst/.fq.zst,
                   or filenames are too long (>245 chars)

    Note:
        Current implementation forces all paths to be under 245 characters.
        This could be relaxed if needed, but it ensures each filename
        unambiguously corresponds to a source without reference to an external key.

    To-do:
        Validate that each path points to an actual file
    """
    paths = sorted(paths)
    if len(set(paths)) < len(paths):
        raise ValueError("Input paths are not unique.")
    records = []
    for path in paths:
        # Validate file extension
        if not (path.lower().endswith(".fastq.zst") or path.lower().endswith(".fq.zst")):
            raise ValueError(f"Path {path} must end with .fastq.zst or .fq.zst")
        # to-do: validate path points to a file

        # Generate filename based on path type
        path_lower = path.lower()
        if path_lower.startswith("s3://"):
            # S3 path: drop s3:// prefix
            filename = "-".join(Path(path).parts[1:])
        elif path_lower.startswith("gs://"):
            # GCS path: drop gs:// prefix
            filename = "-".join(Path(path).parts[1:])
        else:
            # Local path: use full path components, skipping root "/" or "\"
            parts = [p for p in Path(path).parts if p not in ("/", "\\")]
            filename = "-".join(parts)

        # Drop the .fastq.zst or .fq.zst extension
        filename = filename.rsplit(".", maxsplit=2)[0]

        if len(filename) > 245:
            raise ValueError(f"Derived filename from path {path} is too long (>245 chars): {filename}")

        records.append(S3Record(path, filename))

    return records


def s3_files_with_prefix(bucket: str, prefix: str) -> list[str]:
    """
    List all S3 objects with given prefix (which may be a S3 "directory" with a trailing
    slash or include the beginning of "filenames").

    Args:
        bucket: S3 bucket name
        prefix: Key prefix to filter objects (no leading slash)

    Returns:
        List of full S3 URIs of matching objects
    """
    from .fs_abstraction import get_filesystem
    fs = get_filesystem()
    return fs.list_files(f"s3://{bucket}/{prefix}")


def _read_files_in_dir(dir: PathLike) -> List[str]:
    """List .fastq.zst files in a directory."""
    return [s for s in os.listdir(dir) if s.endswith(".fastq.zst")]


def dir_to_s3_paths(dir: PathLike, s3_prefix: str) -> List[str]:
    """Given a dir containing .fastq.zst read files and corresponding to a S3 prefix (which
    must end with a trailing slash), construct a list of S3 paths appropriate for passing
    to outward_assembly."""
    # To avoid stripping a slash from s3:// we do the basic path operations without Path
    if not s3_prefix.startswith("s3://"):
        raise ValueError(f"Invalid s3 prefix: {s3_prefix}")
    if not s3_prefix.endswith("/"):
        s3_prefix = s3_prefix + "/"
    return [s3_prefix + f for f in _read_files_in_dir(dir)]


def _count_lines(filename):
    from .fs_abstraction import get_filesystem
    fs = get_filesystem()
    with fs.open(filename, "rb") as f:
        return sum(1 for _ in f)


def load_config(yaml_path):
    from .fs_abstraction import get_filesystem
    fs = get_filesystem()
    with fs.open(yaml_path, "r") as file:
        config = yaml.safe_load(file)
    return config


def get_s3_paths_by_priority(input_csv: str, priority: int) -> list[str]:
    """
    Read input CSV file and return S3 paths for a specific priority level.
    Validates that priority numbers form a continuous sequence from 1 to N.

    Args:
        input_csv (str): Path to CSV file containing s3_path and priority columns
        priority (int): Priority level to filter by

    Returns:
        list[str]: List of S3 paths matching the specified priority

    Raises:
        ValueError: If priorities don't form a continuous sequence from 1 to N
                   or if any priority is less than 1
    """
    from .fs_abstraction import get_filesystem
    fs = get_filesystem()

    # First pass: collect all priorities
    priorities = set()
    with fs.open(input_csv, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            priority_val = int(row["priority"])
            if priority_val < 1:
                raise ValueError(
                    f"Invalid priority value {priority_val}. Priorities must be >= 1"
                )
            priorities.add(priority_val)

    # Verify sequence
    max_priority = max(priorities)
    expected_priorities = set(range(1, max_priority + 1))
    if priorities != expected_priorities:
        missing = expected_priorities - priorities
        raise ValueError(
            f"Priority sequence is not continuous 1 to {max_priority}. Missing numbers: {sorted(missing)}"
        )

    # Second pass: collect paths for requested priority
    with fs.open(input_csv, "r") as f:
        reader = csv.DictReader(f)
        filtered_paths = [
            str(row["s3_path"]) for row in reader if int(row["priority"]) == priority
        ]
    return filtered_paths


def concat_and_tag_fastq(input_files: list[PathLike], output_file: PathLike) -> None:
    """
    Concatenates a list of input FASTQ into a combined FASTQ, appending the input file
    basename (with _{1/2}.fastq trimmed) to header lines.

    Note: trimmed filenames are added to every fourth line;
    i.e. all records must be exactly four lines long.

    Args:
        input_files: A list of paths to the input files.
        output_file: The path to the output file to be created.

    Raises:
        RuntimeError: If any of the input files do not exist or an IO error occurs.
    """
    from .fs_abstraction import get_filesystem
    fs = get_filesystem()

    try:
        with fs.open(output_file, "w") as outfile:
            for filename in input_files:
                if os.path.getsize(filename) == 0:
                    continue
                base_filename = os.path.basename(filename)
                # Remove trailing _{1/2}.fastq
                sample_name = re.sub(r"_[12]\.fastq$", "", base_filename)

                with fs.open(filename, "r") as infile:
                    # Identify headers by line number, not leading @ since quality
                    # lines can also start with @
                    for identifier, sequence, plus, quality in itertools.batched(infile, 4):
                        outfile.write(f"{identifier.rstrip()} {sample_name}\n")
                        outfile.writelines([sequence, plus, quality])
    except (IOError, FileNotFoundError) as e:
        raise RuntimeError(f"Error processing files: {e}") from e
    except ValueError as e:
        raise ValueError("FASTQ file had number of lines not a multiple of 4") from e
