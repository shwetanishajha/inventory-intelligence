import io
import json
import pandas as pd

PUBLIC_COLUMNS = [
    ("Quantity", "quantity"), ("Price", "price"), ("Description", "description"),
    ("Person name", "person_name"), ("Job site", "job_site"),
    ("Job name", "job_name"), ("Job #", "job_number"), ("Date", "date"),
]

def build_workbook(records, audit_events):
    output = io.BytesIO()
    transactions = pd.DataFrame([
        {label: rec.get(key, "") for label, key in PUBLIC_COLUMNS}
        for rec in records
    ], columns=[label for label, _ in PUBLIC_COLUMNS])
    review_rows = []
    audit_rows = []
    for rec in records:
        for reason in rec.get("review_reasons", []):
            review_rows.append({
                "Source document": rec.get("source_document"),
                "Page": rec.get("source_page"),
                "Source row": rec.get("source_row"),
                "Field / issue": reason,
                "Extracted values": json.dumps({k: rec.get(k) for _, k in PUBLIC_COLUMNS}, ensure_ascii=False),
                "Status": rec.get("status"),
            })
        audit_rows.append({
            "Record ID": rec.get("record_id"),
            "Source document": rec.get("source_document"),
            "Page": rec.get("source_page"),
            "Source row": rec.get("source_row"),
            "Status": rec.get("status"),
            "Flags": ", ".join(rec.get("flags") or []),
            "Confidence": json.dumps(rec.get("confidence") or {}, ensure_ascii=False),
            "Raw values": json.dumps(rec.get("raw_values") or {}, ensure_ascii=False),
            "Extraction notes": rec.get("extraction_notes", ""),
            "Review reasons": " | ".join(rec.get("review_reasons") or []),
        })
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        transactions.to_excel(writer, sheet_name="Transactions", index=False)
        pd.DataFrame(review_rows, columns=[
            "Source document", "Page", "Source row", "Field / issue", "Extracted values", "Status"
        ]).to_excel(writer, sheet_name="Review Queue", index=False)
        pd.DataFrame(audit_rows).to_excel(writer, sheet_name="Audit & Processing Log", index=False)
        pd.DataFrame(audit_events).to_excel(writer, sheet_name="Processing Events", index=False)
    output.seek(0)
    return output.getvalue()
