# Third-Party Data Attribution

The 349 images under `cohort_images/` are a subset of a third-party dataset,
included here under the terms of its license. They are **not** original to
this study.

## Original dataset

- **Title:** A dataset of histopathology images of paratuberculosis disease
- **Authors:** Wael Hananeh, Mohammad Fraiwan (Jordan University of Science
  and Technology, Faculty of Veterinary Medicine, Irbid, Jordan)
- **Repository:** Mendeley Data
- **DOI:** [10.17632/zjhymwjtxv.3](https://doi.org/10.17632/zjhymwjtxv.3)
- **URL:** https://data.mendeley.com/datasets/zjhymwjtxv/3
- **License:** CC BY 4.0 (Creative Commons Attribution 4.0 International) —
  https://creativecommons.org/licenses/by/4.0/
- **Associated publication:** Hananeh, W. & Fraiwan, M. "A histopathology
  image dataset for Johne's disease detection and research," *Data in
  Brief*, 2025. DOI: `10.1016/j.dib.2025.111975`.

## What was changed

CC BY 4.0 permits redistribution of adaptations provided changes are
indicated. Relative to the original 366-image release (157 Negative, 209
Positive):

- 16 exact pixel-content duplicate images were removed (one representative
  kept per duplicate group).
- 1 further image was removed as a verified near-duplicate (perceptual-hash
  Hamming distance 2/256, visually confirmed alternate copy).
- No image content itself was modified (no cropping, recompression, or
  relabeling) — files under `cohort_images/` are byte-identical copies of
  the corresponding files in the original Mendeley release.
- The result is a curated 349-image subset (150 Negative, 199 Positive) used
  as the analytical cohort in this study.

See `manifest/excluded_images.csv` and `../data_audit/metadata_availability_report.md`
for the full exclusion methodology and rationale.

## Required attribution

If you reuse `cohort_images/` (or any subset of it), attribute the original
authors and dataset, e.g.:

> Images derived from Hananeh, W. & Fraiwan, M. (2025), "A dataset of
> histopathology images of paratuberculosis disease," Mendeley Data, V3,
> DOI: 10.17632/zjhymwjtxv.3, licensed under CC BY 4.0. A curated subset of
> 349/366 images (duplicates removed) is redistributed here per the license
> terms; see ATTRIBUTION.md for details of the changes made.

This attribution is in addition to, not a replacement for, citing this
study's own manuscript when reusing the classification framework, code, or
results.
