# Reproducibility Package: Histopathological Classification of Paratuberculosis

Everything needed to obtain, verify, and (if desired) regenerate the exact
349-image analytical cohort (199 MAP-positive, 150 MAP-negative) used in this
study, derived from the publicly available Mendeley dataset described below.

This folder is self-contained and contains the full modeling pipeline —
Swin-Tiny/GLCM/XGBoost training, statistics, figures — not needed just to
reconstruct the cohort).

## What's in here

```
reproducibility_package/
├── README.md                  — this file
├── ATTRIBUTION.md             — required CC BY 4.0 attribution for the original dataset
├── requirements.txt           — minimal deps (no torch/xgboost needed)
├── config/
│   └── cohort_reconstruction_config.yaml   — thresholds used for de-duplication
├── code/
│   ├── dataset_loader.py            — discovery + hashing (file SHA-256, decoded-pixel SHA-256, pHash)
│   ├── duplicate_detection.py       — exact pixel-content duplicate removal
│   ├── near_duplicate_detection.py  — perceptual-hash near-duplicate removal
│   ├── reconstruct_cohort.py        — end-to-end: raw Mendeley download -> verified 349-image cohort
│   └── verify_shipped_cohort.py     — integrity-checks cohort_images/ against manifest/cohort_manifest.csv
├── manifest/
│   ├── original_dataset_manifest.csv  — all 366 original images: hashes, dims, inclusion/exclusion status
│   ├── cohort_manifest.csv            — the 349 included images (the analytical cohort)
│   ├── excluded_images.csv            — the 17 excluded images and why
│   ├── exact_duplicate_report.csv     — the 16 exact-duplicate groups
│   └── near_duplicate_candidates.csv  — near-duplicate pairs found and their disposition
└── cohort_images/
    ├── Negative/   — 150 images
    └── Positive/   — 199 images
```

`cohort_images/` contains byte-identical copies of 349 of the 366 images
from the original Mendeley release (see "Data source" and `ATTRIBUTION.md`
for license terms). No image content was altered.

## Data source

- Hananeh, W. & Fraiwan, M. "A histopathology image dataset for Johne's
  disease detection and research," *Data in Brief*, 2025.
  DOI: `10.1016/j.dib.2025.111975`.
- Dataset: "A dataset of histopathology images of paratuberculosis disease,"
  Mendeley Data, V3. DOI: [`10.17632/zjhymwjtxv.3`](https://doi.org/10.17632/zjhymwjtxv.3).
  License: **CC BY 4.0**.
- Original release: 366 H&E-stained images (157 Negative, 209 Positive),
  collected from slaughterhouses in Irbid, Amman, and Mafraq, Jordan
  (Jordan University of Science and Technology).

## Cohort construction summary

| Stage | Negative | Positive | Total |
|---|---|---|---|
| Original Mendeley release | 157 | 209 | 366 |
| − exact pixel-content duplicates | −6 | −10 | −16 |
| − verified near-duplicate (pHash) | −1 | 0 | −1 |
| **Final analytical cohort** | **150** | **199** | **349** |

- **Exact duplicates** (16 images, 16 groups): identified by hashing the
  *decoded* RGB pixel buffer (`pixel_content_sha256`), which catches
  duplicates even if re-saved/re-encoded, not just byte-identical files. One
  representative per group (lexicographically first `image_id`) was kept.
- **Near duplicate** (1 image): a 64-bit DCT perceptual hash (pHash) found
  one pair, `Negative/132.jpg` / `Negative/143.jpg`, at Hamming distance
  2/256 (>99% similarity), same class label — visually confirmed as an
  alternate copy of the same field and excluded (`Negative/143.jpg` removed).
  No cross-class near-duplicate pairs were found at any threshold, so no
  images were excluded on grounds that could indicate a labeling conflict.
- No images were excluded on artifact/scale-bar grounds: automated screening
  plus direct visual inspection confirmed `Negative/` and `Positive/` (unlike
  the auxiliary `ImagesS/` folder, which is documentation-only and was never
  used) contain no scale bars, overlaid text, or annotation borders. See
  `../data_audit/metadata_availability_report.md` for the full audit.

Full per-image detail is in `manifest/`.

## How to verify this package (no download needed)

Confirms the shipped `cohort_images/` files match their recorded hashes —
i.e. this package has not been corrupted or altered in transit:

```bash
pip install -r requirements.txt
python code/verify_shipped_cohort.py
```

Expected output: `SUCCESS: all 349 images verified against the manifest`.

## How to independently reconstruct the cohort from Mendeley

To confirm the cohort was *derived reproducibly* from the original release
(rather than just checking this copy is internally consistent), download the
dataset yourself and rebuild it from scratch:

1. Download and extract the dataset from
   https://data.mendeley.com/datasets/zjhymwjtxv/3 (DOI `10.17632/zjhymwjtxv.3`).
   The extracted folder should contain `Negative/`, `Positive/`, and `ImagesS/`
   subfolders (366 + 366 images respectively).
2. Install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   python code/reconstruct_cohort.py --source-dir /path/to/extracted/mendeley_download
   ```
   Add `--copy-cohort-to some/output/dir` to also materialize the 349-image
   cohort as files (this is how `cohort_images/` in this package was itself
   produced).

The script hashes every discovered image, verifies the release matches the
366-image manifest this study used (`manifest/original_dataset_manifest.csv`),
re-runs exact- and near-duplicate detection with the exact thresholds in
`config/cohort_reconstruction_config.yaml`, and diffs the result against
`manifest/cohort_manifest.csv`, printing `PASS`/`FAIL` and exit code 0/1.

## Notes

- **Hashing:** `file_sha256` is the raw file's hash (fails on any byte-level
  difference, e.g. re-compression); `pixel_content_sha256` is the hash of
  the *decoded* pixel array (robust to harmless re-encoding). Cohort
  membership is determined by `pixel_content_sha256`; `reconstruct_cohort.py`
  treats a `file_sha256` mismatch as a warning, not a failure, unless run
  with `--strict`.
- **No acquisition metadata** (animal/specimen/slide/scanner/magnification
  identifiers) exists in the public release beyond class label; see
  `../data_audit/metadata_availability_report.md`.
- **License compliance:** `cohort_images/` is redistributed under the
  original dataset's CC BY 4.0 license; see `ATTRIBUTION.md` for the
  required attribution and a description of the changes made (duplicate
  removal only — no image content was altered).

## How to cite this study

*To be added upon publication.*

If you use this reproducibility package, the analytical cohort, or the
associated code/results, please cite the manuscript:

> [Author list]. "[Manuscript title]." *[Journal name]*, [year].
> DOI: `[to be added]`.

```bibtex
@article{TODO_citekey,
  title   = {[Manuscript title]},
  author  = {[Author list]},
  journal = {[Journal name]},
  year    = {[year]},
  doi     = {[to be added]}
}
```

Also cite the original image dataset per the terms in `ATTRIBUTION.md`.
