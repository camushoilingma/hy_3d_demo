# -*- coding: utf-8 -*-
"""
Submit a Hunyuan 3D Part job (3D model → component identification/generation), wait for completion, and download results.

Uses SubmitHunyuan3DPartJob and QueryHunyuan3DPartJob.
Input: FBX only, ≤30k faces, ≤100MB recommended. Local files (--file) are uploaded via cos_upload (Tencent COS public-read).
"""

import argparse
import json
import os
import sys
import time

from tencentcloud.common.common_client import CommonClient
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

from secrets import load_secrets

from cos_upload import resolve_input_to_url
from download_utils import download_results


def get_client():
    s = load_secrets()
    cred = credential.Credential(s.secret_id, s.secret_key)

    http_profile = HttpProfile()
    http_profile.endpoint = s.endpoint

    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile

    return CommonClient("hunyuan", "2023-09-01", cred, s.region, profile=client_profile)


def submit_part_job(*, file_url: str, file_type: str = "FBX") -> str:
    """Submit a Hunyuan 3D Part job. file_url (public URL) is required."""
    file3d = {"Type": file_type.upper(), "Url": file_url}
    params = {"File": file3d}
    client = get_client()
    result = client.call_json("SubmitHunyuan3DPartJob", params)
    job_id = result.get("Response", {}).get("JobId")
    if not job_id:
        raise RuntimeError(f"Submit failed: {json.dumps(result, indent=2)}")
    return job_id


def wait_for_completion(job_id: str, poll_seconds: int) -> list:
    client = get_client()
    params = {"JobId": job_id}

    start_time = time.time()
    while True:
        result = client.call_json("QueryHunyuan3DPartJob", params)
        resp = result.get("Response", {})
        status = resp.get("Status")

        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        print(f"\rStatus: {status:<6} | Elapsed: {mins:02d}:{secs:02d}", end="", flush=True)

        if status == "DONE":
            print("\n✅ Job completed!")
            return resp.get("ResultFile3Ds", []) or []
        if status == "FAIL":
            print("\n❌ Job failed!")
            raise RuntimeError(f"{resp.get('ErrorCode')} - {resp.get('ErrorMessage')}")

        time.sleep(poll_seconds)


def detect_file_type(path_or_url: str) -> str:
    """Detect file type from path/URL extension. API supports FBX only."""
    s = (path_or_url or "").lower().split("?")[0]
    return "FBX" if s.endswith(".fbx") else "FBX"


def main():
    parser = argparse.ArgumentParser(
        description="Submit a Hunyuan 3D Part job (3D model → component identification/generation), wait for completion, and download results.",
        epilog="""
Examples:
  # From URL (FBX, ≤30k faces, ≤100MB recommended)
  python3 submit_part_3d_job.py --url "https://example.com/model.fbx"
  python3 submit_part_3d_job.py --url "https://example.com/model.fbx" -o ./part_out

  # From local file (uploaded to Tencent COS public-read; requires cos_bucket in secrets)
  python3 submit_part_3d_job.py --file ./model.fbx
  python3 submit_part_3d_job.py --file ./model.fbx --poll 10 -o ./part_out
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", "-u", help="URL of input 3D file (FBX; valid 24h). Cannot be used with --file.")
    parser.add_argument("--file", "-f", help="Path to local FBX file (uploaded via cos_upload; requires cos_bucket in secrets). Cannot be used with --url.")
    parser.add_argument("--type", "-t", choices=["FBX"], default=None, help="Input file format (API supports FBX only; default: FBX)")
    parser.add_argument("--poll", type=int, default=10, help="Polling interval in seconds (default: 10)")
    parser.add_argument("--output", "-o", default="./hunyuan_output_part", help="Output directory (default: ./hunyuan_output_part)")
    args = parser.parse_args()

    has_url = bool((args.url or "").strip())
    has_file = bool(args.file)
    if not has_url and not has_file:
        parser.error("One of --url or --file is required")
    if has_url and has_file:
        parser.error("Use only one of --url or --file")

    file_type = args.type or detect_file_type(args.url or args.file or "")

    if has_file and not os.path.exists(args.file):
        print(f"❌ File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    if has_file and not (args.file or "").lower().endswith(".fbx"):
        print("⚠️  Warning: SubmitHunyuan3DPartJob accepts FBX only (≤30k faces, ≤100 MB recommended).", file=sys.stderr)

    input_ref = (args.url or "").strip() if has_url else args.file
    file_url_arg = resolve_input_to_url(input_ref, subfolder="part")

    if not file_url_arg:
        print("❌ Could not resolve input to a URL", file=sys.stderr)
        sys.exit(1)

    try:
        job_id = submit_part_job(file_url=file_url_arg, file_type=file_type)
        print(f"✅ Submitted. JobId: {job_id}")
        results = wait_for_completion(job_id, poll_seconds=args.poll)
        base_name = None
        if has_file:
            base_name = os.path.splitext(os.path.basename(args.file))[0]
        elif has_url:
            base_name = os.path.splitext(os.path.basename(file_url_arg.split("?")[0]))[0] or None
        downloaded = download_results(results, args.output, base_name=base_name)
        print(f"✅ Downloaded {len(downloaded)} file(s) to: {os.path.abspath(args.output)}")
        if downloaded:
            print("Files:")
            for p in downloaded:
                print(f"  - {p}")
    except TencentCloudSDKException as err:
        raise SystemExit(f"API Error: {err}") from err


if __name__ == "__main__":
    main()
