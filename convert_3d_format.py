# -*- coding: utf-8 -*-
"""
Convert a 3D model to another format using Tencent Hunyuan Convert3DFormat API.

Input: public URL or local file path (FBX, OBJ, or GLB; max 60 MB).
For local files, the file is uploaded to Tencent COS (if cos_bucket is set in secrets)
with public-read ACL, then the COS URL is used for the API call.
Output format: STL, USDZ, FBX, MP4, or GIF.
"""

import argparse
import json
import os
import sys
import urllib.request

from tencentcloud.common.common_client import CommonClient
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

from secrets import load_secrets

from cos_upload import resolve_input_to_url


def get_client():
    s = load_secrets()
    cred = credential.Credential(s.secret_id, s.secret_key)

    http_profile = HttpProfile()
    http_profile.endpoint = s.endpoint

    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile

    return CommonClient("hunyuan", "2023-09-01", cred, s.region, profile=client_profile)


def convert_3d_format(file_3d_url: str, output_format: str) -> str:
    """
    Call Convert3DFormat API. Returns the result file URL.

    Args:
        file_3d_url: Public URL of the 3D file (FBX, OBJ, or GLB; max 60 MB).
        output_format: One of STL, USDZ, FBX, MP4, GIF.

    Returns:
        URL of the converted file.
    """
    client = get_client()
    params = {"File3D": file_3d_url, "Format": output_format}
    result = client.call_json("Convert3DFormat", params)
    resp = result.get("Response", {})
    result_url = resp.get("ResultFile3D")
    if not result_url:
        error = resp.get("Error", {})
        if error:
            raise RuntimeError(f"{error.get('Code', 'Unknown')}: {error.get('Message', 'No message')}")
        raise RuntimeError(f"Convert failed: {json.dumps(result, indent=2)}")
    return result_url


def download_file(url: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    urllib.request.urlretrieve(url, output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Convert a 3D model to another format (Hunyuan Convert3DFormat API). Input: public URL or local path (FBX/OBJ/GLB, max 60 MB). Local files are uploaded to Tencent COS (public-read) when cos_bucket is set in secrets.",
        epilog="""
Examples:
  python3 convert_3d_format.py "https://example.com/model.glb" --format STL
  python3 convert_3d_format.py ./model.glb -f FBX -o ./converted
  python3 convert_3d_format.py test_out/model.glb -f FBX -o test_out
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file_3d_url",
        help="3D file: public URL or local path (FBX, OBJ, or GLB; max 60 MB). Local files are uploaded to COS (public-read) when cos_bucket is in secrets.",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["STL", "USDZ", "FBX", "MP4", "GIF"],
        default="STL",
        help="Output format (default: STL). USDZ/MP4/GIF may timeout for models over ~500k polygons.",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output path: directory (saved filename from URL) or full file path. If omitted, only the result URL is printed.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw API response JSON",
    )
    args = parser.parse_args()

    input_ref = (args.file_3d_url or "").strip()
    if not input_ref:
        parser.error("file_3d_url is required")
    if not input_ref.startswith("http://") and not input_ref.startswith("https://"):
        if not os.path.exists(input_ref):
            print(f"❌ Local file not found: {input_ref}", file=sys.stderr)
            sys.exit(1)
        ext = os.path.splitext(input_ref.split("?")[0])[1].lower()
        if ext not in (".glb", ".obj", ".fbx", ".gltf"):
            print("⚠️  Warning: Convert3DFormat supports FBX, OBJ, GLB. Other formats may fail.", file=sys.stderr)
        try:
            size_mb = os.path.getsize(input_ref) / (1024 * 1024)
            if size_mb > 60:
                print(f"⚠️  Warning: File is {size_mb:.1f} MB. API limit is 60 MB.", file=sys.stderr)
        except OSError:
            pass

    try:
        url = resolve_input_to_url(input_ref)
        if not url:
            raise SystemExit("Could not resolve input to a URL")
        result_url = convert_3d_format(url, args.format)
        if args.json:
            print(json.dumps({"Response": {"ResultFile3D": result_url}}, indent=2))
        else:
            print(f"✅ Converted. Result: {result_url}")

        if args.output:
            out_path = args.output
            if os.path.isdir(out_path) or not os.path.splitext(out_path)[1]:
                url_path = result_url.split("?")[0]
                filename = os.path.basename(url_path) or f"converted.{args.format.lower()}"
                out_path = os.path.join(out_path, filename)
            print(f"📥 Downloading to {out_path}...")
            download_file(result_url, out_path)
            print(f"✅ Saved: {os.path.abspath(out_path)}")
    except TencentCloudSDKException as err:
        raise SystemExit(f"API Error: {err}") from err


if __name__ == "__main__":
    main()
