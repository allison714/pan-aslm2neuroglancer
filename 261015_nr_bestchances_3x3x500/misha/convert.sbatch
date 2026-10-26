#!/bin/bash
#SBATCH --job-name=bestchances_convert
#SBATCH --partition=day
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=06:00:00
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

# Usage:  sbatch convert.sbatch 488     (or 560)
# Converts <ch>/bestchances_<ch>_..._XxYxZ.raw -> <ch>/precomputed (Neuroglancer)
CH="${1:?usage: sbatch convert.sbatch <488|560>}"
set -eo pipefail
cd "$SLURM_SUBMIT_DIR/$CH"
echo "Converting channel $CH in $(pwd)"; date

module load FFTW/3.3.10-GCC-13.3.0
module load libpng/1.6.43-GCCcore-13.3.0
module load LibTIFF/4.6.0-GCCcore-13.3.0
module load Blosc/1.21.6-GCCcore-13.3.0
set +e
source /gpfs/radev/apps/avx512/software/miniconda/24.3.0-miniforge/etc/profile.d/conda.sh
conda activate pi2_env
set -e
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"

ls bestchances_${CH}_0.0_0.0_0.0_*x*x*.raw >/dev/null || { echo "[ERROR] no stitched raw for $CH" >&2; exit 1; }
python convert_to_neuroglancer.py
echo "Done"; date
