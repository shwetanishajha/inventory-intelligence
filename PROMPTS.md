# Prompt and session log

## Extraction prompt
See `prompts/extraction_prompt.md`. The full system prompt is embedded in `src/extractor.py` so the running application uses the same version.

## Human steering / operating instructions
1. Extract every apparent line item separately.
2. Do not guess unreadable handwriting, quantities, prices, dates or job references.
3. Preserve fractional quantities and original financial notation.
4. Inherit group metadata only where the sheet provides clear visual evidence.
5. Keep crossed-out entries for audit, but flag them as excluded from approval.
6. Return evidence notes and field-level confidence indicators.
7. A human must verify flagged records against the original image before approval.

## Session log
This file is a starter record, not a fabricated transcript. Add the actual prompts, corrections, model/version, and decisions made during your working session before submission. Preserve any relevant AI coding-assistant session history separately if available.
