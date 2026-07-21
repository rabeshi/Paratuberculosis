"""Integrity-checks the 349 images shipped in ../cohort_images/ against the
cryptographic hashes recorded in ../manifest/cohort_manifest.csv.

Use this to confirm your local copy of this package (e.g. after unzipping a
supplementary-materials download, or cloning the repo) has not been altered,
truncated, or corrupted, without needing to re-download anything from
Mendeley. To verify the *selection* of these 349 images was reproducibly
derived from the original 366-image Mendeley release, use
reconstruct_cohort.py instead (requires a separate download from Mendeley).

Usage:
    python verify_shipped_cohort.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dataset_loader as dl  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
COHORT_DIR = PACKAGE_ROOT / "cohort_images"
MANIFEST_PATH = PACKAGE_ROOT / "manifest" / "cohort_manifest.csv"


def main() -> int:
    manifest = pd.read_csv(MANIFEST_PATH, dtype=str).set_index("image_id")
    print(f"Checking {len(manifest)} images listed in {MANIFEST_PATH.relative_to(PACKAGE_ROOT)} "
          f"against {COHORT_DIR.relative_to(PACKAGE_ROOT)} ...")

    missing, pixel_mismatch, file_mismatch, ok_count = [], [], [], 0
    for image_id, ref in manifest.iterrows():
        path = COHORT_DIR / image_id
        if not path.exists():
            missing.append(image_id)
            continue
        pixel_hash = dl.pixel_content_hash(path)
        file_hash = dl.file_sha256(path)
        if pixel_hash != ref["pixel_content_sha256"]:
            pixel_mismatch.append(image_id)
        elif file_hash != ref["file_sha256"]:
            file_mismatch.append(image_id)
        else:
            ok_count += 1

    print(f"  OK (file + pixel hash match): {ok_count}")
    if file_mismatch:
        print(f"  [WARN] pixel content matches but raw file bytes differ (harmless re-save): {len(file_mismatch)} "
              f"-> {file_mismatch[:5]}")
    if pixel_mismatch:
        print(f"  [FAIL] decoded pixel content differs from the manifest: {len(pixel_mismatch)} -> {pixel_mismatch[:5]}")
    if missing:
        print(f"  [FAIL] listed in manifest but not found under cohort_images/: {len(missing)} -> {missing[:5]}")

    extra = sorted(set(p.relative_to(COHORT_DIR).as_posix() for p in COHORT_DIR.rglob("*") if p.is_file())
                    - set(manifest.index))
    if extra:
        print(f"  [WARN] files present under cohort_images/ but not listed in the manifest: {len(extra)} -> {extra[:5]}")

    success = not missing and not pixel_mismatch
    print()
    if success:
        print(f"SUCCESS: all {len(manifest)} images verified against the manifest "
              f"(150 Negative / 199 Positive expected).")
    else:
        print("FAILED: see [FAIL] messages above -- this package's cohort_images/ does not match its own manifest.")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
