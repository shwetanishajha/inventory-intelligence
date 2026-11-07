
import io
import json
import pandas as pd


PUBLIC_COLUMNS = [
    ("Quantity", "quantity"),
    ("Price", "price"),
    ("Description", "description"),
    ("Person name", "person_name"),
    ("Job site", "job_site"),
    ("Job name", "job_name"),
    ("Job #", "job_number"),
    ("Date", "date"),
]


def json_text(value):
    return json.dumps(
        value if value is not None else {},
        ensure_ascii=False
    )


def build_workbook(records, audit_events):

    output = io.BytesIO()

    # 1. Transactions
    transactions = pd.DataFrame(
        [
            {
                label: rec.get(key, "")
                for label, key in PUBLIC_COLUMNS
            }
            for rec in records
        ],
        columns=[label for label, _ in PUBLIC_COLUMNS]
    )

    review_rows = []
    audit_rows = []

    for rec in records:

        # 2. Human review queue
        for reason in rec.get("review_reasons", []):

            review_rows.append({
                "Source document": rec.get("source_document"),
                "Page": rec.get("source_page"),
                "Source row": rec.get("source_row"),
                "Group ID": rec.get("group_id"),
                "Field / issue": reason,
                "Extracted values": json_text({
                    key: rec.get(key)
                    for _, key in PUBLIC_COLUMNS
                }),
                "Field issues": json_text(
                    rec.get("field_issues")
                ),
                "Status": rec.get("status"),
            })

        # 3. Complete audit trail
        audit_rows.append({

            "Record ID": rec.get("record_id"),
            "Source document": rec.get("source_document"),
            "Page": rec.get("source_page"),
            "Source row": rec.get("source_row"),
            "Group ID": rec.get("group_id"),

            "Status": rec.get("status"),

            "Flags": ", ".join(
                rec.get("flags") or []
            ),

            "Review reasons": " | ".join(
                rec.get("review_reasons") or []
            ),

            "Extracted values": json_text({
                key: rec.get(key)
                for _, key in PUBLIC_COLUMNS
            }),

            "Raw values": json_text(
                rec.get("raw_values")
            ),

            "Field markers": json_text(
                rec.get("field_markers")
            ),

            "Field issues": json_text(
                rec.get("field_issues")
            ),

            "Inheritance provenance": json_text(
                rec.get("inheritance_provenance")
            ),

            "Confidence": json_text(
                rec.get("confidence")
            ),

            "Extraction notes": rec.get(
                "extraction_notes", ""
            ),
        })

    # 4. Write workbook
    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        transactions.to_excel(
            writer,
            sheet_name="Transactions",
            index=False
        )

        pd.DataFrame(review_rows).to_excel(
            writer,
            sheet_name="Review Queue",
            index=False
        )

        pd.DataFrame(audit_rows).to_excel(
            writer,
            sheet_name="Audit & Processing Log",
            index=False
        )

        pd.DataFrame(audit_events).to_excel(
            writer,
            sheet_name="Processing Events",
            index=False
        )

    output.seek(0)

    return output.getvalue()
