# -*- coding: utf-8 -*-
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

from download_utils import download_results


def get_client():
    s = load_secrets()
    cred = credential.Credential(s.secret_id, s.secret_key)

    http_profile = HttpProfile()
    http_profile.endpoint = s.endpoint

    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile

    return CommonClient("hunyuan", "2023-09-01", cred, s.region, profile=client_profile)


def submit_text_to_3d(prompt: str, face_count: int, generate_type: str) -> str:
    client = get_client()
    params = {"Prompt": prompt, "FaceCount": face_count, "GenerateType": generate_type}
    result = client.call_json("SubmitHunyuanTo3DProJob", params)
    job_id = result.get("Response", {}).get("JobId")
    if not job_id:
        raise RuntimeError(f"Submit failed: {json.dumps(result, indent=2)}")
    return job_id


def wait_for_completion(job_id: str, poll_seconds: int) -> list:
    client = get_client()
    params = {"JobId": job_id}

    start_time = time.time()
    while True:
        result = client.call_json("QueryHunyuanTo3DProJob", params)
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


def main():
    parser = argparse.ArgumentParser(description="Submit a Text-to-3D job, wait for completion, and download results.")
    parser.add_argument("--prompt", "-p", help="Text prompt. If omitted, you'll be prompted in the terminal.")
    parser.add_argument(
        "--faces",
        "-f",
        type=int,
        default=400000,
        help="Face count 40000–1500000 (default: 400000). Pro API minimum is 40000.",
    )
    parser.add_argument(
        "--type",
        "-t",
        choices=["Normal", "LowPoly", "Geometry", "Sketch"],
        default="Normal",
        help="Generate type (default: Normal)",
    )
    parser.add_argument("--poll", type=int, default=10, help="Polling interval in seconds (default: 10)")
    parser.add_argument("--output", "-o", default="./hunyuan_output_txt", help="Output directory (default: ./hunyuan_output_txt)")
    args = parser.parse_args()

    # Pro API FaceCount must be 40000–1500000
    if not 40000 <= args.faces <= 1500000:
        print(
            f"❌ --faces must be between 40,000 and 1,500,000 (Pro API limit). Got {args.faces}.",
            file=sys.stderr,
        )
        sys.exit(1)

    prompt = (args.prompt or "").strip()
    if not prompt:
        prompt = input("Enter prompt: ").strip()
    if not prompt:
        print("❌ Prompt is required.", file=sys.stderr)
        sys.exit(1)
    if len(prompt.encode("utf-8")) > 1024:
        print("⚠️  Warning: Pro API supports up to 1024 UTF-8 characters; prompt may be truncated.", file=sys.stderr)

    try:
        job_id = submit_text_to_3d(prompt=prompt, face_count=args.faces, generate_type=args.type)
        print(f"✅ Submitted. JobId: {job_id}")
        results = wait_for_completion(job_id, poll_seconds=args.poll)
        downloaded = download_results(results, args.output, base_name=prompt)
        print(f"✅ Downloaded {len(downloaded)} file(s) to: {os.path.abspath(args.output)}")
        if downloaded:
            print("Files:")
            for p in downloaded:
                print(f"  - {p}")
    except TencentCloudSDKException as err:
        raise SystemExit(f"API Error: {err}") from err


if __name__ == "__main__":
    main()