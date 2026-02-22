# -*- coding: utf-8 -*-
"""
Shared helpers for downloading 3D result files with optional base name (title).

Exported files are named from the generating prompt or source filename when base_name is set.
"""

import os
import re
import urllib.request
from typing import Dict, List, Optional


def sanitize_base_name(s: str, max_length: int = 120) -> str:
    """
    Make a string safe for use as a filename prefix (e.g. from prompt or image name).
    Replaces invalid path chars, collapses spaces to underscore, truncates.
    """
    if not s or not isinstance(s, str):
        return "model"
    # Strip path if present
    s = os.path.basename(s.strip())
    # Remove extension for cleaner title when s was a filename
    s = os.path.splitext(s)[0]
    # Replace chars invalid in filenames: \ / : * ? " < > |
    s = re.sub(r'[\s\\/:*?"<>|]+', "_", s)
    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        return "model"
    return s[:max_length] if len(s) > max_length else s


def download_file(url: str, output_path: str) -> None:
    """Download a file from URL to output_path."""
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    urllib.request.urlretrieve(url, output_path)


def _ext_from_url(url: str, default: str = ".glb") -> str:
    """Get file extension from URL path (before query string)."""
    path = url.split("?")[0].lower()
    if ".zip" in path:
        return ".zip"
    if ".obj" in path:
        return ".obj"
    if ".glb" in path or ".gltf" in path:
        return ".glb"
    if ".fbx" in path:
        return ".fbx"
    if ".stl" in path:
        return ".stl"
    if ".png" in path:
        return ".png"
    if ".jpg" in path or ".jpeg" in path:
        return ".jpg"
    return default


def download_results(
    file_list: list,
    output_dir: str,
    base_name: Optional[str] = None,
) -> List[str]:
    """
    Download result files (ResultFile3Ds) into output_dir.
    If base_name is set, name files: base_name.ext, base_name_2.ext, ... (sanitized).
    Otherwise use filename from URL as before.
    """
    os.makedirs(output_dir, exist_ok=True)
    downloaded: List[str] = []
    used_names: Dict[str, int] = {}  # base no ext -> count for _2, _3

    for i, file_info in enumerate(file_list):
        if isinstance(file_info, dict):
            url = file_info.get("Url") or file_info.get("FileUrl") or file_info.get("url") or ""
        else:
            url = str(file_info)
        url = url.strip()
        if not url:
            continue

        ext = _ext_from_url(url)
        if base_name:
            safe = sanitize_base_name(base_name)
            if safe not in used_names:
                used_names[safe] = 0
            used_names[safe] += 1
            n = used_names[safe]
            filename = f"{safe}{ext}" if n == 1 else f"{safe}_{n}{ext}"
        else:
            filename = os.path.basename(url.split("?")[0]) or f"model_{i+1}{ext}"

        out_path = os.path.join(output_dir, filename)
        print(f"📥 Downloading {filename}...")
        download_file(url, out_path)
        downloaded.append(out_path)

    return downloaded
