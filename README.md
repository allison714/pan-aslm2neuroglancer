# panaslm2neuroglancer — Run Bundle Generator

A Streamlit GUI that generates ready-to-execute **Run Bundles** for stitching large pan-ASLM light-sheet datasets using [pi2/NRStitcher](https://github.com/arttumiettinen/pi2).

Supports both **local workstations** (Windows / Mac / Linux) and the **Misha HPC Cluster** (Yale YCRC Slurm).

---

## Features

| Feature | Description |
|---|---|
| **Interactive Configuration** | Input dataset parameters (dimensions, overlap, voxel size, scan order) via a GUI |
| **Remote-Safe Validation** | Validates local datasets while gracefully bypassing checks for remote Misha paths |
| **Misha Cluster Optimization** | Generates Slurm `sbatch` scripts with correct `module load`, OpenMP thread pinning, and `ldd` pre-flight validation |
| **YCRC Resource Estimation** | Recommends CPU, memory, partition and time based on dataset size; warns when memory < 120GB |
| **Staging to `/tmp`** | Optionally stages data to local node `/tmp` for maximum I/O throughput (recommended by YCRC) |
| **Tiles View** | Creates a `tiles/` folder with symlinks renaming files to `tile_{t}_z_{z}_c_{c}.tif` without duplicating data |
| **QC Analytics** | Post-stitch warping diagnostics, intensity drift analysis, and gain correction tools |
| **Preview** | Visually inspect tile grid coordinate mapping before committing |

---

## Quick Start

### 1. Clone the Repo

```bash
git clone https://github.com/kuan-lab/panaslm2neuroglancer.git
cd panaslm2neuroglancer
```

### 2. Launch the App

**Windows (Easiest)**
```
Double-click RUN_ME.bat
```
This auto-creates the `stitch_app` conda environment, installs dependencies, and opens the browser UI.

**Mac / Linux (Manual)**
```bash
conda create -n stitch_app python=3.9 -y
conda activate stitch_app
pip install -r requirements.txt
streamlit run app.py
```

---

## Workflow

### For Misha HPC (Recommended for large datasets > 100GB)

This is the **offline configuration** model: generate the bundle locally, upload to Misha, and let the cluster do the heavy lifting.

```
[Local PC]                              [Misha HPC]
  Streamlit App          Globus             sbatch
  ─────────────   ─────────────────►   ─────────────►
  Generate Bundle      Transfer              Stitch
  (lightweight)      bundle folder        2.2TB output
```

**Step-by-step:**

1. Open the app and select **"Misha Cluster (Slurm)"** as the Target Environment.
2. Set paths to your data (Misha paths like `/gpfs/...` are accepted — local validation is skipped automatically).
3. Configure Slurm resources (CPU, memory, partition). The app will recommend values based on your dataset size.
4. Click **"Generate Run Bundle"**.
5. Find the output folder (named `YYMMDD_slurm_nr_<dataset>`) on your local machine.
6. Transfer it to Misha using [Globus](https://app.globus.org) → drop it in your target output directory on `/gpfs/...`.
7. SSH into Misha:
   ```bash
   cd /path/to/your/transferred/bundle
   sbatch run_nrstitcher.sbatch
   ```
8. Monitor progress:
   ```bash
   squeue -u <netid>           # Check job status (PD → R → done)
   jobstats <JOBID>            # Live CPU/memory usage
   tail -f *.out               # Live log output
   seff <JOBID>                # Efficiency summary after completion
   ```

**Key paths for Misha (Yale WTI):**

| Path | Purpose |
|---|---|
| `/gpfs/radev/scratch/kuan/amc345/raw/` | Raw input data (fast scratch) |
| `/gpfs/marilyn/pi/kuan/shared/Allison/` | Output for stitched results (shared storage) |
| `/gpfs/radev/scratch/kuan/amc345/panaslm2neuroglancer/pi2-4.5-linux/` | pi2 binary on Misha |

---

### For Local Workstations

1. Select **"Local Workstation"** as Target Environment.
2. Point the app to your local `pi2` binaries (auto-detected from `D:\pi2-v4.5-win-no-opencl` or `resources/pi2`).
3. Click **"Generate Run Bundle"**.
4. Navigate to the output folder and run:
   - **Windows**: double-click `run_local.bat`
   - **Linux/Mac**: `./run_local.sh`

---

## Output Bundle Contents

| File | Description |
|---|---|
| `stitch_settings.txt` | pi2/NRStitcher tile coordinate configuration |
| `dataset_manifest.json` | Full parameter record for reproducibility |
| `run_nrstitcher.sbatch` | Slurm job submission script (Misha) |
| `run_local.bat` / `run_local.sh` | Local execution scripts (Windows/Mac/Linux) |
| `stack_tiles.py` | Pre-processing: stacks 2D z-slices into 3D tile volumes |
| `convert_to_neuroglancer.py` | Post-processing: converts output to Neuroglancer Precomputed |
| `serve.py` | Local web server for Neuroglancer visualization |

---

## Neuroglancer Visualization

After stitching completes, view the 3D volume in your browser:

```bash
# From within the bundle folder (with output present)
python serve.py
```

Then open [neuroglancer-demo.appspot.com](https://neuroglancer-demo.appspot.com/) and add:
```
precomputed://http://localhost:8000/precomputed
```

---

## Misha Slurm Script Details

The generated `run_nrstitcher.sbatch` includes:

```bash
# Loads required modules
module load miniconda/24.3.0
module load FFTW/3.3.10-GCC-13.3.0
module load libpng/1.6.43-GCCcore-13.3.0
module load LibTIFF/4.6.0-GCCcore-13.3.0
module load Blosc/1.21.6-GCCcore-13.3.0

# Pins OpenMP threads to allocated CPUs (prevents oversubscription)
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

# Optional: stage to local /tmp for faster I/O (recommended by YCRC)
rsync -a . $SCRATCH && cd $SCRATCH
```

---

## Troubleshooting

**"Generate Run Bundle" button is greyed out (Misha mode)**
→ Expected. The app skips local file validation when Misha Cluster is selected. Make sure the Execution Configuration expander is open and `Misha Cluster (Slurm)` is selected.

**"str object has no attribute 'get'"**
→ This was caused by a duplicate `generate_slurm_script` definition in `core.py` that had swapped parameter order. Fixed in current version.

**"generate_slurm_script() got an unexpected keyword argument 'stage_to_tmp'"**
→ Caused by Python loading a stale cached module. Fixed by forcing `importlib.reload(core)` at call time.

**"Conda not found"**
→ Open the app → Backend Configuration → update the "Conda Init Script" to your actual `conda.sh` path.

**"ldd not found" pre-flight errors on Misha**
→ The pre-flight now correctly runs `ldd` on the `pi2` ELF binary, not the `.py` script.

---

## Project Structure

```
panaslm2neuroglancer/
├── app.py                    # Main Streamlit application
├── src/
│   └── core.py               # Bundle generation logic (stitch settings, Slurm, local scripts)
├── RUN_ME.bat                # Windows one-click launcher
├── requirements.txt          # Python dependencies
├── pi2-4.5-linux/            # pi2 Linux binary (for Misha use)
└── pi2-v4.5-win-no-opencl/   # pi2 Windows binary (for local use)
```

---

*A. Cairns || 2026 — Kuan × Bewersdorf Labs, Yale University*
