# Extraction prompt

The system prompt used by `src/extractor.py` is the authoritative extraction prompt for this prototype. It asks the vision model to:
- identify table structure, groups and line items;
- preserve handwritten quantities and prices without rounding or calculating totals;
- inherit blank group values only with clear visual evidence;
- flag ambiguity, corrections, inherited values and crossed-out rows;
- use null rather than guessing;
- return source row/page, confidence indicators and notes.

The prompt is intentionally conservative. It does not assume that the Price column is a unit price or a line total.
