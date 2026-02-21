# hy-3d

CLI scripts for Tencent Cloud **Hunyuan 3D** APIs: text/image → 3D, topology, part generation, texture edit, format conversion, and job query.

---

## Requirements

| Requirement | Notes |
|-------------|--------|
| **Python 3** | 3.8+ recommended |
| **tencentcloud-sdk-python** | Required for all scripts: `pip install tencentcloud-sdk-python` |
| **cos-python-sdk-v5** | Optional. Only needed when using **local files** with `convert_3d_format.py`, `submit_part_3d_job.py`, or `submit_texture_edit_job.py` (upload to Tencent COS). |

Create a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install tencentcloud-sdk-python
# Optional, for local-file uploads:
pip install cos-python-sdk-v5
```

---

## Implemented APIs

| API | Script | What it does | Input requirements |
|-----|--------|---------------|--------------------|
| **SubmitHunyuanTo3DProJob** | `submit_txt_to_3d_job.py` | Text → 3D (Pro) | Prompt ≤1024 chars; faces 40k–1.5M |
| **QueryHunyuanTo3DProJob** | (same + `query_job.py`) | Query Pro job | JobId |
| **SubmitHunyuanTo3DProJob** | `submit_2d_to_3d.py` | Image → 3D (Pro) | Image JPG/PNG/JPEG/WEBP, ≤6 MB; faces 40k–1.5M |
| **SubmitHunyuanTo3DRapidJob** | `submit_rapid_3d_job.py` | Text or image → 3D (Rapid) | Prompt ≤200 chars or image; output format OBJ/GLB/STL/USDZ/FBX/MP4/GIF |
| **QueryHunyuanTo3DRapidJob** | (same) | Query Rapid job | JobId (use `query_job.py` with type for download) |
| **SubmitHunyuan3DPartJob** | `submit_part_3d_job.py` | 3D → component parts | **FBX only**, ≤30k faces, ≤100 MB; URL or local (COS) |
| **QueryHunyuan3DPartJob** | (same) | Query Part job | JobId |
| **Submit3DSmartTopologyJob** | `submit_smart_topology.py` | 3D retopology (Polygen 1.5) | URL or local; GLB/GLTF/OBJ/FBX/STL |
| **Describe3DSmartTopologyJob** | (same + `query_job.py`) | Query Smart Topology job | JobId |
| **SubmitHunyuanTo3DTextureEditJob** | `submit_texture_edit_job.py` | Redraw FBX texture from prompt or image | FBX model <100k faces; prompt **or** reference image |
| **QueryHunyuanTo3DTextureEditJob** | (same + `query_job.py`) | Query Texture Edit job | JobId |
| **Convert3DFormat** | `convert_3d_format.py` | Convert 3D format | Input: FBX/OBJ/GLB, max 60 MB. Output: STL/USDZ/FBX/MP4/GIF |
| **Query (any)** | `query_job.py` | Query by JobId, optional wait + download | JobId; `--type hunyuan\|smart-topology\|texture-edit\|part\|rapid` |

All scripts validate inputs where possible and print **warnings** (e.g. wrong format, size) or **errors** (e.g. missing file, invalid range) before calling the API.

---

## Secrets (required)

Secrets file **location** (first found wins):

1. `$HY3D_SECRETS_PATH`
2. `./secrets.json`
3. `~/.hy-3d-secrets.json`

**Contents:**

```json
{
  "secret_id": "YOUR_SECRET_ID",
  "secret_key": "YOUR_SECRET_KEY",
  "region": "ap-singapore",
  "endpoint": "hunyuan.intl.tencentcloudapi.com",
  "cos_bucket": "your-bucket-appid",
  "cos_region": "ap-singapore"
}
```

- `cos_bucket` and `cos_region` are **optional**; needed only when scripts upload **local** files (e.g. Part job, Texture Edit, Convert) to Tencent COS.

---

## Input and output layout

Scripts use a simple layout so inputs and outputs stay organised:

| Path | Purpose |
|------|---------|
| **`input/images/`** | 2D images for Image→3D (Pro, Rapid) and texture reference (Texture Edit). JPG, PNG, WEBP. Example files: `bose.png`, `chair_selency.webp`, `electro-box.png`, `table-selency.webp`. |
| **`input/models/`** | 3D models for Part job (FBX), Smart Topology, Texture Edit, Convert. GLB, OBJ, FBX, etc. |
| **`input/prompts/`** | Example text prompts for Text→3D. e.g. `leopard_airpods.txt`. Use: `--prompt "$(cat input/prompts/leopard_airpods.txt)"`. |
| **`output/`** | All script outputs. Subdirs: `pro/`, `rapid/`, `part/`, `smart_topology/`, `texture_edit/`, `convert/`, `query/`, `test/`. |

- **Input:** Put your images and 3D files in `input/images/` and `input/models/` (see [input/README.md](input/README.md)). Scripts also accept paths anywhere.
- **Output:** Scripts default to their own dirs (e.g. `./hunyuan_output_txt`); you can pass `-o output/pro` etc. The **test script** writes under `output/test/<api>/`.
- The `output/` directory is in `.gitignore`.

---

## Running the API tests

A single script runs each API endpoint (submit → wait → download where applicable). Use your venv so the Tencent SDK is available:

```bash
source .venv/bin/activate   # if you use a venv
# List which APIs have required input present
python3 test_apis.py --list

