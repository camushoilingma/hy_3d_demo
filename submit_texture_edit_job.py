# -*- coding: utf-8 -*-
"""
Submit a Hunyuan 3D Texture Edit job: redraw texture of an FBX model from a prompt or reference image.

Uses SubmitHunyuanTo3DTextureEditJob and QueryHunyuanTo3DTextureEditJob.
Input: one FBX 3D model (URL or local path; under 100k faces) and either a text prompt or reference image.
Output: redrawn texture files (e.g. OBJ, FBX, IMAGE) in ResultFile3Ds.
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


def submit_texture_edit_job(
    *,
    file_3d_url: str,
    prompt: str | None = None,
    image_base64: str | None = None,
    image_url: str | None = None,
    enable_pbr: bool = False,
) -> str:
    """
    Submit a texture edit job. File3D must be FBX (<100k faces).
    Exactly one of prompt or (image_base64 or image_url) is required; they cannot be used together.
    """
    if not prompt and not image_base64 and not image_url:
        raise ValueError("One of prompt or image (--image / --image-url) is required")
    if prompt and (image_base64 or image_url):
        raise ValueError("Prompt and image cannot be used together")

    params = {
        "File3D": {"Type": "FBX", "Url": file_3d_url},
    }
    if prompt:
        params["Prompt"] = prompt
        if enable_pbr:
            params["EnablePBR"] = True
    elif image_base64:
        params["Image"] = {"Base64": image_base64}
    else:
        params["Image"] = {"Url": image_url}

    client = get_client()
    result = client.call_json("SubmitHunyuanTo3DTextureEditJob", params)
    job_id = result.get("Response", {}).get("JobId")
    if not job_id:
        raise RuntimeError(f"Submit failed: {json.dumps(result, indent=2)}")
    return job_id


def wait_for_completion(job_id: str, poll_seconds: int) -> list:
    client = get_client()
    params = {"JobId": job_id}
    start_time = time.time()
    while True:
        result = client.call_json("QueryHunyuanTo3DTextureEditJob", params)
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
        description="Submit a 3D texture edit job (redraw FBX texture from prompt or reference image).",
        epilog="""
Requirements:
  - 3D model: FBX format, public URL or local path; <100,000 faces.
  - Guidance: either --prompt (text) or --image/--image-url (reference image). Not both.
  - Reference image: 128–4096 px, JPG/PNG, Base64 <10MB if using --image.

Examples:
  # Texture from text prompt
  python3 submit_texture_edit_job.py "https://example.com/model.fbx" --prompt "wooden material"
  python3 submit_texture_edit_job.py ./model.fbx -p "red metallic" --pbr -o ./texture_out

  # Texture from reference image
  python3 submit_texture_edit_job.py ./model.fbx --image reference.png -o ./texture_out
  python3 submit_texture_edit_job.py "https://example.com/model.fbx" --image-url "https://example.com/ref.jpg"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "model",
        help="FBX 3D model: public URL or local path (<100k faces). Local files are uploaded to COS if configured.",
    )
    parser.add_argument(
        "--prompt", "-p",
        help="Text description for texture editing (e.g. 'a kitten', 'wooden'). Cannot be used with --image/--image-url.",
    )
    parser.add_argument(
        "--image", "-i",
        help="Path to reference image for texture (JPG/PNG, 128–4096 px, <10MB).",
    )
    parser.add_argument(
        "--image-url",
        help="URL of reference image. Cannot be used with --prompt/--image.",
    )
    parser.add_argument(
        "--pbr",
        action="store_true",
        help="Enable PBR texture (only when using --prompt).",
    )
    parser.add_argument("--poll", type=int, default=10, help="Polling interval in seconds (default: 10)")
    parser.add_argument(
        "--output", "-o",
        default="./hunyuan_output_texture_edit",
        help="Output directory (default: ./hunyuan_output_texture_edit)",
    )
    args = parser.parse_args()

    model_ref = (args.model or "").strip()
    if not model_ref:
        parser.error("model is required")
    if not model_ref.startswith("http") and not os.path.exists(model_ref):
        print(f"❌ Model path not found: {model_ref}", file=sys.stderr)
        sys.exit(1)
    if not model_ref.lower().split("?")[0].endswith(".fbx"):
        print("⚠️  Warning: Texture Edit API expects FBX format, <100,000 faces recommended.", file=sys.stderr)

    has_prompt = bool((args.prompt or "").strip())
    has_image = bool(args.image)
    has_image_url = bool((args.image_url or "").strip())
    if not has_prompt and not has_image and not has_image_url:
        parser.error("One of --prompt, --image, or --image-url is required")
    if has_prompt and (has_image or has_image_url):
        parser.error("--prompt cannot be used together with --image or --image-url")
    if has_image and has_image_url:
        parser.error("Use only one of --image or --image-url")

    # Resolve model to URL (upload local FBX to COS if needed)
    try:
        file_3d_url = resolve_input_to_url(model_ref)
    except SystemExit:
        raise
    if not file_3d_url:
        raise SystemExit("Could not resolve model to a URL")

    prompt_arg = (args.prompt or "").strip() if has_prompt else None
    image_base64_arg = None
    if args.image:
        if not os.path.exists(args.image):
            print(f"❌ Image not found: {args.image}", file=sys.stderr)
            sys.exit(1)
        ext = os.path.splitext(args.image)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png"):
            print("⚠️  Warning: Reference image should be JPG or PNG, 128–4096 px, Base64 <10 MB.", file=sys.stderr)
        with open(args.image, "rb") as f:
            image_base64_arg = base64.b64encode(f.read()).decode("utf-8")
    image_url_arg = (args.image_url or "").strip() if has_image_url else None

    # Base name for downloaded files: prompt or model/image name
    if prompt_arg:
        export_title = prompt_arg
    elif args.image:
        export_title = os.path.splitext(os.path.basename(args.image))[0]
    else:
        export_title = os.path.splitext(os.path.basename(model_ref.split("?")[0]))[0] or "texture_edit"

    try:
        job_id = submit_texture_edit_job(
            file_3d_url=file_3d_url,
            prompt=prompt_arg,
            image_base64=image_base64_arg,
            image_url=image_url_arg,
            enable_pbr=args.pbr,
        )
        print(f"✅ Submitted. JobId: {job_id}")
        results = wait_for_completion(job_id, poll_seconds=args.poll)
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
