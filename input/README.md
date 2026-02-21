# Input files

Place assets here for the CLI scripts and the test runner.

| Directory   | Use for |
|------------|---------|
| `images/`  | 2D images for **Image → 3D** (Pro, Rapid) and texture reference (Texture Edit). JPG, PNG, WEBP; ≤6 MB recommended. Example: `bose.png`, `chair_selency.webp`, `electro-box.png`, `table-selency.webp`. |
| `models/`  | 3D models for **Part job** (FBX, ≤30k faces, ≤100 MB), **Smart Topology** (GLB/OBJ/FBX/STL), **Texture Edit** (FBX, <100k faces), **Convert** (GLB/OBJ/FBX, ≤60 MB). |
| `prompts/` | Example text prompts for **Text → 3D** (Pro, Rapid). One prompt per line or file; use with `submit_txt_to_3d_job.py -p "$(cat input/prompts/leopard_airpods.txt)"`. Example: `leopard_airpods.txt`. |

Scripts accept paths anywhere; these folders are the default location used by the test script and by the README examples.
