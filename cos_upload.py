# -*- coding: utf-8 -*-
"""
Upload local files to Tencent COS with public-read ACL.

Used by scripts that need a public URL for a local file (e.g. convert_3d_format.py).
Configure cos_bucket and optional cos_region in your secrets file.
"""

import os
import re

from secrets import Hy3DSecrets, load_secrets


def upload_local_file_to_cos(
    local_path: str,
    secrets: Hy3DSecrets,
    subfolder: str = "convert",
) -> str:
    """Upload a local file to Tencent COS with public-read ACL; return the public URL."""
    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError:
        raise RuntimeError(
            "COS upload requires cos-python-sdk-v5. Install with: pip install cos-python-sdk-v5"
        ) from None

    bucket = secrets.cos_bucket
    region = secrets.cos_region or secrets.region
    filename = os.path.basename(local_path)
    key = f"hy3d/{subfolder}/{filename}"

    config = CosConfig(
        Region=region,
        SecretId=secrets.secret_id,
        SecretKey=secrets.secret_key,
    )
    client = CosS3Client(config)

    with open(local_path, "rb") as f:
        body = f.read()

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ACL="public-read",
    )

    return f"https://{bucket}.cos.{region}.myqcloud.com/{key}"


def resolve_input_to_url(input_ref: str, subfolder: str = "convert") -> str:
    """
    If input is a local file path, upload to COS and return URL; otherwise return as-is.
    Requires cos_bucket (and optional cos_region) in secrets for local files.
    subfolder: COS key prefix under hy3d/ (e.g. "convert", "part").
    """
    s = (input_ref or "").strip()
    if not s:
        return s
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if os.path.isfile(s):
        secrets = load_secrets()
        if not secrets.cos_bucket:
            raise SystemExit(
                "Local file given but COS upload not configured. "
                "Add cos_bucket (and optional cos_region) to your secrets file, e.g.:\n"
                '  "cos_bucket": "your-bucket-appid",\n'
                '  "cos_region": "ap-singapore"'
            )
        print("📤 Uploading local file to Tencent COS (public-read)...")
        url = upload_local_file_to_cos(s, secrets, subfolder=subfolder)
        print(f"   {url}")
        return url
    return s
