"""Build a Misha run bundle for a pan-ASLM acquisition without the Streamlit UI.

Usage (no shell wrappers, no UI):
    python make_misha_bundle.py \
        --dataset-name 3dtile_4x4x9520 \
        --raw-path /gpfs/marilyn/pi/kuan/shared/Allison/raw/3dtile_4x4x9520 \
        --z-slices 9520

That writes a bundle dir next to this script (YYMMDD_slurm_nr_<dataset_name>/)
containing run_nrstitcher.sbatch, convert.sbatch, stack_tiles.py,
convert_to_neuroglancer.py, tile_grid_viewer.py, stitch_settings.txt,
serve.py, and dataset_manifest.json.

Then on your side:
    1. Globus the bundle dir to /gpfs/marilyn/pi/kuan/shared/Allison/stitched/
    2. ssh misha → cd into it → sbatch run_nrstitcher.sbatch
    3. After it finishes: sbatch convert.sbatch

All pan-ASLM acquisition defaults (voxel size, overlap, tile px, scan order,
filename pattern) are baked in. Override via flags only if a future dataset
deviates. Slurm resource defaults are scaled off the proven 4x4x7200 stitch
(13 h wall on `day` partition, 200G mem, 32 cpus) — keep them in sync with
what nr_stitcher needs as datasets grow.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))

import core  # noqa: E402


# --- pan-ASLM acquisition defaults (override via flags if needed) -----------
PAN_ASLM = dict(
    n_tiles_x=4,
    n_tiles_y=4,
    n_channels=1,
    overlap_x=15,
    overlap_y=15,
    voxel_size_x_um=0.203125,
    voxel_size_y_um=0.203125,
    voxel_size_z_um=0.200,
    width_px=3200,
    height_px=3200,
    bit_depth=16,
    scan_order=core.ScanOrder.COL_SERPENTINE.value,
    channel_order=core.ChannelOrder.INTERLEAVED_PER_Z.value,
    prefix_filter="ss_single_",
)

# --- Slurm defaults, sized off the proven 7200 run --------------------------
SLURM_STITCH = dict(partition="day", cpus=32, mem="200G", time="24:00:00")
SLURM_CONVERT = dict(partition="day", cpus=8, mem="64G", time="06:00:00")

# --- Conda env / pi2 entrypoint on Misha (per misha_pi2_install memory) -----
CONDA_CONFIG = dict(
    env_name="pi2_env",
    entrypoint="/gpfs/radev/home/amc345/project/pi2/bin-linux64/release-nocl/nr_stitcher.py",
)


def synthesize_file_list(n_tiles: int, z_slices: int, n_channels: int, prefix: str) -> list[str]:
    """Build the [ss_single_NNNNNNN.tiff] list the bundle needs without touching the raw dir.

    pan-ASLM writes one file per (tile, z, channel) in linear acquisition order,
    1-indexed with 7-digit zero padding. stack_tiles.py maps linear index ->
    (tile, z, channel) the same way, so we just enumerate the count.
    """
    n_total = n_tiles * z_slices * n_channels
    return [f"{prefix}{i:07d}.tiff" for i in range(1, n_total + 1)]


def build_bundle(args: argparse.Namespace) -> Path:
    n_tiles = args.n_tiles_x * args.n_tiles_y
    files = synthesize_file_list(n_tiles, args.z_slices, args.n_channels, PAN_ASLM["prefix_filter"])

    manifest = core.DatasetManifest(
        dataset_name=args.dataset_name,
        n_tiles_x=args.n_tiles_x,
        n_tiles_y=args.n_tiles_y,
        z_slices=args.z_slices,
        n_channels=args.n_channels,
        overlap_x=PAN_ASLM["overlap_x"],
        overlap_y=PAN_ASLM["overlap_y"],
        voxel_size_x_um=PAN_ASLM["voxel_size_x_um"],
        voxel_size_y_um=PAN_ASLM["voxel_size_y_um"],
        voxel_size_z_um=PAN_ASLM["voxel_size_z_um"],
        scan_order=PAN_ASLM["scan_order"],
        channel_order=PAN_ASLM["channel_order"],
        width_px=PAN_ASLM["width_px"],
        height_px=PAN_ASLM["height_px"],
        bit_depth=PAN_ASLM["bit_depth"],
        prefix_filter=PAN_ASLM["prefix_filter"],
        files=files,
    )

    stamp = dt.date.today().strftime("%y%m%d")
    out_dir = Path(args.output_dir) if args.output_dir else REPO / f"{stamp}_slurm_nr_{args.dataset_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    slurm_stitch = {**SLURM_STITCH, "partition": args.partition or SLURM_STITCH["partition"],
                    "cpus": args.cpus or SLURM_STITCH["cpus"],
                    "mem": args.mem or SLURM_STITCH["mem"],
                    "time": args.time or SLURM_STITCH["time"]}

    print(f"[bundle] dataset:   {args.dataset_name}")
    print(f"[bundle] z slices:  {args.z_slices}")
    print(f"[bundle] tiles:     {args.n_tiles_x}x{args.n_tiles_y} = {n_tiles} ({len(files)} total files)")
    print(f"[bundle] raw path:  {args.raw_path}")
    print(f"[bundle] output:    {out_dir}")
    print(f"[bundle] stitch:    partition={slurm_stitch['partition']} cpus={slurm_stitch['cpus']} mem={slurm_stitch['mem']} time={slurm_stitch['time']}")
    print(f"[bundle] convert:   partition={SLURM_CONVERT['partition']} cpus={SLURM_CONVERT['cpus']} mem={SLURM_CONVERT['mem']} time={SLURM_CONVERT['time']}")
    print()

    core.generate_manifest(manifest, str(out_dir))
    core.generate_stack_script(manifest, str(out_dir), args.raw_path)
    core.generate_tile_grid_viewer(manifest, str(out_dir))
    core.generate_stitch_settings(manifest, str(out_dir), args.raw_path,
                                  use_tiles_view=False,
                                  stitch_output_format="raw",
                                  allow_warping=True,
                                  binning=1)
    core.generate_neuroglancer_converter(manifest, str(out_dir), binning=1)
    core.generate_slurm_script(manifest, slurm_stitch, CONDA_CONFIG, str(out_dir),
                               stage_to_tmp=False, run_stacking=True)
    core.generate_convert_slurm_script(manifest, SLURM_CONVERT, CONDA_CONFIG, str(out_dir),
                                       stage_to_tmp=False)

    return out_dir


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset-name", required=True, help="e.g. 3dtile_4x4x9520")
    p.add_argument("--raw-path", required=True, help="Absolute Misha path to the raw ss_single_*.tiff dir")
    p.add_argument("--z-slices", type=int, required=True, help="Number of z-slices per tile")
    p.add_argument("--n-tiles-x", type=int, default=PAN_ASLM["n_tiles_x"])
    p.add_argument("--n-tiles-y", type=int, default=PAN_ASLM["n_tiles_y"])
    p.add_argument("--n-channels", type=int, default=PAN_ASLM["n_channels"])
    p.add_argument("--output-dir", default=None, help="Default: ./YYMMDD_slurm_nr_<dataset>/")
    p.add_argument("--partition", default=None, help=f"Slurm partition for stitch (default {SLURM_STITCH['partition']})")
    p.add_argument("--cpus", type=int, default=None, help=f"CPUs per task for stitch (default {SLURM_STITCH['cpus']})")
    p.add_argument("--mem", default=None, help=f"Memory for stitch (default {SLURM_STITCH['mem']})")
    p.add_argument("--time", default=None, help=f"Walltime for stitch (default {SLURM_STITCH['time']})")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    out_dir = build_bundle(args)

    expected = [
        "dataset_manifest.json",
        "stack_tiles.py",
        "tile_grid_viewer.py",
        "stitch_settings.txt",
        "convert_to_neuroglancer.py",
        "run_nrstitcher.sbatch",
        "convert.sbatch",
    ]
    print("[bundle] files written:")
    for name in expected:
        path = out_dir / name
        marker = "OK" if path.exists() else "MISSING"
        size = f"{path.stat().st_size:,} B" if path.exists() else "-"
        print(f"  [{marker:>7}] {name}  ({size})")

    print()
    print(f"[bundle] done. Globus this dir to Misha and run:")
    print(f"  sbatch run_nrstitcher.sbatch    # stitch (~17 h for 9520)")
    print(f"  sbatch convert.sbatch            # raw -> precomputed + MIPs (~3-4 h)")
