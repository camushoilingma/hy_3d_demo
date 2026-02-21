#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tencent Hunyuan 3D Generator (2D image -> 3D model)

Usage:
  python3 submit_2d_to_3d.py <image_path> [options]
"""

import argparse
import base64
import os
import sys
import time

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

from secrets import load_secrets

from download_utils import download_results


def image_to_base64(image_path):
    """Convert local image file to base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_client():
    """Create and return API client"""
    s = load_secrets()
    cred = credential.Credential(s.secret_id, s.secret_key)
    
    httpProfile = HttpProfile()
    httpProfile.endpoint = s.endpoint
    
    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    
    return CommonClient("hunyuan", "2023-09-01", cred, s.region, profile=clientProfile)


def submit_job(params):
    """Submit the 3D generation job"""
    print("\n⏳ Submitting job...")
    
    client = get_client()
    result = client.call_json("SubmitHunyuanTo3DProJob", params)
    
    job_id = result.get("Response", {}).get("JobId")
    
    if job_id:
        print(f"✅ Job submitted successfully!")
        print(f"   Job ID: {job_id}")
        return job_id
    else:
        error = result.get("Response", {}).get("Error", {})
        print(f"❌ Submission failed!")
        print(f"   Error: {error.get('Code', 'Unknown')} - {error.get('Message', str(result))}")
        return None


def wait_for_completion(job_id):
    """Poll for job completion with progress display"""
    print("\n⏱️  Waiting for 3D generation (typically 2-5 minutes)...")
    print("-" * 50)
    
    client = get_client()
    params = {"JobId": job_id}
    
    start_time = time.time()
    poll_count = 0
    
    while True:
        poll_count += 1
        result = client.call_json("QueryHunyuanTo3DProJob", params)
        response = result.get("Response", {})
        status = response.get("Status")
        
        elapsed = int(time.time() - start_time)
        mins, secs = divmod(elapsed, 60)
        
        # Progress display
        spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"][poll_count % 10]
        print(f"\r   {spinner} Status: {status:<6} | Elapsed: {mins:02d}:{secs:02d}", end="", flush=True)
        
        if status == "DONE":
            print(f"\n\n🎉 SUCCESS! 3D model generated in {mins}m {secs}s")
            return response.get("ResultFile3Ds", [])
            
        elif status == "FAIL":
            error_code = response.get("ErrorCode", "Unknown")
            error_msg = response.get("ErrorMessage", "Unknown error")
            print(f"\n\n❌ Generation failed!")
            print(f"   Error: {error_code} - {error_msg}")
            return None
            
        else:  # WAIT or RUN
            time.sleep(5)


