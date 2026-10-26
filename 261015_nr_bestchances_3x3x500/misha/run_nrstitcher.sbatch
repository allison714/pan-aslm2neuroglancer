#!/bin/bash
#SBATCH --job-name=bestchances_3x3x500_stitch
#SBATCH --partition=day
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=200G
#SBATCH --time=12:00:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

# Stitches channel 488 (full registration), then channel 560 reusing the 488
# registration so both channels share one geometry.  Pre-stacked 3D TIFF tiles
# are read directly by nr_stitcher; no stack_tiles.py step is needed.
#
# EDIT THIS to the Misha directory holding Zstack0000N{488,560}.tif:
RAW_DIR="/gpfs/radev/scratch/kuan/amc345/raw/Allison_bestchances_3x3x500"

set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
echo "Starting stitching job in $(pwd)"; date

module load FFTW/3.3.10-GCC-13.3.0
module load libpng/1.6.43-GCCcore-13.3.0
module load LibTIFF/4.6.0-GCCcore-13.3.0
module load Blosc/1.21.6-GCCcore-13.3.0

set +e
source /gpfs/radev/apps/avx512/software/miniconda/24.3.0-miniforge/etc/profile.d/conda.sh
conda activate pi2_env
set -e
EXPECTED_PYTHON="${CONDA_PREFIX:-}/bin/python"
ACTUAL_PYTHON="$(command -v python || true)"
if [ -z "${CONDA_PREFIX:-}" ] || [ "$ACTUAL_PYTHON" != "$EXPECTED_PYTHON" ]; then
    echo "[ERROR] conda env did not activate cleanly (python at '$ACTUAL_PYTHON')." >&2
    exit 1
fi
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"

NR_STITCHER="/gpfs/radev/home/amc345/project/pi2/bin-linux64/release-nocl/nr_stitcher.py"
[ -f "$NR_STITCHER" ] || { echo "[ERROR] $NR_STITCHER not found" >&2; exit 1; }

# --- raw data check + per-channel raw/ symlinks the settings files point at ---
for t in 0 1 2 3 4 5 6 7 8; do
    for ch in 488 560; do
        f="$RAW_DIR/Zstack0000${t}${ch}.tif"
        [ -f "$f" ] || { echo "[ERROR] missing tile $f" >&2; exit 1; }
    done
done
ln -sfn "$RAW_DIR" 488/raw
ln -sfn "$RAW_DIR" 560/raw
echo "488/raw, 560/raw -> $RAW_DIR (18 tiles present)"

# --- channel 488: full registration + mosaic ---
echo "=== 488: nr_stitcher"; date
( cd 488 && python "$NR_STITCHER" stitch_settings.txt )
ls -la 488/bestchances_488_0.0_0.0_0.0_*x*x*.raw
echo "=== 488 done"; date

# --- channel 560: reuse 488 displacement fields, re-run optimisation + mosaic ---
echo "=== 560: reuse registration"; date
python reuse_registration.py --src-sample bestchances_488 --src-dir 488 \
       --dst-settings 560/stitch_settings.txt --dst-dir 560
echo "=== 560: nr_stitcher"; date
( cd 560 && python "$NR_STITCHER" stitch_settings.txt )
ls -la 560/bestchances_560_0.0_0.0_0.0_*x*x*.raw
echo "=== 560 done"; date

echo "Done. Next: sbatch convert.sbatch 488 ; sbatch convert.sbatch 560"
# jobstats $SLURM_JOB_ID   /   seff $SLURM_JOB_ID