# Run all tests that have input (Pro, Rapid; Part/Smart Topology/Texture Edit/Convert if files in input/models/)
python3 test_apis.py

# Run one API only
python3 test_apis.py --api pro
python3 test_apis.py --api rapid
python3 test_apis.py --api part        # needs input/models/*.fbx
python3 test_apis.py --api smart-topology  # needs input/models/*.glb etc.
python3 test_apis.py --api texture-edit    # needs input/models/*.fbx
python3 test_apis.py --api convert         # needs input/models/*.glb or .obj or .fbx
python3 test_apis.py --api query --job-id <JOB_ID>
```

- **Pro** and **Rapid** need no files (they use a test prompt). **Part**, **Smart Topology**, **Texture Edit**, and **Convert** need files in `input/models/`; if missing, they are skipped when you run `--api all`.
- Results are written to **`output/test/<api>/`**. When you run `--api all`, the script also runs a **Query** test using the JobId from the Pro job.
- Polling interval: `--poll 10` (default).

---

## Usage

### Text → 3D (Pro)

```bash
python3 submit_txt_to_3d_job.py --prompt "a cute cartoon cat" -o output/pro
```

Options: `--faces 400000`, `--type Normal|LowPoly|Geometry|Sketch`, `--poll 10`.

### Image → 3D (Pro)

```bash
python3 submit_2d_to_3d.py input/images/photo.png -o output/pro
```

Options: `--faces`, `--type`, `--pbr`, `--polygon triangle|quad`, `--left/--right/--back`.

### Text or Image → 3D (Rapid, optional output format)

```bash
python3 submit_rapid_3d_job.py --prompt "a wooden chair" --format FBX -o output/rapid
python3 submit_rapid_3d_job.py --image input/images/photo.png --format GLB -o output/rapid
```

Options: `--format OBJ|GLB|STL|USDZ|FBX|MP4|GIF`, `--pbr`, `--geometry`.

### 3D Part (component generation, FBX only)

```bash
python3 submit_part_3d_job.py --url "https://example.com/model.fbx" -o output/part
python3 submit_part_3d_job.py --file input/models/model.fbx -o output/part   # requires cos_bucket in secrets
```

### Smart Topology (retopology)

```bash
python3 submit_smart_topology.py https://example.com/model.glb -f low
python3 submit_smart_topology.py input/models/model.glb --local --wait --download -o output/smart_topology
```

Options: `-t GLB|GLTF|OBJ|FBX|STL`, `-p triangle|quadrilateral`, `-f high|medium|low`, `--wait`, `--download`.

### Texture Edit (redraw FBX texture)

```bash
python3 submit_texture_edit_job.py input/models/model.fbx --prompt "wooden material" -o output/texture_edit
python3 submit_texture_edit_job.py "https://example.com/model.fbx" --image input/images/ref.png -o output/texture_edit
```

### Convert 3D format

```bash
python3 convert_3d_format.py "https://example.com/model.glb" --format STL
python3 convert_3d_format.py input/models/model.glb -f FBX -o output/convert
```

### Query any job

```bash
python3 query_job.py <JOB_ID> --wait --download -o output/query
python3 query_job.py <JOB_ID> --type smart-topology --wait --download -o output/query
python3 query_job.py <JOB_ID> --type texture-edit --wait --download -o output/query
```

---

## Output files

- **Pro / Rapid / Smart Topology:** usually `.glb` (and sometimes `.zip` with textures).
- **Part / Texture Edit / Convert:** depends on task (e.g. FBX, OBJ, STL).

If Blender shows missing textures: **File → External Data → Find Missing Files…** and point to the folder with extracted assets.

---

## API coverage

For a list of **implemented vs remaining** Hunyuan APIs, see [API_COVERAGE.md](API_COVERAGE.md). Not yet implemented in this repo: UV job (Submit/Describe HunyuanTo3DUVJob), ChatCompletions, ChatTranslations.
