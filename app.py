import io
import json
import os
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from src.extractor import extract_document
from src.validator import build_review_reasons, validate_record
from src.exporter import build_workbook

load_dotenv()

st.set_page_config(page_title="Inventory Intelligence", page_icon="📋", layout="wide")

PUBLIC_COLUMNS = [
    "Quantity", "Price", "Description", "Person name",
    "Job site", "Job name", "Job #", "Date"
]
FIELD_MAP = {
    "Quantity": "quantity",
    "Price": "price",
    "Description": "description",
    "Person name": "person_name",
    "Job site": "job_site",
    "Job name": "job_name",
    "Job #": "job_number",
    "Date": "date",
}
INTERNAL_FIELDS = [
    "record_id", "source_document", "source_row", "source_page",
    "status", "review_reasons", "flags", "confidence",
    "raw_values", "extraction_notes", "created_at"
]

def init_state():
    defaults = {
        "uploaded_docs": {},
        "records": [],
        "audit": [],
        "extraction_complete": False,
        "last_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def add_audit(event, document="", detail=""):
    st.session_state.audit.append({
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "document_id": document,
        "detail": detail,
    })

def to_public_frame(records):
    rows = []
    for rec in records:
        rows.append({col: rec.get(FIELD_MAP[col], "") for col in PUBLIC_COLUMNS})
    return pd.DataFrame(rows, columns=PUBLIC_COLUMNS)

def screen_upload():
    st.header("1 · Upload documents")
    st.write("Upload the handwritten inventory removal sheets. The four supplied case-study sheets are already included in `data/input` and can be selected below.")
    existing = sorted((__import__("pathlib").Path("data/input")).glob("*"))
    if existing:
        st.caption("Sample documents bundled with this prototype")
        selected = st.multiselect(
            "Use bundled sample sheets",
            options=[p.name for p in existing if p.suffix.lower() in [".png", ".jpg", ".jpeg"]],
            default=[p.name for p in existing if p.suffix.lower() in [".png", ".jpg", ".jpeg"]],
        )
        if st.button("Load selected sample sheets", type="secondary"):
            for name in selected:
                p = __import__("pathlib").Path("data/input") / name
                st.session_state.uploaded_docs[name] = p.read_bytes()
            add_audit("documents_loaded", detail=f"{len(selected)} bundled sample(s)")
            st.success(f"Loaded {len(selected)} sample document(s).")
    uploads = st.file_uploader(
        "Or upload your own image files",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="This prototype accepts image files. PDF conversion can be added if required.",
    )
    if uploads:
        for upload in uploads:
            st.session_state.uploaded_docs[upload.name] = upload.getvalue()
    if st.session_state.uploaded_docs:
        st.divider()
        st.subheader("Documents ready")
        cols = st.columns(4)
        for idx, (name, data) in enumerate(st.session_state.uploaded_docs.items()):
            with cols[idx % 4]:
                st.image(data, caption=name, use_container_width=True)
        st.info(f"{len(st.session_state.uploaded_docs)} document(s) ready for extraction.")
    else:
        st.warning("No documents loaded yet.")

def screen_extract():
    st.header("2 · AI extraction")
    st.write("Each sheet is sent to a vision-capable OpenAI model. The model returns structured line items; Python then applies basic validation and routes uncertain records for review.")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
    st.caption(f"Configured model: {model}")
    if not api_key:
        st.error("OPENAI_API_KEY is missing. Add it to your local .env file (see .env.example), then restart Streamlit.")
        return
    if not st.session_state.uploaded_docs:
        st.warning("Load documents on the Upload screen first.")
        return
    st.warning("The model may misread handwriting. Treat the output as a draft; verify it against the source before approval.")
    if st.button("Run extraction for loaded documents", type="primary"):
        st.session_state.records = []
        st.session_state.audit = []
        st.session_state.last_error = None
        progress = st.progress(0)
        status = st.empty()
        docs = list(st.session_state.uploaded_docs.items())
        for idx, (name, image_bytes) in enumerate(docs):
            status.write(f"Processing {name} …")
            try:
                result = extract_document(image_bytes, name, api_key=api_key, model=model)
                items = result.get("line_items", [])
                if not items:
                    add_audit("extraction_warning", name, "No line items returned.")
                for row_index, item in enumerate(items, start=1):
                    record = {
                        "record_id": str(uuid.uuid4()),
                        "source_document": name,
                        "source_row": item.get("source_row") or row_index,
                        "source_page": item.get("source_page") or 1,
                        "status": "EXTRACTED",
                        "review_reasons": [],
                        "flags": item.get("flags") or [],
                        "confidence": item.get("confidence", {}),
                        "raw_values": item.get("raw_values") or {},
                        "extraction_notes": item.get("notes", ""),
                        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    }
                    for key in FIELD_MAP.values():
                        record[key] = item.get(key, "")
                    reasons = build_review_reasons(record)
                    record["review_reasons"] = reasons
                    if reasons or record["flags"]:
                        record["status"] = "REVIEW_REQUIRED"
                    st.session_state.records.append(record)
                add_audit("extraction_completed", name, f"{len(items)} line item(s) returned.")
            except Exception as exc:
                st.session_state.last_error = f"{name}: {exc}"
                add_audit("extraction_failed", name, str(exc))
            progress.progress((idx + 1) / len(docs))
        st.session_state.extraction_complete = True
        status.write("Extraction run finished.")
        if st.session_state.last_error:
            st.error(st.session_state.last_error)
        st.success(f"Extraction returned {len(st.session_state.records)} line item(s). Review flagged records before using the output.")
    if st.session_state.records:
        df = to_public_frame(st.session_state.records)
        review_count = sum(1 for r in st.session_state.records if r["status"] == "REVIEW_REQUIRED")
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows extracted", len(df))
        c2.metric("Require review", review_count)
        c3.metric("Documents processed", len(set(r["source_document"] for r in st.session_state.records)))
        st.dataframe(df, use_container_width=True, hide_index=True)

def screen_review():
    st.header("3 · Human review")
    records = st.session_state.records
    if not records:
        st.info("No extracted records yet. Run extraction first.")
        return
    flagged = [r for r in records if r["status"] == "REVIEW_REQUIRED"]
    st.write("Review the source image and the extracted values together. Correct values only when the handwriting supports the correction.")
    st.metric("Records requiring review", len(flagged))
    if not flagged:
        st.success("No records are currently flagged by the prototype's basic checks. This does not prove that every extraction is correct; still sample-check the source sheets.")
    for rec in flagged:
        title = f'{rec["source_document"]} · Row {rec["source_row"]} · {", ".join(rec["review_reasons"] or rec["flags"])}'
        with st.expander(title, expanded=True):
            source_bytes = st.session_state.uploaded_docs.get(rec["source_document"])
            left, right = st.columns([1, 1.2])
            with left:
                if source_bytes:
                    st.image(source_bytes, caption="Original source sheet", use_container_width=True)
                st.caption(f'Page {rec["source_page"]} · Source row {rec["source_row"]}')
                if rec.get("extraction_notes"):
                    st.write("Model note:", rec["extraction_notes"])
            with right:
                st.write("Extracted fields")
                edits = {}
                for label, key in FIELD_MAP.items():
                    current = rec.get(key, "")
                    edits[key] = st.text_input(label, value="" if current is None else str(current),
                                               key=f'{rec["record_id"]}_{key}')
                if st.button("Save corrections and mark reviewed", key=f'review_{rec["record_id"]}'):
                    for key, value in edits.items():
                        rec[key] = value
                    rec["status"] = "REVIEWED"
                    rec["review_reasons"] = build_review_reasons(rec)
                    add_audit("record_reviewed", rec["source_document"], f'Row {rec["source_row"]} corrected/reviewed.')
                    st.success("Review saved. This is not a financial approval.")
                    st.rerun()
    st.divider()
    st.subheader("All extracted records")
    st.dataframe(to_public_frame(records), use_container_width=True, hide_index=True)

def screen_export():
    st.header("4 · Export and audit")
    records = st.session_state.records
    if not records:
        st.info("Run extraction before exporting.")
        return
    pending = sum(1 for r in records if r["status"] == "REVIEW_REQUIRED")
    st.metric("Records still requiring review", pending)
    st.warning("Export includes all extracted line items, including items still requiring review. The audit sheet records their status; do not treat the workbook as approved financial posting data.")
    workbook = build_workbook(records, st.session_state.audit)
    st.download_button(
        "Download Excel workbook",
        data=workbook,
        file_name="inventory_intelligence_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    csv_data = to_public_frame(records).to_csv(index=False).encode("utf-8-sig")
    st.download_button("Download transactions CSV", data=csv_data, file_name="transactions.csv", mime="text/csv")
    st.subheader("Processing audit")
    audit_df = pd.DataFrame(st.session_state.audit)
    if not audit_df.empty:
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No processing events recorded yet.")

def main():
    init_state()
    st.title("📋 Inventory Intelligence")
    st.caption("Handwritten inventory removal sheet extraction · Case-study prototype")
    page = st.sidebar.radio(
        "Workflow",
        ["1 · Upload", "2 · Extract", "3 · Review", "4 · Export"],
        label_visibility="visible",
    )
    st.sidebar.divider()
    st.sidebar.caption("Prototype controls")
    st.sidebar.write(f"Documents: **{len(st.session_state.uploaded_docs)}**")
    st.sidebar.write(f"Extracted rows: **{len(st.session_state.records)}**")
    st.sidebar.write(f"Needs review: **{sum(1 for r in st.session_state.records if r['status'] == 'REVIEW_REQUIRED')}**")
    if page.startswith("1"):
        screen_upload()
    elif page.startswith("2"):
        screen_extract()
    elif page.startswith("3"):
        screen_review()
    else:
        screen_export()

if __name__ == "__main__":
    main()
