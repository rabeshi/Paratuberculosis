"""Perceptual-hash near-duplicate screening.

Standalone copy of ../../src/near_duplicate_detection.py (logic-identical).
Implements a standard DCT-based pHash with OpenCV. Screens for resized,
recompressed, or brightness/contrast-adjusted copies and alternate versions
of the same underlying image field, without assuming morphologically-similar
but biologically distinct lesion images are duplicates.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def compute_phash(path: str | Path, hash_size: int = 16) -> np.ndarray:
    """64-bit-style DCT perceptual hash (returned as a boolean array of length hash_size**2 // 4)."""
    highfreq_factor = 4
    img_size = hash_size * highfreq_factor
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"Could not read image for pHash: {path}")
    resized = cv2.resize(image, (img_size, img_size), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(resized)
    dct_low = dct[:hash_size, :hash_size]
    med = np.median(dct_low[1:, 1:])  # exclude DC term from the threshold reference
    bits = (dct_low > med).flatten()
    return bits


def hamming_distance(a: np.ndarray, b: np.ndarray) -> int:
    return int(np.count_nonzero(a != b))


def screen_near_duplicates(
    manifest: pd.DataFrame,
    hash_size: int = 16,
    candidate_threshold: int = 12,
    auto_exclude_threshold: int = 4,
) -> pd.DataFrame:
    """All-pairs pHash screening within the retained (post-exact-dedup) manifest.

    Returns one row per candidate pair below `candidate_threshold`. Pairs below
    `auto_exclude_threshold` AND sharing the same class label are marked
    final_decision='auto_exclude_verified_alternate_copy'; everything else is
    'retain_flag_manual_review' so biologically distinct images are never
    dropped automatically.
    """
    hashes = {}
    dims = {}
    for _, row in manifest.iterrows():
        path = row["_abs_path"]
        hashes[row["image_id"]] = compute_phash(path, hash_size=hash_size)
        dims[row["image_id"]] = (row["width"], row["height"])

    labels = dict(zip(manifest["image_id"], manifest["class_label"]))
    ids = list(hashes.keys())
    rows = []
    for id_a, id_b in combinations(ids, 2):
        dist = hamming_distance(hashes[id_a], hashes[id_b])
        if dist > candidate_threshold:
            continue
        max_bits = hash_size * hash_size
        similarity = 1.0 - dist / max_bits
        same_label = labels[id_a] == labels[id_b]
        if dist <= auto_exclude_threshold and same_label:
            decision = "auto_exclude_verified_alternate_copy"
            rationale = f"Hamming distance {dist} <= auto-exclude threshold {auto_exclude_threshold} with matching class label."
        else:
            decision = "retain_flag_manual_review"
            rationale = (
                "Below candidate threshold but not below the conservative auto-exclude "
                "threshold, or class labels differ; retained pending manual review to "
                "avoid dropping biologically distinct images."
            )
        rows.append(
            {
                "image_a": id_a,
                "image_b": id_b,
                "class_a": labels[id_a],
                "class_b": labels[id_b],
                "phash_hamming_distance": dist,
                "similarity": round(similarity, 4),
                "dimensions_a": f"{dims[id_a][0]}x{dims[id_a][1]}",
                "dimensions_b": f"{dims[id_b][0]}x{dims[id_b][1]}",
                "review_status": "manual_review" if decision == "retain_flag_manual_review" else "auto_decided",
                "final_decision": decision,
                "decision_rationale": rationale,
            }
        )
    return pd.DataFrame(rows)


def build_related_groups(near_dup_report: pd.DataFrame) -> dict[str, str]:
    """Union-find over auto-excluded alternate-copy pairs -> {image_id: group_id} for fold grouping."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    verified = near_dup_report[near_dup_report["final_decision"] == "auto_exclude_verified_alternate_copy"]
    for _, row in verified.iterrows():
        union(row["image_a"], row["image_b"])

    return {node: find(node) for node in parent}
