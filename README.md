# hy-3d

Small CLI scripts for Tencent Cloud **Hunyuan 3D**:
- **Text → 3D**: submit a prompt, wait for completion, download model files
- **Image (2D) → 3D**: submit an image, wait for completion, download model files
- **Query**: query an existing JobId (optionally wait + download)

## Prerequisites

- Python 3
- Tencent Cloud SDK:

```bash
pip install tencentcloud-sdk-python
```

## Secrets / credentials setup (required)

These scripts load your credentials from a **local JSON file** (so you don’t hardcode keys in source).

### Option A (recommended): repo-local `secrets.json`

1. Create a new file at:
   - `/Users/camusma/code/hy-3d/secrets.json`

2. Paste this and fill in your values:

```json
{
  "secret_id": "YOUR_SECRET_ID",
  "secret_key": "YOUR_SECRET_KEY",
  "region": "ap-singapore",
  "endpoint": "hunyuan.intl.tencentcloudapi.com"
}
```

3. Confirm it’s being ignored by git:
   - `.gitignore` contains `secrets.json` and `~/.hy-3d-secrets.json`

### Option B: user-level secrets file

Create this file instead:
- `~/.hy-3d-secrets.json`

Same JSON format as above.

### Option C: specify a secrets path explicitly

Set an environment variable:

```bash
export HY3D_SECRETS_PATH="/absolute/path/to/my-secrets.json"
```

The lookup order is:
1. `$HY3D_SECRETS_PATH`
2. `./secrets.json` (repo root)
3. `~/.hy-3d-secrets.json`

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

If you want **Text → Image** generation, we can add a separate script once you confirm the exact Tencent API action name you’re using for text-to-image.

