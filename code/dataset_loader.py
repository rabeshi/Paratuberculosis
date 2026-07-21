"""Dataset discovery and per-image manifest fields.

Standalone copy of ../../src/dataset_loader.py, kept logic-identical so the
hashes this script computes are directly comparable to the ones shipped in
../manifest/. See ../README.md for how this fits into cohort reconstruction.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}
CLASS_TO_LABEL = {"Negative": 0, "Positive": 1}
LABEL_TO_CLASS = {0: "Negative", 1: "Positive"}
AUXILIARY_DIR_NAME = "ImagesS"


@dataclass(frozen=True)
class Sample:
    image_id: str
    path: Path
    filename: str
    class_name: str
    label: int


def discover_samples(repo_root: str | Path) -> list[Sample]:
    """Enumerate modeling images from Negative/ and Positive/ only (ImagesS excluded)."""
    root = Path(repo_root)
    samples: list[Sample] = []
    for class_name, label in CLASS_TO_LABEL.items():
        class_dir = root / class_name
        if not class_dir.exists():
            raise FileNotFoundError(f"Expected directory not found: {class_dir}")
        for path in sorted(class_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                image_id = f"{class_name}/{path.name}"
                samples.append(Sample(image_id=image_id, path=path, filename=path.name, class_name=class_name, label=label))
    if not samples:
        raise RuntimeError(f"No images found under {root}/Negative and {root}/Positive")
    return samples


def discover_auxiliary(repo_root: str | Path) -> list[Path]:
    """Enumerate the ImagesS/ documentation copies (never used for modeling)."""
    root = Path(repo_root) / AUXILIARY_DIR_NAME
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rgb_array(path: str | Path) -> np.ndarray:
    with Image.open(path) as img:
        return np.array(img.convert("RGB"))


def pixel_content_hash(path: str | Path) -> str:
    """SHA-256 of the decoded RGB pixel buffer, independent of file container/metadata."""
    arr = load_rgb_array(path)
    digest = hashlib.sha256()
    digest.update(arr.shape[0].to_bytes(4, "little"))
    digest.update(arr.shape[1].to_bytes(4, "little"))
    digest.update(arr.tobytes())
    return digest.hexdigest()


def image_properties(path: str | Path) -> dict:
    p = Path(path)
    with Image.open(p) as img:
        width, height = img.size
        mode = img.mode
    return {
        "width": width,
        "height": height,
        "mode": mode,
        "file_extension": p.suffix.lower(),
        "file_size_bytes": p.stat().st_size,
    }


def build_base_manifest(samples: list[Sample]) -> pd.DataFrame:
    """Per-image identifier/path/label/dimension/hash fields (before duplicate/artifact status)."""
    rows = []
    for sample in samples:
        props = image_properties(sample.path)
        rows.append(
            {
                "image_id": sample.image_id,
                "filename": sample.filename,
                "relative_source_path": str(sample.path.as_posix()),
                "class_label": sample.class_name,
                "label": sample.label,
                "width": props["width"],
                "height": props["height"],
                "mode": props["mode"],
                "file_extension": props["file_extension"],
                "file_size_bytes": props["file_size_bytes"],
                "file_sha256": file_sha256(sample.path),
                "pixel_content_sha256": pixel_content_hash(sample.path),
            }
        )
    return pd.DataFrame(rows)
