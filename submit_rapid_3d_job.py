# -*- coding: utf-8 -*-
"""
Submit a Hunyuan 3D Rapid job (text or image → 3D), wait for completion, and download results.

Uses SubmitHunyuanTo3DRapidJob and QueryHunyuanTo3DRapidJob.
Either --prompt, --image, or --image-url is required.
"""

import argparse
import base64
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


def submit_rapid_job(
    *,
    prompt: str | None = None,
    image_base64: str | None = None,
    image_url: str | None = None,
    result_format: str = "STL",
    enable_pbr: bool = False,
    enable_geometry: bool = False,
) -> str:
    """Submit a Hunyuan 3D Rapid job. One of prompt, image_base64, or image_url is required."""
    if not prompt and not image_base64 and not image_url:
        raise ValueError("One of prompt, image_base64, or image_url is required")
    if prompt and (image_base64 or image_url):
        raise ValueError("Prompt cannot be used together with image_base64 or image_url")

    params = {
        "ResultFormat": result_format,
        "EnablePBR": enable_pbr,
        "EnableGeometry": enable_geometry,
    }
    if prompt:
        params["Prompt"] = prompt
    elif image_base64:
        params["ImageBase64"] = image_base64
    else:
        params["ImageUrl"] = image_url

    client = get_client()
    result = client.call_json("SubmitHunyuanTo3DRapidJob", params)
    job_id = result.get("Response", {}).get("JobId")
    if not job_id:
        raise RuntimeError(f"Submit failed: {json.dumps(result, indent=2)}")
    return job_id


def wait_for_completion(job_id: str, poll_seconds: int) -> list:
    client = get_client()
    params = {"JobId": job_id}

    start_time = time.time()
    while True:
        result = client.call_json("QueryHunyuanTo3DRapidJob", params)
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
    parser = argparse.ArgumentParser(
        description="Submit a Hunyuan 3D Rapid job (text or image → 3D), wait for completion, and download results.",
        epilog="""
Examples:
  # Text to 3D
  python3 submit_rapid_3d_job.py --prompt "a cute cartoon cat"
  python3 submit_rapid_3d_job.py -p "wooden chair" --format GLB --pbr

  # Image to 3D
  python3 submit_rapid_3d_job.py --image photo.png
  python3 submit_rapid_3d_job.py --image-url "https://example.com/photo.jpg" -o ./rapid_out
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--prompt", "-p", help="Text prompt (text-to-3D). Cannot be used with --image/--image-url.")
    parser.add_argument("--image", "-i", help="Path to input image (image-to-3D). JPG, PNG, JPEG, WEBP.")
    parser.add_argument("--image-url", help="URL of input image (image-to-3D). Cannot be used with --prompt/--image.")
    parser.add_argument(
        "--format", "-f",
        choices=["OBJ", "GLB", "STL", "USDZ", "FBX", "MP4", "GIF"],
        default="STL",
        help="Output 3D file format (default: STL). USDZ/MP4/GIF may timeout for large models.",
    )
    parser.add_argument("--pbr", action="store_true", help="Enable PBR material generation")
    parser.add_argument("--geometry", action="store_true", help="Generate geometry only (white model, no textures); output GLB")
    parser.add_argument("--poll", type=int, default=10, help="Polling interval in seconds (default: 10)")
    parser.add_argument("--output", "-o", default="./hunyuan_output_rapid", help="Output directory (default: ./hunyuan_output_rapid)")
    args = parser.parse_args()

    # Require exactly one input: prompt, image file, or image URL
    has_prompt = bool((args.prompt or "").strip())
    has_image = bool(args.image)
    has_image_url = bool((args.image_url or "").strip())
    prompt_input = (args.prompt or "").strip()
    if not has_prompt and not has_image and not has_image_url:
        prompt_input = input("Enter prompt (or use --image/--image-url): ").strip()
        has_prompt = bool(prompt_input)
        if not has_prompt and not has_image and not has_image_url:
            parser.error("One of --prompt, --image, or --image-url is required")
    if has_prompt and (has_image or has_image_url):
        parser.error("--prompt cannot be used together with --image or --image-url")
    if has_image and has_image_url:
        parser.error("Use only one of --image or --image-url")

    prompt_arg = prompt_input if has_prompt else None
    if has_prompt and len((prompt_arg or "").encode("utf-8")) > 200:
        print("⚠️  Warning: Rapid API supports up to 200 UTF-8 characters for prompt; it may be truncated.", file=sys.stderr)
    image_base64_arg = None
    if args.image:
        if not os.path.exists(args.image):
            print(f"❌ Image file not found: {args.image}", file=sys.stderr)
            sys.exit(1)
        if os.path.splitext(args.image)[1].lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            print("⚠️  Warning: API supports JPG, PNG, JPEG, WEBP.", file=sys.stderr)
        with open(args.image, "rb") as f:
            image_base64_arg = base64.b64encode(f.read()).decode("utf-8")
    image_url_arg = (args.image_url or "").strip() if has_image_url else None

    try:
        job_id = submit_rapid_job(
            prompt=prompt_arg,
            image_base64=image_base64_arg,
            image_url=image_url_arg,
            result_format=args.format,
            enable_pbr=args.pbr,
            enable_geometry=args.geometry,
        )
        print(f"✅ Submitted. JobId: {job_id}")
        results = wait_for_completion(job_id, poll_seconds=args.poll)
        # Title: prompt that generated it, or source image filename/URL basename
        if prompt_arg:
            export_title = prompt_arg
        elif args.image:
            export_title = os.path.splitext(os.path.basename(args.image))[0]
        elif image_url_arg:
            export_title = os.path.splitext(os.path.basename(image_url_arg.split("?")[0]))[0] or "model"
        else:
            export_title = "model"
        downloaded = download_results(results, args.output, base_name=export_title)
        print(f"✅ Downloaded {len(downloaded)} file(s) to: {os.path.abspath(args.output)}")
        if downloaded:
            print("Files:")
            for p in downloaded:
                print(f"  - {p}")
    except TencentCloudSDKException as err:
        raise SystemExit(f"API Error: {err}") from err


if __name__ == "__main__":
    main()
