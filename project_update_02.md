# Project Update 02: Misha SLURM Optimization

In this update, we extended the Run Bundle Generator to natively support the Misha HPC Cluster via proper SLURM batch file generation.

## Key Changes Implementation:

1. **Conda Auto-Initialization**
   * The Streamlit UI specifically targets Misha's non-standard Conda module path (`/gpfs/radev/apps/avx512/software/miniconda/24.3.0-miniforge`).
   * This ensures the job script safely activates the correct Python environment before executing the CLI workflow.

2. **System Dependencies Extraction (`module load`)**
   * The Misha `pi2` binary compilation depends directly on environment modules for dynamically linked `.so` libraries.
   * `run_nrstitcher.sbatch` now automatically prepends the exact modules required to prevent immediate segmentation faults (`FFTW`, `libpng`, `LibTIFF`, `Blosc`).

3. **Performance Tweaks**
   * Added `export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK` to align the underlying C++ multi-threading with the specific SLURM core allocation bounds.
   * Added UI warnings when `Memory` drops below 120GB, as `pi2` drastically shrinks its internal caching arrays (which heavily degrades cross-correlation speed).

4. **Reliability and Pre-Flight Checks**
   * Added an inline `ldd` scan during the SLURM submission to verify `.so` library resolution.
   * Added a `pi2 help` invocation wrapper to ensure the software engine actually triggers before attempting the massive dataset loads.

*Note: The Local Workstation fallback configuration logic remains fully intact and functional. The backend target depends on the user's selection in the Execution Configuration panel.*
