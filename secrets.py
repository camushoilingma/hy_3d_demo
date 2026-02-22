import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Hy3DSecrets:
    secret_id: str
    secret_key: str
    region: str = "ap-singapore"
    endpoint: str = "hunyuan.intl.tencentcloudapi.com"
    cos_bucket: Optional[str] = None  # e.g. "mybucket-1234567890" for local-file upload to COS
    cos_region: Optional[str] = None  # COS region, defaults to region if not set


def _default_secrets_paths() -> list[Path]:
    home = Path.home()
    return [
        Path(os.environ.get("HY3D_SECRETS_PATH", "")).expanduser()
        if os.environ.get("HY3D_SECRETS_PATH")
        else None,
        Path.cwd() / "secrets.json",
        home / ".hy-3d-secrets.json",
    ]


def load_secrets() -> Hy3DSecrets:
    """
    Load secrets from a local JSON file.

    Supported locations (first found wins):
      - $HY3D_SECRETS_PATH
      - ./secrets.json
      - ~/.hy-3d-secrets.json

    Expected JSON format:
      {
        "secret_id": "...",
        "secret_key": "...",
        "region": "ap-singapore",
        "endpoint": "hunyuan.intl.tencentcloudapi.com"
      }
    """
    candidates: list[Path] = [p for p in _default_secrets_paths() if p is not None]
    for p in candidates:
        try:
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                secret_id = (data.get("secret_id") or "").strip()
                secret_key = (data.get("secret_key") or "").strip()
                region = (data.get("region") or "ap-singapore").strip()
                endpoint = (data.get("endpoint") or "hunyuan.intl.tencentcloudapi.com").strip()

                if not secret_id or not secret_key:
                    raise ValueError(f"Missing secret_id/secret_key in {p}")
                cos_bucket = (data.get("cos_bucket") or "").strip() or None
                cos_region = (data.get("cos_region") or "").strip() or None
                return Hy3DSecrets(
                    secret_id=secret_id,
                    secret_key=secret_key,
                    region=region,
                    endpoint=endpoint,
                    cos_bucket=cos_bucket,
                    cos_region=cos_region,
                )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse secrets JSON in {p}: {e}") from e

    searched = "\n".join(f"  - {str(p)}" for p in candidates)
    raise RuntimeError(
        "No secrets file found. Create one of the following files:\n"
        f"{searched}\n\n"
        "Example secrets.json:\n"
        '{\n'
        '  "secret_id": "YOUR_SECRET_ID",\n'
        '  "secret_key": "YOUR_SECRET_KEY",\n'
        '  "region": "ap-singapore",\n'
        '  "endpoint": "hunyuan.intl.tencentcloudapi.com",\n'
        '  "cos_bucket": "your-bucket-appid",\n'
        '  "cos_region": "ap-singapore"\n'
        '}\n'
    )

