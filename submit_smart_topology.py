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
import time
import urllib.request
from datetime import datetime, timezone
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    from tencentcloud.common.common_client import CommonClient
    from tencentcloud.common import credential
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    from tencentcloud.common.profile.client_profile import ClientProfile
    from tencentcloud.common.profile.http_profile import HttpProfile
except ImportError:
    print("❌ Tencent Cloud SDK not installed!")
    print("   Run: pip install tencentcloud-sdk-python")
    sys.exit(1)

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


def get_client():
    """Create and return API client using SDK."""
    s = load_secrets()
    cred = credential.Credential(s.secret_id, s.secret_key)
    
    http_profile = HttpProfile()
    http_profile.endpoint = s.endpoint
    
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    
    return CommonClient("hunyuan", "2023-09-01", cred, s.region, profile=client_profile)


def describe_smart_topology_job(job_id: str) -> dict:
    """
    Query a 3D Smart Topology job status using Describe3DSmartTopologyJob.
    
    Args:
        job_id: The job ID returned by Submit3DSmartTopologyJob
    
    Returns:
        API response as dict
    """
    client = get_client()
    params = {"JobId": job_id}
    return client.call_json("Describe3DSmartTopologyJob", params)


def wait_for_completion(job_id: str, poll_seconds: int = 10) -> Optional[dict]:
    """
    Poll for job completion with progress display.
    
    Args:
        job_id: The job ID to query
        poll_seconds: Polling interval in seconds
    
    Returns:
        Job response dict if successful, None if failed
    """
    print("\n⏱️  Waiting for topology optimization (this may take several minutes)...")
    print("-" * 50)
    
    start_time = time.time()
    poll_count = 0
    
    while True:
        poll_count += 1
        result = describe_smart_topology_job(job_id)
        response = result.get("Response", {})
        status = response.get("Status")
        
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        
        # Progress display
        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"][poll_count % 10]
        print(f"\r   {spinner} Status: {status:<6} | Elapsed: {mins:02d}:{secs:02d}", end="", flush=True)
        
        if status == "DONE":
            print(f"\n\n🎉 SUCCESS! Topology optimization completed in {mins}m {secs}s")
            return response
            
        elif status == "FAIL":
            error_code = response.get("ErrorCode", "Unknown")
            error_msg = response.get("ErrorMessage", "Unknown error")
            print(f"\n\n❌ Optimization failed!")
            print(f"   Error: {error_code} - {error_msg}")
            return None
            
        else:  # WAIT or RUN
            time.sleep(poll_seconds)


def download_file(url: str, output_path: str) -> bool:
    """Download a file from URL."""
    try:
        print(f"   Downloading {os.path.basename(output_path)}...", end=" ", flush=True)
        urllib.request.urlretrieve(url, output_path)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✅ ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def download_results(file_list: list, output_dir: str) -> list[str]:
    """
    Download all result files from the job response.
    
    Args:
        file_list: List of file info dicts or URLs from ResultFile3Ds
        output_dir: Directory to save files
    
    Returns:
        List of downloaded file paths
    """
    print("\n📥 Downloading optimized 3D model files...")
    print("-" * 50)
    
    os.makedirs(output_dir, exist_ok=True)
    downloaded_files = []
    
    for i, file_info in enumerate(file_list):
        # Handle different response formats
        if isinstance(file_info, dict):
            url = file_info.get("Url") or file_info.get("FileUrl") or file_info.get("url", "")
            file_type = file_info.get("Type", file_info.get("type", ""))
        else:
            url = str(file_info)
            file_type = ""
        
        if not url:
            print(f"   ⚠️  Skipping empty URL for file #{i+1}")
            continue
        
        # Extract filename from URL or generate one
        url_path = url.split("?")[0]  # Remove query params
        filename = os.path.basename(url_path)
        
        if not filename or filename == "":
            ext = ".obj" if "obj" in url.lower() else ".glb"
            filename = f"optimized_model_{i+1}{ext}"
        
        output_path = os.path.join(output_dir, filename)
        
        if download_file(url, output_path):
            downloaded_files.append(output_path)
    
    return downloaded_files


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

  # Wait for completion and download results
  %(prog)s ./model.glb --wait --download --output ./optimized_models
  %(prog)s https://example.com/model.glb --wait --poll 5 --download
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
    
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until job is DONE/FAIL (polling for completion)",
    )
    
    parser.add_argument(
        "--poll",
        type=int,
        default=10,
        help="Polling interval in seconds when --wait is used (default: 10)",
    )
    
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download ResultFile3Ds once job is DONE (requires --wait)",
    )
    
    parser.add_argument(
        "--output", "-o",
        default="./hunyuan_output",
        help="Output directory for downloads (default: ./hunyuan_output)",
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
    
    # Validate file_ref
    file_ref = (args.file_ref or "").strip()
    if not file_ref:
        print("❌ file_ref (3D model URL or path) is required.", file=sys.stderr)
        sys.exit(1)
    if args.local and not os.path.exists(file_ref):
        print(f"❌ Local file not found: {file_ref}", file=sys.stderr)
        sys.exit(1)
    is_local = args.local or os.path.exists(file_ref)
    if not is_local and not (file_ref.startswith("http://") or file_ref.startswith("https://")):
        print("⚠️  Warning: file_ref does not look like a URL (http(s)://). Remote requests may fail.", file=sys.stderr)

    # Detect file type if not specified
    file_type = args.file_type or detect_file_type(file_ref)
    
    if not args.json:
        print(f"Submitting job...")
        print(f"  Source: {file_ref}")
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
            file_ref=file_ref,
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
                    job_id = resp["JobId"]
                    print(f"Job submitted successfully!")
                    print(f"  Job ID: {job_id}")
                    print(f"  Request ID: {resp.get('RequestId', 'N/A')}")
                    
                    # Wait for completion if requested
                    if args.wait:
                        job_response = wait_for_completion(job_id, poll_seconds=args.poll)
                        
                        if job_response and args.download:
                            # Download results
                            result_files = job_response.get("ResultFile3Ds", []) or []
                            if result_files:
                                downloaded = download_results(result_files, args.output)
                                if downloaded:
                                    print("\n" + "=" * 50)
                                    print("  📦 DOWNLOAD COMPLETE")
                                    print("=" * 50)
                                    print(f"\n📁 Output directory: {os.path.abspath(args.output)}")
                                    print(f"\n📄 Downloaded files:")
                                    for f in downloaded:
                                        size_mb = os.path.getsize(f) / (1024 * 1024)
                                        print(f"   • {os.path.basename(f)} ({size_mb:.1f} MB)")
                                    print("\n" + "-" * 50)
                            else:
                                print("\n⚠️  No result files found in job response")
                        elif job_response is None:
                            sys.exit(1)
                    elif args.download:
                        print("\n⚠️  --download requires --wait. Use --wait --download to download results.", file=sys.stderr)
                        
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
    except TencentCloudSDKException as e:
        print(f"API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(0)


if __name__ == "__main__":
    main()