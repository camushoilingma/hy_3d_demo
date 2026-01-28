# hy-3d

Small CLI scripts for Tencent Cloud **Hunyuan 3D**:
- **Text → 3D**: submit a prompt, wait for completion, download model files
- **Image (2D) → 3D**: submit an image, wait for completion, download model files
- **Query**: query an existing JobId (optionally wait + download)
- **Smart Topology**: submit an existing 3D model for topology optimization (Polygen 1.5)

## Prerequisites

- Python 3
- Tencent Cloud SDK:

```bash
pip install tencentcloud-sdk-python
```

## Secrets / credentials setup (required)

These scripts load your credentials from a **local JSON file** (so you don’t hardcode keys in source).

**Secrets file lookup order (first found wins):**
1. `$HY3D_SECRETS_PATH` (explicit path)
2. `./secrets.json` (repo root, e.g. `$HOME/code/hy-3d/secrets.json`)
3. `~/.hy-3d-secrets.json` (user-level)

Create **one** of those files with this content (fill in your values):

```json
{
  "secret_id": "YOUR_SECRET_ID",
  "secret_key": "YOUR_SECRET_KEY",
  "region": "ap-singapore",
  "endpoint": "hunyuan.intl.tencentcloudapi.com"
}
```

Confirm it’s being ignored by git:
- `.gitignore` contains `secrets.json` and `~/.hy-3d-secrets.json`

## Usage

### Text → 3D (submit + wait + download)

```bash
python3 submit_txt_to_3d_job.py --prompt "a cute cartoon cat" --output ./hunyuan_output_txt
```

If you omit `--prompt`, the script will ask interactively.

Common options:
- `--faces 400000` (default: 400000)
- `--type Normal|LowPoly|Geometry|Sketch` (default: Normal)
- `--poll 10` (polling interval seconds)
- `--output ./some_dir`

### Image (2D) → 3D (submit + wait + download)

```bash
python3 submit_2d_to_3d.py ./photo.png --output ./hunyuan_output_img
```

Common options:
- `--faces 400000`
- `--type Normal|LowPoly|Geometry|Sketch`
- `--pbr` (enable PBR materials)
- `--polygon triangle|quad` (for LowPoly)
- `--left / --right / --back` (optional multi-view images)

### Query a JobId (optional wait + download)

```bash
python3 query_job.py <JOB_ID> --wait --download --output ./hunyuan_output_query
```

### Smart Topology (3D model retopology)

Submit a 3D model to Tencent Cloud Smart Topology (Polygen 1.5). You can use a public URL or a local file path.

```bash
# Remote URL
python3 submit_smart_topology.py https://example.com/model.glb -f low

# Local file
python3 submit_smart_topology.py ./hunyuan_output/my_model.glb --local -f medium
```

Common options:
- `-t, --file-type GLB|GLTF|OBJ|FBX|STL` (auto-detected if omitted)
- `-p, --polygon-type triangle|quadrilateral`
- `-f, --face-level high|medium|low`
- `--json` to print raw JSON response
- `--secrets /path/to/secrets.json` to override secrets path

## Output files and textures

You’ll often see both:
- `*.glb` (glTF binary): usually easiest to import into Blender (often includes materials/textures)
- `*.zip`: may contain additional formats + texture images

If Blender shows missing textures (pink):
- Blender → **File → External Data → Find Missing Files…**
- Select the folder where you extracted the `.zip` contents.

## Notes

- This repo currently targets **Hunyuan 3D** API actions:
  - `SubmitHunyuanTo3DProJob`
  - `QueryHunyuanTo3DProJob`
  - `Submit3DSmartTopologyJob`

- Example input assets are under:
  - `text_prompts_images/2d_images/` – example 2D images for image → 3D
  - `text_prompts_images/text_to_3d/` – example text prompts / assets for text → 3D

If you want **Text → Image** generation, we can add a separate script once you confirm the exact Tencent API action name you’re using for text-to-image.

