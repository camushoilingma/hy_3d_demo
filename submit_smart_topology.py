#!/usr/bin/env python3
"""
CLI tool for Tencent Cloud 3D Smart Topology API (Polygen 1.5)

Converts high-poly 3D models into clean, lower-poly models with proper topology.

Usage:
    python smart_topology.py https://example.com/model.glb
    python smart_topology.py https://example.com/model.glb --face-level high --polygon-type quadrilateral
    python smart_topology.py --help
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from secrets import Hy3DSecrets, load_secrets





def sign_request(
    secrets: Hy3DSecrets,
    action: str,
    payload: dict,
    timestamp: int
) -> Dict[str, str]:
    """
    Generate Tencent Cloud API v3 signature and return headers.
    """
    service = "hunyuan"
    host = secrets.endpoint
    algorithm = "TC3-HMAC-SHA256"
    date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    
    # Canonical request
    http_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    content_type = "application/json"
    payload_json = json.dumps(payload)
    signed_headers = "content-type;host;x-tc-action"
    
    canonical_headers = (
        f"content-type:{content_type}\n"
        f"host:{host}\n"
        f"x-tc-action:{action.lower()}\n"
    )
    
    hashed_payload = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    
    canonical_request = (
        f"{http_method}\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{hashed_payload}"
    )
    
    # String to sign
    credential_scope = f"{date}/{service}/tc3_request"
    hashed_canonical = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = (
        f"{algorithm}\n"
        f"{timestamp}\n"
        f"{credential_scope}\n"
        f"{hashed_canonical}"
    )
    
    # Signature
    def hmac_sha256(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
    
    secret_date = hmac_sha256(f"TC3{secrets.secret_key}".encode("utf-8"), date)
    secret_service = hmac_sha256(secret_date, service)
    secret_signing = hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    
    # Authorization header
    authorization = (
        f"{algorithm} "
        f"Credential={secrets.secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    
    return {
        "Authorization": authorization,
        "Content-Type": content_type,
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Version": "2023-09-01",
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Region": secrets.region,
    }


def submit_smart_topology_job(
    secrets: Hy3DSecrets,
    file_ref: str,
    file_type: str = "GLB",
    polygon_type: Optional[str] = None,
    face_level: Optional[str] = None,
    is_local: bool = False,
) -> dict:
    """
    Submit a 3D Smart Topology job to Tencent Cloud.
    
    Args:
        secrets: Authentication credentials
        file_url: URL to the 3D model file
        file_type: File type (GLB, OBJ, FBX, etc.)
        polygon_type: 'triangle' or 'quadrilateral'
        face_level: 'high', 'medium', or 'low'
    
    Returns:
        API response as dict
    """
    action = "Submit3DSmartTopologyJob"

    file3d: Dict[str, str] = {"Type": file_type.upper()}

    if is_local:
        with open(file_ref, "rb") as f:
            file_bytes = f.read()
        file3d["Content"] = base64.b64encode(file_bytes).decode("utf-8")
    else:
        file3d["Url"] = file_ref

    payload = {"File3D": file3d}
    
    if polygon_type:
        payload["PolygonType"] = polygon_type
    if face_level:
        payload["FaceLevel"] = face_level
    
    timestamp = int(datetime.now(timezone.utc).timestamp())
    headers = sign_request(secrets, action, payload, timestamp)
    
    url = f"https://{secrets.endpoint}"
    payload_bytes = json.dumps(payload).encode("utf-8")
    
    request = Request(url, data=payload_bytes, headers=headers, method="POST")
    
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"API request failed ({e.code}): {error_body}") from e
    except URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e


def detect_file_type(url: str) -> str:
    """Detect file type from URL extension."""
    url_lower = url.lower()
    if url_lower.endswith(".glb"):
        return "GLB"
    elif url_lower.endswith(".gltf"):
        return "GLTF"
    elif url_lower.endswith(".obj"):
        return "OBJ"
    elif url_lower.endswith(".fbx"):
        return "FBX"
    elif url_lower.endswith(".stl"):
        return "STL"
    else:
        return "GLB"  # Default


def main():
    parser = argparse.ArgumentParser(
        description="Submit a 3D model to Tencent Cloud Smart Topology API (Polygen 1.5)",
        epilog="""
Examples:
  # Remote URL
  %(prog)s https://example.com/model.glb
  %(prog)s https://example.com/model.glb --face-level high
  %(prog)s https://example.com/model.obj --file-type OBJ --polygon-type quadrilateral

  # Local file
  %(prog)s ./models/model.glb --local
  %(prog)s ./models/model.obj --local --file-type OBJ --face-level medium
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "file_ref",
        help="3D model location: either a public URL or a local file path (use --local for local files)",
    )
    
    parser.add_argument(
        "-t", "--file-type",
        choices=["GLB", "GLTF", "OBJ", "FBX", "STL"],
        default=None,
        help="3D file type (auto-detected from URL if not specified)",
    )
    
    parser.add_argument(
        "-p", "--polygon-type",
        choices=["triangle", "quadrilateral"],
        default=None,
        help="Output polygon type: triangle (default) or quadrilateral (mixed tri/quad)",
    )
    
    parser.add_argument(
        "-f", "--face-level",
        choices=["high", "medium", "low"],
        default=None,
        help="Polygon reduction level: high, medium, or low",
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )
    
    parser.add_argument(
        "--secrets",
        type=str,
        default=None,
        help="Path to secrets JSON file (overrides default locations)",
    )

    parser.add_argument(
        "--local",
        action="store_true",
        help="Treat file_ref as a local file path and upload content directly instead of using a URL",
    )
    
    args = parser.parse_args()
    
    # Override secrets path if provided
    if args.secrets:
        os.environ["HY3D_SECRETS_PATH"] = args.secrets
    
    try:
        secrets = load_secrets()
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Detect file type if not specified
    file_type = args.file_type or detect_file_type(args.file_ref)

    # If --local not set but path exists locally, assume local for convenience
    is_local = args.local or os.path.exists(args.file_ref)
    
    if not args.json:
        print(f"Submitting job...")
        print(f"  Source: {args.file_ref}")
        print(f"  Mode: {'local file' if is_local else 'remote URL'}")
        print(f"  File type: {file_type}")
        if args.polygon_type:
            print(f"  Polygon type: {args.polygon_type}")
        if args.face_level:
            print(f"  Face level: {args.face_level}")
        print()
    
    try:
        response = submit_smart_topology_job(
            secrets=secrets,
            file_ref=args.file_ref,
            file_type=file_type,
            polygon_type=args.polygon_type,
            face_level=args.face_level,
            is_local=is_local,
        )
        
        if args.json:
            print(json.dumps(response, indent=2))
        else:
            if "Response" in response:
                resp = response["Response"]
                if "JobId" in resp:
                    print(f"Job submitted successfully!")
                    print(f"  Job ID: {resp['JobId']}")
                    print(f"  Request ID: {resp.get('RequestId', 'N/A')}")
                elif "Error" in resp:
                    error = resp["Error"]
                    print(f"API Error: {error.get('Code', 'Unknown')}", file=sys.stderr)
                    print(f"  Message: {error.get('Message', 'No message')}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(json.dumps(response, indent=2))
                
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()