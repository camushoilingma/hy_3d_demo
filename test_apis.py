#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run tests for each Hunyuan 3D API endpoint.

Uses input/ and output/ layout (see paths.py). APIs that need local files
(image or 3D model) are skipped if the required input is missing.

Usage:
  python test_apis.py              # run all tests that have inputs
  python test_apis.py --api pro   # run only Pro text-to-3D
  python test_apis.py --api all   # run all (pro, rapid, then query with pro job_id)
  python test_apis.py --list      # list APIs and whether input is present
"""

import argparse
import os
import subprocess
import sys

# Repo root
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from paths import (
    DIR_INPUT_IMAGES,
    DIR_INPUT_MODELS,
    DIR_OUTPUT_TEST,
    ensure_dirs,
)


def _first_file(directory: str, *extensions: str) -> str | None:
    """Return path to first file in directory with one of the given extensions (e.g. .fbx, .glb)."""
    if not os.path.isdir(directory):
        return None
    exts = {e.lower() for e in extensions}
    for name in sorted(os.listdir(directory)):
        if os.path.splitext(name)[1].lower() in exts:
            return os.path.join(directory, name)
    return None


def has_pro_input() -> bool:
    return True  # prompt only


def has_rapid_input() -> bool:
    return True  # prompt only


def has_part_input() -> bool:
    return _first_file(DIR_INPUT_MODELS, ".fbx") is not None


def has_smart_topology_input() -> bool:
    return (
        _first_file(DIR_INPUT_MODELS, ".glb", ".gltf", ".obj", ".fbx", ".stl")
        is not None
    )


def has_texture_edit_input() -> bool:
    return _first_file(DIR_INPUT_MODELS, ".fbx") is not None


def has_convert_input() -> bool:
    return _first_file(DIR_INPUT_MODELS, ".glb", ".obj", ".fbx") is not None


def run_cmd(args: list[str], timeout: int | None = 600, env: dict | None = None) -> tuple[bool, str]:
    """Run command; return (success, combined stdout+stderr)."""
    env = env or os.environ.copy()
    try:
        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, out
    except subprocess.TimeoutExpired as e:
        return False, (e.stdout or "") + (e.stderr or "") + "\n(Timed out)"
    except Exception as e:
        return False, str(e)


def test_pro(out_dir: str, poll: int) -> tuple[bool, str]:
    script = os.path.join(ROOT, "submit_txt_to_3d_job.py")
    ok, out = run_cmd(
        [sys.executable, script, "--prompt", "a simple cube", "--faces", "40000", "-o", out_dir, "--poll", str(poll)],
        timeout=600,
    )
    return ok, out


def test_rapid(out_dir: str, poll: int) -> tuple[bool, str]:
    script = os.path.join(ROOT, "submit_rapid_3d_job.py")
    ok, out = run_cmd(
        [sys.executable, script, "--prompt", "a simple cube", "--format", "GLB", "-o", out_dir, "--poll", str(poll)],
        timeout=600,
    )
    return ok, out


def test_part(out_dir: str, poll: int) -> tuple[bool, str]:
    fbx = _first_file(DIR_INPUT_MODELS, ".fbx")
    if not fbx:
        return False, "No FBX file in input/models/ (Part job requires FBX)."
    script = os.path.join(ROOT, "submit_part_3d_job.py")
    ok, out = run_cmd(
        [sys.executable, script, "--file", fbx, "-o", out_dir, "--poll", str(poll)],
        timeout=600,
    )
    return ok, out


def test_smart_topology(out_dir: str, poll: int) -> tuple[bool, str]:
    model = _first_file(DIR_INPUT_MODELS, ".glb", ".gltf", ".obj", ".fbx", ".stl")
    if not model:
        return False, "No 3D file (GLB/OBJ/FBX/STL) in input/models/."
    script = os.path.join(ROOT, "submit_smart_topology.py")
    ok, out = run_cmd(
        [sys.executable, script, model, "--local", "--wait", "--download", "-o", out_dir, "--poll", str(poll)],
        timeout=600,
    )
    return ok, out


def test_texture_edit(out_dir: str, poll: int) -> tuple[bool, str]:
    fbx = _first_file(DIR_INPUT_MODELS, ".fbx")
    if not fbx:
        return False, "No FBX file in input/models/ (Texture Edit requires FBX)."
    script = os.path.join(ROOT, "submit_texture_edit_job.py")
    ok, out = run_cmd(
        [sys.executable, script, fbx, "--prompt", "white material", "-o", out_dir, "--poll", str(poll)],
        timeout=600,
    )
    return ok, out


def test_convert(out_dir: str) -> tuple[bool, str]:
    model = _first_file(DIR_INPUT_MODELS, ".glb", ".obj", ".fbx")
    if not model:
        return False, "No GLB/OBJ/FBX in input/models/ (Convert needs a 3D file)."
    script = os.path.join(ROOT, "convert_3d_format.py")
    ok, out = run_cmd(
        [sys.executable, script, model, "--format", "STL", "-o", out_dir],
        timeout=300,
    )
    return ok, out


def test_query(job_id: str, out_dir: str, poll: int) -> tuple[bool, str]:
    if not job_id:
        return False, "No job_id provided (run Pro or Rapid test first to get one)."
    script = os.path.join(ROOT, "query_job.py")
    ok, out = run_cmd(
        [sys.executable, script, job_id, "--type", "hunyuan", "--wait", "--download", "-o", out_dir, "--poll", str(poll)],
        timeout=300,
    )
    return ok, out


def main():
    parser = argparse.ArgumentParser(
        description="Test each Hunyuan 3D API endpoint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--api",
        choices=["all", "pro", "rapid", "part", "smart-topology", "texture-edit", "convert", "query"],
        default="all",
        help="Which API(s) to test (default: all). 'query' needs a job_id from a previous run.",
    )
    parser.add_argument(
        "--poll",
        type=int,
        default=10,
        help="Polling interval in seconds for async jobs (default: 10).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Only list APIs and whether required input is present; do not run.",
    )
    parser.add_argument(
        "--job-id",
        default="",
        help="JobId for testing query API (optional; if not set and --api query, query is skipped).",
    )
    args = parser.parse_args()

    ensure_dirs()

    apis = [
        ("pro", "SubmitHunyuanTo3DProJob (text→3D)", has_pro_input, None),
        ("rapid", "SubmitHunyuanTo3DRapidJob (text→3D)", has_rapid_input, None),
        ("part", "SubmitHunyuan3DPartJob", has_part_input, None),
        ("smart-topology", "Submit3DSmartTopologyJob", has_smart_topology_input, None),
        ("texture-edit", "SubmitHunyuanTo3DTextureEditJob", has_texture_edit_input, None),
        ("convert", "Convert3DFormat", has_convert_input, None),
        ("query", "QueryHunyuanTo3DProJob", lambda: bool(args.job_id), None),
    ]

    if args.list:
        print("API tests and required input:\n")
        for key, label, has_input, _ in apis:
            status = "✓ input present" if has_input() else "✗ missing input (skip)"
            print(f"  {key:20} {label:45} {status}")
        return 0

    to_run = []
    if args.api == "all":
        # Run all that have input; query will be run at the end if we got a job_id from pro/rapid
        to_run = [a for a in apis if a[0] != "query" and a[2]()]
        if not to_run:
            print("No APIs have required input. Add files to input/images/ and input/models/ (see input/README.md).")
            return 1
    else:
        for a in apis:
            if a[0] == args.api:
                if not a[2]():
                    print(f"Missing input for {a[0]}. {a[1]}")
                    return 1
                to_run = [a]
                break
        if not to_run:
            to_run = [(args.api, args.api, lambda: True, None)]

    print("=" * 60)
    print("  Hunyuan 3D API tests")
    print("=" * 60)
    print(f"  Output dir: {DIR_OUTPUT_TEST}")
    print(f"  Poll: {args.poll}s")
    print()

    last_job_id = args.job_id
    results = []

    for key, label, _, _ in to_run:
        out_dir = os.path.join(DIR_OUTPUT_TEST, key)
        os.makedirs(out_dir, exist_ok=True)
        print(f"[{key}] {label} ...")

        if key == "pro":
            ok, out = test_pro(out_dir, args.poll)
        elif key == "rapid":
            ok, out = test_rapid(out_dir, args.poll)
        elif key == "part":
            ok, out = test_part(out_dir, args.poll)
        elif key == "smart-topology":
            ok, out = test_smart_topology(out_dir, args.poll)
        elif key == "texture-edit":
            ok, out = test_texture_edit(out_dir, args.poll)
        elif key == "convert":
            ok, out = test_convert(out_dir)
        elif key == "query":
            ok, out = test_query(last_job_id, out_dir, args.poll)
        else:
            ok, out = False, "Unknown API"

        # Capture JobId from submit output for later query test
        if "JobId:" in out or "Job ID:" in out:
            for line in out.splitlines():
                line = line.strip()
                if "JobId:" in line:
                    parts = line.split("JobId:", 1)
                    if len(parts) == 2:
                        last_job_id = parts[1].strip().split()[0].rstrip(",")
                        break
                if "Job ID:" in line:
                    parts = line.split("Job ID:", 1)
                    if len(parts) == 2:
                        last_job_id = parts[1].strip().split()[0].rstrip(",")
                        break

        results.append((key, ok, out))
        if ok:
            print(f"  ✅ PASS")
        else:
            print(f"  ❌ FAIL")
            if out.strip():
                for line in out.strip().splitlines()[:15]:
                    print(f"     {line}")

    # If we ran "all" and got a job_id from pro/rapid, run query test
    if args.api == "all" and last_job_id:
        out_dir = os.path.join(DIR_OUTPUT_TEST, "query")
        os.makedirs(out_dir, exist_ok=True)
        print(f"[query] QueryHunyuanTo3DProJob (JobId from above) ...")
        ok, out = test_query(last_job_id, out_dir, args.poll)
        results.append(("query", ok, out))
        if ok:
            print(f"  ✅ PASS")
        else:
            print(f"  ❌ FAIL")
            if out.strip():
                for line in out.strip().splitlines()[:15]:
                    print(f"     {line}")

    print()
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"  Result: {passed}/{len(results)} passed")
    print("=" * 60)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
