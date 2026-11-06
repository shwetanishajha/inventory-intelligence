# Inventory Intelligence — case-study prototype

A small Streamlit application that uses a vision-capable OpenAI model to extract handwritten inventory removal sheets into structured line items, route uncertain records for human review, and export an Excel workbook.

## What it does
- Uploads image-based inventory sheets (PNG/JPG).
- Sends each image to a vision model for structured extraction.
- Preserves quantities and prices as written; does not calculate line totals.
- Flags ambiguity, inherited values, corrections, crossed-out rows and missing core fields.
- Displays source images alongside editable review fields.
- Exports an Excel workbook with Transactions, Review Queue, Audit & Processing Log, and Processing Events sheets, plus a CSV of the eight requested transaction columns.

## Run locally (approximately 10 minutes if Python is installed)
1. Unzip the project and open the folder in VS Code.
2. Create and activate a virtual environment:
   - macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows PowerShell: `python -m venv .venv; .\.venv\Scripts\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and add your OpenAI API key.
5. Run: `streamlit run app.py`
6. In the sidebar, choose Upload, load the four bundled sheets, then Extract, Review and Export.

## Important limitations
- This is a case-study prototype, not a production financial control.
- The model may misread handwriting or omit rows. Independently reconcile source row counts and verify every output against the original sheets.
- Confidence values are model-reported and are not calibrated probabilities.
- No client job master is supplied. Job number/name/site matching is therefore not represented as a successful master-data validation.
- Price semantics (unit price versus line total) are unknown; values are preserved without calculating totals.
- Duplicate detection, authentication, cloud storage, ERP posting, PDF ingestion and production monitoring are not implemented.
- The current review screen supports correction of flagged records; a reviewer should still sample-check unflagged rows.
- API usage incurs charges. Do not commit `.env` or expose API keys.

## Output
`Transactions` contains exactly the eight requested columns. All extracted rows are retained, including flagged or crossed-out entries; their review/exclusion status is recorded in the audit sheets. Do not treat the export as approved posting data.

## Production considerations
A production version would require representative labelled ground truth, calibrated field-level evaluation, client job-master integration, duplicate controls, role-based approval, secure document retention, idempotent ERP integration, auditability, operational monitoring and a controlled rollout.
