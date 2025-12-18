import pytest

from outward_assembly.io_helpers import (
    _count_lines,
    concat_and_tag_fastq,
    process_s3_paths,
)


@pytest.mark.fast
@pytest.mark.unit
def test_process_s3_paths():
    """Processing s3 paths should produce unique valid filenames."""
    s3_paths = [
        # same suffix, we should disambiguate
        "s3://a/b/c.fastq.zst",
        "s3://a/x/c.fastq.zst",
    ]
    records = process_s3_paths(s3_paths)
    assert len(set([rec.filename for rec in records])) == len(s3_paths)
    assert sorted(s3_paths) == sorted([rec.s3_path for rec in records])
    for rec in records:
        # filename should be a valid file name; could check more conditions
        assert "/" not in rec.filename
        assert len(rec.filename) <= 245  # need extra space for other prefixes/suffixes


@pytest.mark.fast
@pytest.mark.unit
def test_process_s3_paths_invalid():
    with pytest.raises(ValueError):
        process_s3_paths(["s3://not/valid/extension.jpg"])


@pytest.mark.fast
@pytest.mark.unit
def test_process_gcs_paths():
    """Processing GCS paths should work like S3 paths."""
    gcs_paths = [
        "gs://bucket/data/reads_1.fastq.zst",
        "gs://bucket/data/reads_2.fq.zst",
    ]
    records = process_s3_paths(gcs_paths)
    assert len(records) == 2
    assert records[0].s3_path == "gs://bucket/data/reads_1.fastq.zst"
    assert records[0].filename == "bucket-data-reads_1"
    assert records[1].filename == "bucket-data-reads_2"
    # Ensure no slashes in derived filenames
    for rec in records:
        assert "/" not in rec.filename


@pytest.mark.fast
@pytest.mark.unit
def test_process_local_paths():
    """Processing local paths should strip leading / or \\ from filenames."""
    local_paths = [
        "/data/reads/sample_1.fastq.zst",
        "data/reads/sample_2.fq.zst",
    ]
    records = process_s3_paths(local_paths)
    assert len(records) == 2
    assert records[0].s3_path == "/data/reads/sample_1.fastq.zst"
    assert records[0].filename == "data-reads-sample_1"
    assert records[1].s3_path == "data/reads/sample_2.fq.zst"
    assert records[1].filename == "data-reads-sample_2"
    # Ensure no slashes in derived filenames
    for rec in records:
        assert "/" not in rec.filename


@pytest.mark.fast
@pytest.mark.unit
def test_process_mixed_paths():
    """Processing mixed S3, GCS, and local paths should all work together."""
    mixed_paths = [
        "s3://bucket/s3_data.fastq.zst",
        "gs://bucket/gcs_data.fastq.zst",
        "/local/data.fastq.zst",
    ]
    records = process_s3_paths(mixed_paths)
    assert len(records) == 3
    # Paths are sorted, so order will be: /local, gs://, s3://
    assert records[0].s3_path == "/local/data.fastq.zst"
    assert records[0].filename == "local-data"
    assert records[1].s3_path == "gs://bucket/gcs_data.fastq.zst"
    assert records[1].filename == "bucket-gcs_data"
    assert records[2].s3_path == "s3://bucket/s3_data.fastq.zst"
    assert records[2].filename == "bucket-s3_data"
    # Ensure all original paths are preserved in sorted order
    assert [r.s3_path for r in records] == sorted(mixed_paths)


@pytest.mark.fast
@pytest.mark.unit
def test_count_lines(temp_empty_file):
    assert _count_lines(temp_empty_file) == 0
    with open(temp_empty_file, "a") as f:
        f.write("hi")  # no newline
    assert _count_lines(temp_empty_file) == 1
    with open(temp_empty_file, "a") as f:
        f.write("\n")  # finish the same line
    assert _count_lines(temp_empty_file) == 1


@pytest.mark.fast
@pytest.mark.unit
def test_concat_and_tag_fastq_forward_reads(temp_workdir):
    sample1_fwd = temp_workdir / "sample1_1.fastq"
    sample2_fwd = temp_workdir / "sample2_1.fastq"
    output_fwd = temp_workdir / "combined_1.fastq"

    # Create test forward read files
    with open(sample1_fwd, "w") as f:
        f.write("@read1\nACGT\n+\nIIII\n@read2\nTGCA\n+\nIIII\n")

    with open(sample2_fwd, "w") as f:
        f.write("@read3\nGGGG\n+\nIIII\n")

    concat_and_tag_fastq([sample1_fwd, sample2_fwd], output_fwd)

    with open(output_fwd, "r") as f:
        content = f.read()

    expected = "@read1 sample1\nACGT\n+\nIIII\n@read2 sample1\nTGCA\n+\nIIII\n@read3 sample2\nGGGG\n+\nIIII\n"
    assert content == expected


@pytest.mark.fast
@pytest.mark.unit
def test_concat_and_tag_fastq_empty_file(temp_workdir):
    empty_fwd = temp_workdir / "empty_1.fastq"
    sample_fwd = temp_workdir / "sample_1.fastq"
    output_fwd = temp_workdir / "combined_1.fastq"

    # Create empty and non-empty files
    with open(empty_fwd, "w") as f:
        pass  # Empty file

    with open(sample_fwd, "w") as f:
        f.write("@read1\nACGT\n+\nIIII\n")

    concat_and_tag_fastq([empty_fwd, sample_fwd], output_fwd)

    with open(output_fwd, "r") as f:
        content = f.read()

    expected = "@read1 sample\nACGT\n+\nIIII\n"
    assert content == expected


@pytest.mark.fast
@pytest.mark.unit
def test_concat_and_tag_fastq_file_not_found(temp_workdir):
    nonexistent_fwd = temp_workdir / "nonexistent_1.fastq"
    output_fwd = temp_workdir / "combined_1.fastq"

    with pytest.raises(RuntimeError, match="Error processing files"):
        concat_and_tag_fastq([nonexistent_fwd], output_fwd)


@pytest.mark.fast
@pytest.mark.unit
def test_concat_and_tag_fastq_bad_line_count(temp_workdir):
    # 3 line input file can't be a legal fastq
    infile = temp_workdir / "sample_1.fastq"
    outfile = temp_workdir / "out.fastq"
    with open(infile, "w") as f:
        f.write("Chocolate\nVanilla\nStrawberry\n")
    with pytest.raises(ValueError):
        concat_and_tag_fastq([infile], outfile)
