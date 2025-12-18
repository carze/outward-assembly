# Installation

To run this software, you need to follow the instructions in [basic requirements](#basic-requirements). This will allow you to run the outward assembly software in the *local* profile (we expect the *local* profile will work for most use-cases).

Briefly, the outward assembly software has two profiles (read our [usage docs](./usage.md#profiles) to learn more about when to use either profile):
* *Local*: Run outward assembly using your local machine.
* *Batch*: Run outward assembly using AWS Batch (via Nextflow) for distributed read searching; other algorithm steps run locally.

If you want to use the *batch* profile, you'll also need to follow the [instructions below to install the required software](#optional-batch-profile).

## Basic requirements

### Python dependencies

Python dependencies are managed with [uv](https://docs.astral.sh/uv/). From the base repository directory:

```bash
# Install and sync Python dependencies with uv
uv sync --extra dev

# Run Python commands with uv
uv run your_script.py
uv run pytest

# Or activate the virtual environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate     # Windows
```

### Bioinformatics tools

Bioinformatics tools are managed via conda using the **tools-only** environment (`oa_tools_env.yml`) that contains just the bioinformatics tools (BBMap/BBDuk, MEGAHIT, fastp, KMC) without Python dependencies:

```bash
mamba env create -n oa-tools -f oa_tools_env.yml --channel-priority flexible
```

**Before running the pipeline, activate the tools environment:**

```bash
mamba activate oa-tools
```

Then run Python commands via uv (while the tools environment is activated):
```bash
uv run your_script.py
```

**Note:** You need both uv (for Python packages) and mamba/conda (for bioinformatics tools like MEGAHIT, BBMap, etc.).

## Cloud Storage Setup (Optional)

The filesystem abstraction supports AWS S3, Google Cloud Storage (GCS), and local filesystems. If you plan to use cloud storage, configure credentials as follows:

### AWS S3

**Option 1: AWS CLI configure**
```bash
aws configure
```

**Option 2: Environment variables**
```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1
```

### Google Cloud Storage

For optimal performance with GCS, create HMAC keys for s5cmd compatibility:

**Step 1: Create HMAC keys**
```bash
gcloud storage hmac create
```

**Step 2: Add to ~/.aws/credentials**
```bash
cat >> ~/.aws/credentials << EOF
[gcs]
aws_access_key_id = GOOG1EXAMPLE...
aws_secret_access_key = abcd1234...
EOF
```

**Step 3: Use with s5cmd**
```bash
AWS_PROFILE=gcs s5cmd ls gs://my-bucket/
```

### Verify Cloud Setup

```bash
# Check if s5cmd is available (optional but recommended for performance)
s5cmd version

# Verify filesystem abstraction
python -c "from outward_assembly.fs_abstraction import FilesystemAbstraction; fs = FilesystemAbstraction(); print(f's5cmd available: {fs._has_s5cmd}')"

# Run unit tests
pixi run --environment dev pytest tests/unit_tests/ -v

# Or with uv (if not using pixi)
uv run pytest tests/unit_tests/ -v
```

## (Optional) Batch profile

Using the batch profile requires doing two steps:

1. Install Nextflow and the AWS CLI
2. Configuring AWS Batch

### Nextflow installation

#### 1. Install Nextflow 
To install Nextflow, you can follow the instructions [here](https://www.nextflow.io/docs/latest/getstarted.html)

#### 2. Install AWS CLI
To install the AWS CLI, you can follow the instructions [here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

#### 3. Install Docker
To install Docker, you can follow the instructions [here](https://docs.docker.com/engine/install/).

#### 4. Configure AWS & Docker

[Configure AWS access](https://www.nextflow.io/docs/latest/aws.html) by creating a file at `~/.aws/config` **or** `~/.aws/credentials`, specifying your access key ID and secret access key, e.g.

`~/.aws/config`:
```
[default]
region = us-east-1
output = table
tcp_keepalive = true
aws_access_key_id = <ACCESS_KEY_ID>
aws_secret_access_key = <SECRET_ACCESS_KEY>
```

`~/.aws/credentials`:
```
[default]
aws_access_key_id = <ACCESS_KEY_ID>
aws_secret_access_key = <SECRET_ACCESS_KEY>
```

> [!TIP]
> If you encounter `AccessDenied` errors after doing this, you may also need to export these keys as environment variables before running Nextflow:
>
> ```
> eval "$(aws configure export-credentials --format env)"
> ```

Next, you need to make sure your user is configured to use Docker. To do this, create the `docker` user group and add your current user to it:

```
sudo groupadd docker
sudo usermod -aG docker $USER
newgrp docker
docker run hello-world
```

### Setup AWS Batch

To setup AWS Batch, we recommend that you follow the latest [^1] instructions in the [MGS Workflow](https://github.com/naobservatory/mgs-workflow/blob/master/docs/batch.md) [^1], _except_ substitute the following storage configuration in your EC2 launch template:
* Volume type: gp3
* Capacity: 5GB plus whatever space is required for the snapshot used by your launch template
* Throughput: 125MB/s (free tier)
* IOPS: 3000 (free tier)

Though each Batch job runs for just a few seconds, running outward assembly at scale may create hundreds of thousands of Batch jobs. Thus, to control costs, it's important not to provision unnecessarily large EBS volumes. 

[^1]: In the situation that the instructions change, [this link](https://github.com/naobservatory/mgs-workflow/blob/9fe05a5ca9ce7cbc886927788f22c71ff9f26443/docs/batch.md) should be used as reference for the version of the docs used at the time.

### Seqera Tower Credentials
Using the Batch profile requires a Seqera Tower [access token](https://docs.seqera.io/platform-cloud/api/overview). See your tokens or create a new one in the Seqera [console](https://cloud.seqera.io/tokens).

 
