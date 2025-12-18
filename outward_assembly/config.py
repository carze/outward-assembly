"""
Configuration management for outward assembly cloud operations.

Handles cloud credentials, filesystem settings, and runtime parameters.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class CloudConfig:
    """
    Cloud provider configuration.

    Credentials are loaded from environment variables or standard
    credential files (~/.aws/credentials, ~/.config/gcloud/, etc.)
    following each cloud provider's standard credential chain.

    For s5cmd with GCS, use HMAC keys in ~/.aws/credentials:
        [gcs]
        aws_access_key_id = GOOG1EXAMPLE...
        aws_secret_access_key = abcd1234...
    """

    # AWS Configuration
    aws_profile: Optional[str] = field(
        default_factory=lambda: os.getenv('AWS_PROFILE')
    )
    aws_region: Optional[str] = field(
        default_factory=lambda: os.getenv('AWS_REGION', 'us-east-1')
    )

    # GCS Configuration (for smart_open)
    gcs_project: Optional[str] = field(
        default_factory=lambda: os.getenv('GCP_PROJECT')
    )

    # Azure Configuration
    azure_account_name: Optional[str] = field(
        default_factory=lambda: os.getenv('AZURE_STORAGE_ACCOUNT')
    )

    # Filesystem behavior
    default_compression: Optional[str] = 'infer_from_extension'  # Auto-detect compression
    stream_buffer_size: int = 8 * 1024 * 1024  # 8MB default chunk size
    prefer_native_tools: bool = True  # Use s5cmd when available

    def get_transport_params(self) -> dict:
        """
        Get smart_open transport parameters based on configuration.

        Returns:
            Dictionary of transport parameters for smart_open
        """
        params = {}

        if self.aws_profile:
            import boto3
            session = boto3.Session(
                profile_name=self.aws_profile,
                region_name=self.aws_region
            )
            params['client'] = session.client('s3')

        return params
