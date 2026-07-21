"""Reconstructs the 349-image analytical cohort (150 Negative / 199 Positive)
used in this study from an independently downloaded copy of the public
Mendeley dataset.

This script does not ship, embed, cache, or require any original image pixel
data. It only reads images that the user has separately downloaded from
Mendeley Data (see ../README.md for the DOI and citation) and compares
cryptographic hashes against the manifests shipped in ../manifest/.

Pipeline (identical logic/thresholds to the study's internal
Claude_Runs/src/dataset_audit.py, minus the compute-heavy artifact audit,
which excluded zero additional images and is documented separately in
../manifest/ for provenance only):

    1. Discover images under <source-dir>/Negative/ and <source-dir>/Positive/.
    2. Hash every image (file SHA-256, decoded-pixel SHA-256, perceptual hash).
    3. Verify this matches the exact 366-image release used in the study.
    4. Remove exact pixel-content duplicates (16 groups -> 16 images removed).
    5. Remove verified perceptual near-duplicates (1 alternate copy removed).
    6. Compare the reconstructed 349-image cohort against the shipped
       manifest/cohort_manifest.csv and report PASS/FAIL.

Usage:
    python reconstruct_cohort.py --source-dir /path/to/mendeley_download
    python reconstruct_cohort.py --source-dir /path/to/mendeley_download --copy-cohort-to ./cohort
    python reconstruct_cohort.py --source-dir /path/to/mendeley_download --strict

Expected --source-dir layout (as distributed by Mendeley DOI 10.17632/zjhymwjtxv.3):
    <source-dir>/Negative/*.jpg   (157 images)
    <source-dir>/Positive/*.jpg   (209 images)
    <source-dir>/ImagesS/...      (auxiliary scale-bar copies; ignored, not used in modeling)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dataset_loader as dl  # noqa: E402
import duplicate_detection as dd  # noqa: E402
import near_duplicate_detection as ndd  # noqa: E402

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = PACKAGE_ROOT / "manifest"
CONFIG_PATH = PACKAGE_ROOT / "config" / "cohort_reconstruction_config.yaml"


def load_config() -> dict:
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


def verify_against_original_release(manifest: pd.DataFrame, cfg: dict, strict: bool) -> bool:
    """Compare freshly computed hashes against manifest/original_dataset_manifest.csv."""
    shipped = pd.read_csv(MANIFEST_DIR / "original_dataset_manifest.csv", dtype=str)
    ok = True

    exp = cfg["expected"]
    counts = manifest["class_label"].value_counts().to_dict()
    print(f"  discovered: {len(manifest)} total "
          f"(Negative={counts.get('Negative', 0)}, Positive={counts.get('Positive', 0)})")
    if len(manifest) != exp["n_original_total"]:
        print(f"  [WARN] expected {exp['n_original_total']} images in the original release, found {len(manifest)}.")
        ok = False

    shipped_ids = set(shipped["image_id"])
    found_ids = set(manifest["image_id"])
    missing = shipped_ids - found_ids
    extra = found_ids - shipped_ids
    if missing:
        print(f"  [WARN] {len(missing)} image_id(s) present in the study's original release are missing "
              f"from --source-dir, e.g. {sorted(missing)[:5]}")
        ok = False
    if extra:
        print(f"  [WARN] {len(extra)} image_id(s) in --source-dir were not part of the study's original "
              f"release, e.g. {sorted(extra)[:5]} (they will be ignored downstream since they do not "
              f"appear in manifest/cohort_manifest.csv either way).")

    shipped_by_id = shipped.set_index("image_id")
    pixel_mismatches, file_mismatches = [], []
    for _, row in manifest.iterrows():
        iid = row["image_id"]
        if iid not in shipped_by_id.index:
            continue
        ref = shipped_by_id.loc[iid]
        if row["pixel_content_sha256"] != ref["pixel_content_sha256"]:
            pixel_mismatches.append(iid)
        if row["file_sha256"] != ref["file_sha256"]:
            file_mismatches.append(iid)

    if pixel_mismatches:
        print(f"  [WARN] {len(pixel_mismatches)} image(s) have different DECODED PIXEL CONTENT than the "
              f"study's release (this changes cohort membership, not just file bytes): "
              f"{pixel_mismatches[:5]}")
        ok = False
    else:
        print("  decoded pixel content: MATCHES the study's original release for all shared image_ids.")

    if file_mismatches:
        level = "[WARN]" if not strict else "[FAIL]"
        print(f"  {level} {len(file_mismatches)} image(s) have different raw file bytes than the study's "
              f"release but IDENTICAL decoded pixel content (harmless re-encoding/re-save, e.g. different "
              f"JPEG compression pass): {file_mismatches[:5]}")
        if strict:
            ok = False
    else:
        print("  raw file bytes: MATCH the study's original release for all shared image_ids.")

    return ok


def reconstruct(manifest: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the same exact- and near-duplicate screening used in the study.

    Returns (final_cohort_manifest, excluded_exact, excluded_near).
    """
    print("  removing exact pixel-content duplicates ...")
    exact_report = dd.find_exact_duplicate_groups(manifest)
    retained_after_exact, excluded_exact = dd.apply_exclusions(manifest, exact_report)
    n_groups = exact_report["duplicate_group_id"].nunique() if not exact_report.empty else 0
    print(f"    {n_groups} exact-duplicate group(s); {len(excluded_exact)} image(s) removed; "
          f"{len(retained_after_exact)} retained.")

    print("  screening near-duplicates (perceptual hash) on retained images ...")
    ndc = cfg["near_duplicate"]
    near_report = ndd.screen_near_duplicates(
        retained_after_exact,
        hash_size=ndc["phash_hash_size"],
        candidate_threshold=ndc["hamming_threshold_candidate"],
        auto_exclude_threshold=ndc["hamming_threshold_auto_exclude"],
    )
    groups = ndd.build_related_groups(near_report)
    group_members: dict[str, list[str]] = {}
    for image_id, gid in groups.items():
        group_members.setdefault(gid, []).append(image_id)
    near_dup_excluded_ids = set()
    for gid, members in group_members.items():
        for m in sorted(members)[1:]:
            near_dup_excluded_ids.add(m)

    retained_after_near = retained_after_exact[~retained_after_exact["image_id"].isin(near_dup_excluded_ids)].copy()
    excluded_near = retained_after_exact[retained_after_exact["image_id"].isin(near_dup_excluded_ids)].copy()
    print(f"    {len(excluded_near)} verified near-duplicate alternate cop(y/ies) removed; "
          f"{len(retained_after_near)} retained.")

    final = retained_after_near.drop(columns=["_abs_path"], errors="ignore").reset_index(drop=True)
    return final, excluded_exact, excluded_near


