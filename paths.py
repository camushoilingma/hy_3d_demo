# -*- coding: utf-8 -*-
"""
Standard input/output paths for hy-3d scripts.
All paths are relative to the repo root (where paths.py lives).
"""

import os

# Repo root (directory containing paths.py)
ROOT = os.path.dirname(os.path.abspath(__file__))

# Input assets (place your files here)
DIR_INPUT = os.path.join(ROOT, "input")
DIR_INPUT_IMAGES = os.path.join(DIR_INPUT, "images")
DIR_INPUT_MODELS = os.path.join(DIR_INPUT, "models")
DIR_INPUT_PROMPTS = os.path.join(DIR_INPUT, "prompts")

# Outputs (scripts and test write here)
DIR_OUTPUT = os.path.join(ROOT, "output")
DIR_OUTPUT_PRO = os.path.join(DIR_OUTPUT, "pro")
DIR_OUTPUT_RAPID = os.path.join(DIR_OUTPUT, "rapid")
DIR_OUTPUT_PART = os.path.join(DIR_OUTPUT, "part")
DIR_OUTPUT_SMART_TOPOLOGY = os.path.join(DIR_OUTPUT, "smart_topology")
DIR_OUTPUT_TEXTURE_EDIT = os.path.join(DIR_OUTPUT, "texture_edit")
DIR_OUTPUT_CONVERT = os.path.join(DIR_OUTPUT, "convert")
DIR_OUTPUT_QUERY = os.path.join(DIR_OUTPUT, "query")
DIR_OUTPUT_TEST = os.path.join(DIR_OUTPUT, "test")


def ensure_dirs():
    """Create input/output directories if they don't exist."""
    for d in (
        DIR_INPUT,
        DIR_INPUT_IMAGES,
        DIR_INPUT_MODELS,
        DIR_INPUT_PROMPTS,
        DIR_OUTPUT,
        DIR_OUTPUT_PRO,
        DIR_OUTPUT_RAPID,
        DIR_OUTPUT_PART,
        DIR_OUTPUT_SMART_TOPOLOGY,
        DIR_OUTPUT_TEXTURE_EDIT,
        DIR_OUTPUT_CONVERT,
        DIR_OUTPUT_QUERY,
        DIR_OUTPUT_TEST,
    ):
        os.makedirs(d, exist_ok=True)