def print_summary(downloaded_files, output_dir):
    """Print final summary"""
    print("\n" + "=" * 50)
    print("  📦 DOWNLOAD COMPLETE")
    print("=" * 50)
    
    print(f"\n📁 Output directory: {os.path.abspath(output_dir)}")
    print(f"\n📄 Downloaded files:")
    
    for f in downloaded_files:
        size_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"   • {os.path.basename(f)} ({size_mb:.1f} MB)")
    
    print("\n" + "-" * 50)
    print("EN IN BLENDER:")
    print("   1. Open Blender")
    print("   2. File → Import → Wavefront (.obj) or glTF (.glb)")
    print(f"   3. Navigate to: {os.path.abspath(output_dir)}")
    print("   4. Select the file and click Import")
    print("   5. Press Z → Material Preview to see textures")
    print("-" * 50)


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Convert 2D images to 3D models using Tencent Hunyuan API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 submit_2d_to_3d.py photo.png
  python3 submit_2d_to_3d.py photo.png --faces 800000 --pbr
  python3 submit_2d_to_3d.py sketch.png --type Sketch
  python3 submit_2d_to_3d.py car.jpg --type LowPoly --polygon quad
        """
    )
    
    parser.add_argument(
        "image",
        help="Path to input image (JPG, PNG, JPEG, WEBP)"
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["Normal", "LowPoly", "Geometry", "Sketch"],
        default="Normal",
        help="Generation type (default: Normal)"
    )
    
    parser.add_argument(
        "--faces", "-f",
        type=int,
        default=400000,
        help="Face/polygon count: 40000-1500000 (default: 400000)"
    )
    
    parser.add_argument(
        "--pbr",
        action="store_true",
        help="Enable PBR materials (metallic, roughness)"
    )
    
    parser.add_argument(
        "--polygon", "-p",
        choices=["triangle", "quad"],
        default="triangle",
        help="Polygon type for LowPoly mode (default: triangle)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="./hunyuan_output",
        help="Output directory (default: ./hunyuan_output)"
    )
    
    parser.add_argument(
        "--left",
        help="Path to left view image (optional)"
    )
    
    parser.add_argument(
        "--right",
        help="Path to right view image (optional)"
    )
    
    parser.add_argument(
        "--back",
        help="Path to back view image (optional)"
    )
    
    args = parser.parse_args()
    
    # Print header
    print("\n" + "=" * 50)
    print("  🎨 TENCENT HUNYUAN 3D GENERATOR")
    print("=" * 50)
    
    # Validate input image
    if not os.path.exists(args.image):
        print(f"\n❌ Image file not found: {args.image}", file=sys.stderr)
        sys.exit(1)
    allowed_ext = (".jpg", ".jpeg", ".png", ".webp")
    if os.path.splitext(args.image)[1].lower() not in allowed_ext:
        print(f"\n⚠️  Warning: API supports JPG, PNG, JPEG, WEBP. Your file may not be accepted.", file=sys.stderr)
    try:
        size_mb = os.path.getsize(args.image) / (1024 * 1024)
        if size_mb > 6:
            print(f"\n⚠️  Warning: Image is {size_mb:.1f} MB. API recommends ≤6 MB (encoding adds ~30%%).", file=sys.stderr)
    except OSError:
        pass
    # Validate face count
    if not 40000 <= args.faces <= 1500000:
        print(f"\n❌ Face count must be between 40,000 and 1,500,000 (Pro API limit). Got {args.faces}.", file=sys.stderr)
        sys.exit(1)
    
    # Build API parameters
    print(f"\n📸 Loading image: {args.image}")
    params = {
        "ImageBase64": image_to_base64(args.image),
        "GenerateType": args.type,
        "FaceCount": args.faces,
        "EnablePBR": args.pbr
    }
    
    # Add polygon type for LowPoly mode
    if args.type == "LowPoly":
        params["PolygonType"] = "quadrilateral" if args.polygon == "quad" else "triangle"
    
    # Add multi-view images if provided
    multi_views = []
    for view_type, view_path in [("left", args.left), ("right", args.right), ("back", args.back)]:
        if view_path:
            if not os.path.exists(view_path):
                print(f"\n❌ {view_type} view image not found: {view_path}")
                sys.exit(1)
            print(f"📸 Loading {view_type} view: {view_path}")
            multi_views.append({
                "ViewType": view_type,
                "ViewImageBase64": image_to_base64(view_path)
            })
    
    if multi_views:
        params["MultiViewImages"] = multi_views
    
    # Print settings
    print("\n⚙️  Settings:")
    print(f"   • Type: {args.type}")
    print(f"   • Faces: {args.faces:,}")
    print(f"   • PBR: {'Yes' if args.pbr else 'No'}")
    if args.type == "LowPoly":
        print(f"   • Polygon: {args.polygon}")
    if multi_views:
        print(f"   • Extra views: {', '.join(v['ViewType'] for v in multi_views)}")
    
    try:
        # Submit job
        job_id = submit_job(params)
        if not job_id:
            sys.exit(1)

        # Wait for completion
        results = wait_for_completion(job_id)
        if not results:
            sys.exit(1)

        # Download results (title from source image filename)
        image_base_name = os.path.splitext(os.path.basename(args.image))[0]
        print("\n📥 Downloading 3D model files...")
        print("-" * 50)
        downloaded = download_results(results, args.output, base_name=image_base_name)

        if downloaded:
            print_summary(downloaded, args.output)
        else:
            print("\n❌ No files were downloaded")
            sys.exit(1)

    except TencentCloudSDKException as e:
        print(f"\n❌ API Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