def compare_to_shipped_cohort(final: pd.DataFrame, cfg: dict) -> bool:
    shipped = pd.read_csv(MANIFEST_DIR / "cohort_manifest.csv", dtype=str)
    shipped_ids = set(shipped["image_id"])
    got_ids = set(final["image_id"])

    exp = cfg["expected"]
    counts = final["class_label"].value_counts().to_dict()
    print(f"  reconstructed cohort: {len(final)} images "
          f"(Negative={counts.get('Negative', 0)}, Positive={counts.get('Positive', 0)})")
    print(f"  expected cohort:      {exp['n_cohort_total']} images "
          f"(Negative={exp['n_cohort_negative']}, Positive={exp['n_cohort_positive']})")

    ok = got_ids == shipped_ids
    if ok:
        print("  RESULT: PASS -- reconstructed cohort image_id set is IDENTICAL to manifest/cohort_manifest.csv.")
    else:
        missing = shipped_ids - got_ids
        extra = got_ids - shipped_ids
        print("  RESULT: FAIL -- reconstructed cohort does not match manifest/cohort_manifest.csv.")
        if missing:
            print(f"    missing from reconstruction ({len(missing)}): {sorted(missing)[:10]}")
        if extra:
            print(f"    unexpected in reconstruction ({len(extra)}): {sorted(extra)[:10]}")
    return ok


def copy_cohort(final: pd.DataFrame, source_dir: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for _, row in final.iterrows():
        src = source_dir / row["relative_source_path"]
        dst = dest_dir / row["relative_source_path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"  copied {len(final)} images to {dest_dir} (this is a local reorganization of your own "
          f"downloaded copy, not a redistribution).")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", required=True, help="Path to your local extracted Mendeley download "
                                                              "(must contain Negative/ and Positive/).")
    parser.add_argument("--copy-cohort-to", default=None, help="Optional: materialize the reconstructed "
                                                                 "349-image cohort into this directory "
                                                                 "(Negative/Positive structure preserved).")
    parser.add_argument("--strict", action="store_true", help="Also fail if raw file bytes differ from the "
                                                                "study's release, even when decoded pixel "
                                                                "content is identical (default: warn only).")
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        print(f"ERROR: --source-dir does not exist: {source_dir}")
        return 2

    cfg = load_config()

    print(f"Step 1/4: discovering images under {source_dir} ...")
    samples = dl.discover_samples(source_dir)
    auxiliary = dl.discover_auxiliary(source_dir)
    print(f"  found {len(samples)} modeling images (Negative/ + Positive/); "
          f"{len(auxiliary)} auxiliary ImagesS/ files (ignored, not used in modeling).")

    print("Step 2/4: hashing images and verifying against the study's original release manifest ...")
    manifest = dl.build_base_manifest(samples)
    manifest["_abs_path"] = [str(s.path) for s in samples]
    manifest["relative_source_path"] = [
        Path(s.path).resolve().relative_to(source_dir).as_posix() for s in samples
    ]
    phash_size = cfg["near_duplicate"]["phash_hash_size"]
    manifest["perceptual_hash"] = [
        "".join("1" if b else "0" for b in ndd.compute_phash(p, hash_size=phash_size)) for p in manifest["_abs_path"]
    ]
    release_ok = verify_against_original_release(manifest, cfg, strict=args.strict)

    print("Step 3/4: reconstructing the analytical cohort (exact- + near-duplicate removal) ...")
    final, excluded_exact, excluded_near = reconstruct(manifest, cfg)

    print("Step 4/4: comparing reconstructed cohort to the shipped cohort manifest ...")
    cohort_ok = compare_to_shipped_cohort(final, cfg)

    if args.copy_cohort_to:
        copy_cohort(final, source_dir, Path(args.copy_cohort_to).resolve())

    print()
    if release_ok and cohort_ok:
        print("SUCCESS: the 349-image analytical cohort (150 Negative / 199 Positive) was reconstructed "
              "and matches this study exactly.")
        return 0
    else:
        print("FAILED: see [WARN]/[FAIL] messages above. This usually means --source-dir is not the same "
              "Mendeley release version, or the download is incomplete/corrupted.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
