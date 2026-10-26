# bestchances 3x3x500 — two-channel nr_stitcher run

Dataset: `F:\Sept 2026\pan-ASLM\Allison_bestchances_images_multichannel_multitiling\RAW`
18 pre-stacked 3D TIFFs (`Zstack0000<t><ch>.tif`, t = 0..8, ch = 488 / 560), 3200 x 3200 x 500 px, 10.2 GB each.
Grid: 3 x 3, column-serpentine, 2720 px pitch (15 % overlap). No re-slicing into 2D tiles is needed:
nr_stitcher reads 3D tiles directly (the `stack_tiles.py` step in the pipeline only exists because
pan-ASLM normally saves one 2D TIFF per z).

State on 2026-10-15:
- Channel 488 was already stitched locally on 2026-10-13 in the dataset folder
  (`Allison_bestchances_images_multichan_0.0_0.0_0.0_8641x8641x502.raw`, 75 GB, warped, rotation on).
- Channel 560 has not been stitched. `local/` is already prepared for it (see below).

## How the second channel reuses the first channel's registration

nr_stitcher caches the expensive pairwise block matching as `<sample>_<i>-<j>_*` files and
only recomputes them if `<sample>_position_settings.txt` disagrees with the `[positions]` section.
`reuse_registration.py` copies those caches under a new sample name and writes a matching
position file with the 560 file names. nr_stitcher then skips block matching and just redoes the
global optimisation and mosaic. The optimiser is not bit-for-bit deterministic: on 2026-10-15 the 560
tile transforms matched 488 to within 0.15 px, and the 560 volume came out 8641x8642x501 vs 8641x8641x502
for 488. Crop both to the common 8641x8641x501 before voxel-wise colocalisation.

Because the cached files also carry 488 intensity-normalisation factors, the 560 settings use
`normalize_while_stitching = False`. If 560 tile seams look uneven, use
`local/stitch_settings_560_independent.txt` instead (own registration, own normalisation,
geometry may differ by a sub-pixel amount; about 1 h extra locally).

## Option A — local (recommended for this dataset)

The 488 full-res run took about 3.5 h on this workstation; 560 with reuse took 5.1 h (2026-10-15).
`reuse_registration.py` has already been run, so the 560 caches and position file are in place.

```
261015_nr_bestchances_3x3x500\local\run_560_local.bat
```

It activates conda env `stitch_app`, changes into the dataset folder, re-runs the (idempotent) reuse
step and launches `pi2-v4.5-win-no-opencl\nr_stitcher.py stitch_settings_560.txt`.
Output: `Allison_bestchances_images_multichan_560_0.0_0.0_0.0_<X>x<Y>x<Z>.raw` next to the 488 one.

Converting locally to Neuroglancer precomputed: the generated converter picks the largest
`*_XxYxZ.raw` in its working directory, so move each channel's raw into its own folder
(`488/`, `560/`) and run `misha/<ch>/convert_to_neuroglancer.py` from inside that folder
(needs `pip install tensorstore`, optionally cloud-volume for the MIP pyramid).

## Option B — Misha (Slurm)

Use this when the workstation is busy or for the larger 4x4 x 7200–9520 datasets. Overhead here is
the 172 GB raw upload.

1. Globus: transfer the `RAW` folder to Misha, e.g.
   `/gpfs/radev/scratch/kuan/amc345/raw/Allison_bestchances_3x3x500/` (18 TIFFs + 2 logs).
2. Globus or OnDemand: upload the `misha/` folder to your run location, e.g.
   `/gpfs/marilyn/pi/kuan/shared/Allison/stitched/261015_bestchances_3x3x500/`.
3. Edit `RAW_DIR=` at the top of `run_nrstitcher.sbatch` if you used a different raw path.
4. Submit:
   ```bash
   ssh <netid>@misha.ycrc.yale.edu
   cd /gpfs/marilyn/pi/kuan/shared/Allison/stitched/261015_bestchances_3x3x500
   sbatch run_nrstitcher.sbatch          # 488 full registration, then 560 reusing it; 12 h limit
   squeue -u $USER ; tail -f bestchances_3x3x500_stitch_*.out
   ```
   Resources: `day` partition, 32 CPU, 200 GB, 12 h (sized off the proven 4x4x7200 run; this
   dataset is about 7x smaller, expect well under 6 h).
5. After it finishes (`seff <jobid>` to check), convert each channel:
   ```bash
   sbatch convert.sbatch 488
   sbatch convert.sbatch 560
   ```
   Outputs: `488/precomputed/` and `560/precomputed/`.
6. Publish: Globus `488/precomputed` to nginx as `.../<dataset>/chan0/` and `560/precomputed`
   as `.../<dataset>/chan1/` (lab convention, see the neuroglancer hosting notes).

Files in `misha/`:
- `run_nrstitcher.sbatch`, `convert.sbatch`, `reuse_registration.py`
- `488/stitch_settings.txt`, `560/stitch_settings.txt` — positions point at `raw/Zstack...tif`
  (the sbatch creates `488/raw` and `560/raw` symlinks to `RAW_DIR`)
- `<ch>/convert_to_neuroglancer.py`, `<ch>/dataset_manifest.json`, `<ch>/serve.py`

Voxel size in the converters is the pan-ASLM default (0.203 x 0.203 x 0.200 um); the acquisition
log in RAW does not record it, so correct `VOXEL_*_NM` in the converter if this run differed.
