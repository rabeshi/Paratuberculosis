"""Exact-duplicate detection using decoded pixel-content hashes.

Standalone copy of ../../src/duplicate_detection.py (logic-identical). Groups
images by pixel_content_sha256 (dataset_loader.pixel_content_hash), which
catches images that are byte-identical after re-encoding/re-saving, not just
files with matching raw bytes. Any duplicate group spanning conflicting class
labels is flagged for manual review and excluded from modeling rather than
silently resolved.
"""
from __future__ import annotations

import pandas as pd


def find_exact_duplicate_groups(manifest: pd.DataFrame) -> pd.DataFrame:
    """Group images by pixel_content_sha256; assign a duplicate_group_id to any group with >1 member."""
    groups = manifest.groupby("pixel_content_sha256")
    rows = []
    group_id = 0
    for pixel_hash, group in groups:
        if len(group) <= 1:
            continue
        group_id += 1
        labels = sorted(group["label"].unique().tolist())
        label_conflict = len(labels) > 1
        retained = group.sort_values("image_id").iloc[0]
        for _, row in group.iterrows():
            rows.append(
                {
                    "duplicate_group_id": group_id,
                    "image_id": row["image_id"],
                    "filename": row["filename"],
                    "class_label": row["class_label"],
                    "label": row["label"],
                    "file_sha256": row["file_sha256"],
                    "pixel_content_sha256": pixel_hash,
                    "width": row["width"],
                    "height": row["height"],
                    "label_conflict": label_conflict,
                    "retained_image_id": None if label_conflict else retained["image_id"],
                    "excluded_image_id": None if (label_conflict or row["image_id"] == retained["image_id"]) else row["image_id"],
                    "exclusion_reason": (
                        "label_conflict_manual_review_required" if label_conflict
                        else ("exact_pixel_duplicate" if row["image_id"] != retained["image_id"] else "retained_representative")
                    ),
                }
            )
    return pd.DataFrame(rows)


def apply_exclusions(manifest: pd.DataFrame, duplicate_report: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (retained_manifest, excluded_images) after applying exact-duplicate exclusions."""
    if duplicate_report.empty:
        excluded = pd.DataFrame(columns=["image_id", "class_label", "label", "exclusion_reason", "duplicate_group_id"])
        manifest = manifest.copy()
        manifest["inclusion_status"] = "included"
        return manifest, excluded

    excluded_ids = duplicate_report.loc[
        duplicate_report["exclusion_reason"].isin(["exact_pixel_duplicate", "label_conflict_manual_review_required"]),
        "image_id",
    ].unique()

    manifest = manifest.copy()
    manifest["inclusion_status"] = manifest["image_id"].apply(
        lambda iid: "excluded_exact_duplicate" if iid in set(excluded_ids) else "included"
    )
    # Label conflicts exclude the *entire* group, including the would-be representative.
    conflict_groups = duplicate_report.loc[duplicate_report["label_conflict"], "duplicate_group_id"].unique()
    if len(conflict_groups):
        conflict_ids = duplicate_report.loc[duplicate_report["duplicate_group_id"].isin(conflict_groups), "image_id"].unique()
        manifest.loc[manifest["image_id"].isin(conflict_ids), "inclusion_status"] = "excluded_label_conflict_manual_review"

    excluded = duplicate_report[duplicate_report["exclusion_reason"] != "retained_representative"][
        ["image_id", "class_label", "label", "exclusion_reason", "duplicate_group_id"]
    ].reset_index(drop=True)

    retained = manifest[manifest["inclusion_status"] == "included"].reset_index(drop=True)
    return retained, excluded
