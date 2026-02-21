# -*- coding: utf-8 -*-
import argparse
import json
import os
import sys
import time
import urllib.request

from tencentcloud.common.common_client import CommonClient
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

from secrets import load_secrets


def get_client():
    s = load_secrets()
    cred = credential.Credential(s.secret_id, s.secret_key)

    http_profile = HttpProfile()
    http_profile.endpoint = s.endpoint

    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile

    return CommonClient("hunyuan", "2023-09-01", cred, s.region, profile=client_profile)


def download_file(url: str, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    urllib.request.urlretrieve(url, output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Query a Hunyuan 3D job; optionally wait and download results.",
        epilog="""
Examples:
  # Query a text/image-to-3d job (default)
  %(prog)s <job_id> --wait --download

  # Query a Smart Topology job
  %(prog)s <job_id> --type smart-topology --wait --download

  # Query a Texture Edit / Part / Rapid job
  %(prog)s <job_id> --type texture-edit --wait --download
  %(prog)s <job_id> --type part --wait --download
  %(prog)s <job_id> --type rapid --wait --download
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("job_id", help="JobId to query")
    parser.add_argument(
        "--type", "-t",
        choices=["hunyuan", "smart-topology", "texture-edit", "part", "rapid"],
        default="hunyuan",
        help="Job type: hunyuan (default), smart-topology, texture-edit, part, or rapid"
    )
    parser.add_argument("--wait", action="store_true", help="Wait until job is DONE/FAIL")
    parser.add_argument("--poll", type=int, default=10, help="Polling interval seconds (default: 10)")
    parser.add_argument("--download", action="store_true", help="Download ResultFile3Ds once DONE")
    parser.add_argument("--output", "-o", default="./hunyuan_output_query", help="Output directory for downloads")
    args = parser.parse_args()

    job_id = (args.job_id or "").strip()
    if not job_id:
        print("❌ job_id is required.", file=sys.stderr)
        sys.exit(1)
    if not job_id.replace("-", "").replace("_", "").isalnum():
        print("⚠️  Warning: JobId usually looks like a numeric string (e.g. 1375367755519696896). Check if correct.", file=sys.stderr)

    client = get_client()
    params = {"JobId": job_id}

    # Determine which API to use based on job type
    if args.type == "smart-topology":
        api_action = "Describe3DSmartTopologyJob"
    elif args.type == "texture-edit":
        api_action = "QueryHunyuanTo3DTextureEditJob"
    elif args.type == "part":
        api_action = "QueryHunyuan3DPartJob"
    elif args.type == "rapid":
        api_action = "QueryHunyuanTo3DRapidJob"
    else:
        api_action = "QueryHunyuanTo3DProJob"

    try:
        while True:
            result = client.call_json(api_action, params)
            resp = result.get("Response", {})
            status = resp.get("Status")
            print(f"Status: {status}")

            if status in ("DONE", "FAIL"):
                print(json.dumps(result, indent=2))

            if status == "DONE":
                if args.download:
                    files = resp.get("ResultFile3Ds", []) or []
                    os.makedirs(args.output, exist_ok=True)
                    for i, file_info in enumerate(files):
                        if isinstance(file_info, dict):
                            url = file_info.get("Url") or file_info.get("FileUrl") or file_info.get("url") or ""
                        else:
                            url = str(file_info)
                        url = url.strip()
                        if not url:
                            continue
                        url_path = url.split("?")[0]
                        filename = os.path.basename(url_path) or f"model_{i+1}.glb"
                        out_path = os.path.join(args.output, filename)
                        print(f"📥 Downloading {filename}...")
                        download_file(url, out_path)
                    print(f"✅ Downloaded to: {os.path.abspath(args.output)}")
                break

            if status == "FAIL":
                error_code = resp.get("ErrorCode") or resp.get("Error", {}).get("Code", "Unknown")
                error_msg = resp.get("ErrorMessage") or resp.get("Error", {}).get("Message", "Unknown error")
                raise SystemExit(f"Job failed: {error_code} - {error_msg}")

            if not args.wait:
                break

            time.sleep(args.poll)

    except TencentCloudSDKException as err:
        raise SystemExit(f"API Error: {err}") from err


if __name__ == "__main__":
    main()
