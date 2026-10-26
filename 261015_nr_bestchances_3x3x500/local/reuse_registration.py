#!/usr/bin/env python3
"""Reuse a finished nr_stitcher registration (pairwise displacement fields) for a second channel.

nr_stitcher caches the expensive pairwise block-matching results as
    <sample_name>_<i>-<j>_{refpoints,refpoints_settings,filtered_refpoints,
                           filtered_refpoints_settings}.txt
    <sample_name>_<i>-<j>_{defpoints,filtered_defpoints,gof,filtered_gof}_AxBxC.raw
keyed only by sample_name and tile index pair.  It also compares
<sample_name>_position_settings.txt against the [positions] section and, if that
file is missing or differs, recomputes *everything*.

This script copies the cached pair files from SRC sample to DST sample and writes a
DST position_settings file whose file names come from the DST stitch settings and
whose positions/sizes come from the SRC run.  nr_stitcher then skips block
matching for DST and only re-runs the (cheap) global optimisation + mosaic, so the
second channel gets exactly the same geometry as the first.

Usage (run from the directory where the SRC outputs live, which is also where
nr_stitcher will be run for DST):
    python reuse_registration.py --src-sample <SRC> --dst-settings <dst_stitch_settings.txt> [--src-dir DIR]
"""
import argparse
import configparser
import glob
import os
import re
import shutil
import sys


def positions_from_settings(path):
    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    cfg.read(path)
    if "positions" not in cfg:
        sys.exit(f"[reuse] no [positions] section in {path}")
    sample = cfg["stitch"].get("sample_name", "sample").strip()
    binning = int(cfg["stitch"].get("binning", "1"))
    if binning != 1:
        sample = f"bin{binning}_{sample}"
    return sample, [k for k, _ in cfg.items("positions")]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src-sample", required=True, help="sample_name of the finished run (e.g. Allison_bestchances_images_multichan)")
    ap.add_argument("--dst-settings", required=True, help="stitch_settings.txt that will be used for the new channel")
    ap.add_argument("--src-dir", default=".", help="directory holding the SRC run outputs (default: cwd)")
    ap.add_argument("--dst-dir", default=".", help="directory where the DST run will execute (default: cwd)")
    args = ap.parse_args()

    src, dst_dir, src_dir = args.src_sample, os.path.abspath(args.dst_dir), os.path.abspath(args.src_dir)
    dst, dst_files = positions_from_settings(args.dst_settings)
    if dst == src and dst_dir == src_dir:
        sys.exit("[reuse] DST sample_name equals SRC sample_name in the same directory; give the new channel its own sample_name.")

    # 1. position settings: SRC positions/sizes, DST file names (same order)
    src_pos = os.path.join(src_dir, f"{src}_position_settings.txt")
    if not os.path.isfile(src_pos):
        sys.exit(f"[reuse] missing {src_pos}; was the SRC run completed in {src_dir}?")
    with open(src_pos) as f:
        src_lines = [l.rstrip("\n") for l in f if l.strip()]
    if len(src_lines) != len(dst_files):
        sys.exit(f"[reuse] SRC has {len(src_lines)} tiles but DST settings list {len(dst_files)}")
    out_lines = []
    for fname, line in zip(dst_files, src_lines):
        m = re.match(r"^(.*?) at position (.*)$", line)
        if not m:
            sys.exit(f"[reuse] cannot parse position line: {line}")
        out_lines.append(f"{fname} at position {m.group(2)}")
    os.makedirs(dst_dir, exist_ok=True)
    with open(os.path.join(dst_dir, f"{dst}_position_settings.txt"), "w") as f:
        f.write("\n".join(out_lines) + "\n")
    print(f"[reuse] wrote {dst}_position_settings.txt ({len(out_lines)} tiles)")

    # 2. pairwise displacement caches
    pat = re.compile(rf"^{re.escape(src)}_(\d+)-(\d+)_(.+)$")
    n = 0
    for path in glob.glob(os.path.join(src_dir, f"{src}_*-*_*")):
        base = os.path.basename(path)
        m = pat.match(base)
        if not m:
            continue
        target = os.path.join(dst_dir, f"{dst}_{m.group(1)}-{m.group(2)}_{m.group(3)}")
        if os.path.isfile(target) and os.path.getsize(target) == os.path.getsize(path):
            continue
        shutil.copy2(path, target)
        n += 1
    pairs = {tuple(pat.match(os.path.basename(p)).groups()[:2]) for p in glob.glob(os.path.join(src_dir, f"{src}_*-*_*")) if pat.match(os.path.basename(p))}
    if not pairs:
        sys.exit(f"[reuse] no pairwise files named {src}_<i>-<j>_* found in {src_dir}")
    print(f"[reuse] copied {n} files covering {len(pairs)} tile pairs -> prefix {dst}")
    print("[reuse] done. nr_stitcher will skip block matching for", dst)


if __name__ == "__main__":
    main()
