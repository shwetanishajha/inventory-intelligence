Inventory Intelligence
A Streamlit prototype for extracting handwritten inventory removal/sign-out sheets into structured transaction records. It uses a vision-capable OpenAI model for transcription, Python rules for field-level inheritance, validation to identify records requiring human review, and Excel export.
Prototype notice: AI extraction is a draft, not an approved inventory record. Verify extracted values against the original sheet before relying on them.

Run locally in 5 minutes
Requirements
- Python 3.10 or newer
- An OpenAI API key with access to the model configured for this application
- Git (only if cloning the repository)
1. Get the code
Clone the repository, or open the project folder you received:
git clone <https://github.com/shwetanishajha/inventory-intelligence>
cd inventory-intelligence
If you already have the project files, open a terminal in the folder containing app.py.
2. Create and activate a virtual environment
Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
If PowerShell blocks activation, run this for the current terminal session and retry:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
4. Configure the API key
Copy the example environment file:

Windows PowerShell
Copy-Item .env.example .env
macOS / Linux
cp .env.example .env
Open .env and replace the placeholder with your key:
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
Keep .env private. Never commit it to Git or share it with others.
5. Start the application
python -m streamlit run app.py
Open the local URL shown in the terminal (usually http://localhost:8501).
Use the application
1. Open the extraction page.
2. Upload the inventory sheet image(s).
3. Run extraction for new documents.
4. Inspect the extracted transaction rows.
5. Resolve records in the human-review queue.
6. Export the resulting workbook.
The application may skip a document whose filename is already marked as completed in its local document registry. If you intentionally need to reprocess a document, use the application's supported workflow or carefully reset the local processing data after backing it up. Restart Streamlit after manually changing persisted data so the in-memory session state is refreshed.
Project structure
inventory-intelligence/
├── app.py                       # Streamlit interface and workflow
├── README.md                    # Setup and usage guide
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment-variable template
├── .gitignore                   # Excludes secrets and local/generated files
├── data/
│   ├── input/                   # Local input images (if stored here)
│   ├── output/                  # Export destination / generated output
│   └── processed/               # Local JSON persistence
├── docs/
│   └── deployment_strategy.md   # Deployment considerations
└── src/
    ├── __init__.py
    ├── extractor.py             # OpenAI vision extraction and normalisation
    ├── rules_engine.py          # Deterministic field-level inheritance
    ├── validator.py             # Validation and review reasons
    ├── exporter.py              # Workbook generation
    └── storage.py               # Local records, audit and registry storage
How the processing flow works
1. Extraction: the vision model transcribes the source sheet into structured rows and captures raw values, markers, confidence and potential issues.
2. Inheritance: the Python rules engine resolves supported ditto/repetition markers field by field, respecting group boundaries.
3. Validation: required-field checks and extraction issues generate review reasons.
4. Human review: uncertain or corrected/crossed-out entries can be checked before approval.
5. Export and persistence: records, audit events and document-processing status are stored locally; the application can generate an Excel workbook.
The model does not make final approval decisions. Human review remains an important control.
Local data and privacy
- data/processed/ contains local JSON files used for extracted records, audit history and the document registry. These files are generated at runtime and should not normally be committed.
- data/output/ is for generated output and should not normally be committed.
- .venv/ is a machine-specific Python environment. Each developer should create their own.
- .env contains credentials and must remain private.
- Uploaded source images are sent to the configured OpenAI API for processing. Only use documents you are authorised to submit to that service.
- Back up local records and audit data before deleting or resetting data/processed/.
Troubleshooting
OPENAI_API_KEY is missing or authentication fails
- Confirm .env is in the same directory as app.py.
- Check that the key is valid and has access to the configured model.
- Restart Streamlit after changing .env.
ModuleNotFoundError or dependency errors
- Confirm the virtual environment is activated.
- Run pip install -r requirements.txt from the project root.
- Start Streamlit from the directory containing app.py.
A document is reported as already processed
- The application uses data/processed/document_registry.json to remember completed filenames.
- Deleting input images alone does not clear this registry.
- If you remove persisted data manually, stop and restart Streamlit to clear the session's in-memory state as well.
- Back up records and audit history before resetting local data.
Port 8501 is already in use
Run Streamlit on another port:
python -m streamlit run app.py --server.port 8502
Current limitations
This is a case-study prototype, not a production inventory-control system. Handwriting recognition may be incorrect or incomplete. Confidence labels are model-reported signals and are not calibrated probabilities. Review flagged records and sample-check unflagged records against the original sheets.

Production use would require, at minimum, a defined identity and access-control model, managed secrets, controlled document retention, monitoring, formal evaluation against a labelled dataset, backup/recovery, and an approved human sign-off process.