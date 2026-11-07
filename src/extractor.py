
import base64
import json
import os
import re
from typing import Any

from openai import OpenAI


FIELDS = [
    "quantity",
    "price",
    "description",
    "person_name",
    "job_site",
    "job_name",
    "job_number",
    "date",
]


ALIASES = {
    "quantity": ["quantity", "qty", "q ty"],
    "price": ["price", "unit price", "cost"],
    "description": ["description", "item", "material"],
    "person_name": ["person name", "person", "name"],
    "job_site": ["job site", "site"],
    "job_name": ["job name", "project", "job"],
    "job_number": ["job number", "job no", "job #", "job id"],
    "date": ["date"],
}


def normalise_key(value):
    return re.sub(
        r"[^a-z0-9]+", " ", str(value).lower()
    ).strip()


def get_field(data, field):
    if not isinstance(data, dict):
        return None

    accepted = {normalise_key(field)}

    accepted.update(
        normalise_key(alias)
        for alias in ALIASES[field]
    )

    for key, value in data.items():
        if normalise_key(key) in accepted:
            return value

    return None


SYSTEM_PROMPT = r"""
You extract handwritten inventory removal/sign-out sheets
into structured records.

Your primary responsibility is accurate transcription.
Never invent, calculate, silently correct or silently complete
a handwritten value.

Read the document from top to bottom.
Preserve the physical order of transaction rows.
Do not resolve inheritance. Python will resolve inheritance later.

RETURN FORMAT

Return ONLY valid JSON with this structure:

{
  "line_items": [
    {
      "source_page": 1,
      "source_row": "1",
      "group_id": 1,

      "quantity": "50",
      "price": "13.72",
      "description": "Tiger Paw Flapper Disc",
      "person_name": "A.J.",
      "job_site": "North Bay Shop",
      "job_name": "TSC Upgrade",
      "job_number": "26-1148",
      "date": "5-7-26",

      "raw_values": {
        "quantity": "50",
        "price": "13.72",
        "description": "Tiger Paw Flapper Disc",
        "person_name": "A.J.",
        "job_site": "North Bay Shop",
        "job_name": "TSC Upgrade",
        "job_number": "26-1148",
        "date": "5-7-26"
      },

      "field_markers": {
        "quantity": "explicit",
        "price": "explicit",
        "description": "explicit",
        "person_name": "explicit",
        "job_site": "explicit",
        "job_name": "explicit",
        "job_number": "explicit",
        "date": "explicit"
      },

      "field_issues": {
        "quantity": [],
        "price": [],
        "description": [],
        "person_name": [],
        "job_site": [],
        "job_name": [],
        "job_number": [],
        "date": []
      },

      "flags": [],

      "confidence": {
        "quantity": "high",
        "price": "high",
        "description": "high",
        "person_name": "high",
        "job_site": "high",
        "job_name": "high",
        "job_number": "high",
        "date": "high"
      },

      "notes": ""
    }
  ],
  "document_notes": []
}

Use null for values that are absent or cannot be read.

FIELD MARKERS

Every field must have exactly one marker:

- explicit: a handwritten value is present.
- ditto: quotation marks or ditto symbol indicate repetition.
- slash: a forward slash clearly indicates repetition.
- down_arrow: a downward arrow indicates continuation.
- blank: the cell is genuinely empty.
- ambiguous: the symbol or handwriting cannot be identified reliably.

Do not resolve repetition markers.
Return null as the canonical field value for ditto, slash and down_arrow.
Preserve the original symbol in raw_values.

TRANSCRIPTION

1. Return one record per apparent transaction row.
2. Do not merge separate rows.
3. Preserve fractional quantities exactly, including 1/2, 1.5 and 1½.
4. Preserve prices exactly as written.
5. Do not calculate totals or assume whether a price is a unit price.
6. Distinguish handwritten digits carefully, especially:
   1 and 4,
   1 and 7,
   4 and V,
   0 and 6.
7. Do not convert a questionable character into a confident number.
8. Preserve the original visible transcription in raw_values.

CORRECTIONS AND OVERWRITES

Inspect every cell for overwritten, corrected or rewritten values.

If handwriting has visibly been overwritten:

- Add CORRECTION to the row-level flags.
- Add CORRECTION to the affected field's field_issues list.
- Set that field's marker to ambiguous.
- Preserve the visible original and replacement readings in raw_values or notes.
- If the intended final value is unclear, return null.
- Do not silently treat a corrected value as an ordinary explicit value.

Example:

"field_markers": {
  "price": "ambiguous"
},
"field_issues": {
  "price": ["CORRECTION"]
},
"flags": ["CORRECTION"]

CROSSED-OUT VALUES

If a value or row is crossed out:

- Add CROSSED_OUT to flags.
- Add CROSSED_OUT to the affected field's field_issues list.
- Set the affected canonical field to null.
- Preserve the original visible writing in raw_values.
- Explain the observation in notes.
- Do not discard the row.

AMBIGUOUS HANDWRITING

If a character or value cannot be identified reliably:

- Return null for the affected canonical field.
- Add AMBIGUOUS_HANDWRITING to flags.
- Add AMBIGUOUS_HANDWRITING to the affected field's field_issues list.
- Preserve the best visible candidate in raw_values.
- Explain what is unclear in notes.

CONFIDENCE

Assign confidence independently to all eight fields.

Use:
- high: clearly readable.
- medium: plausible reading, but some visual uncertainty.
- low: substantially uncertain.

Do not assign high confidence merely because a plausible interpretation exists.

GROUPS AND INHERITANCE

1. Identify transaction groups from the physical layout.
2. Group IDs must follow visible layout, not changes in person alone.
3. Do not assume a new group merely because the person changes.
4. Do not infer values across a new group boundary.
5. Identify ditto marks, slashes and downward arrows.
6. Do not replace these symbols with inherited values.
7. A genuinely blank cell is not a repetition marker.
8. Never inherit from an uncertain preceding value.

FINAL REQUIREMENTS

- Include all eight canonical fields in every row.
- Include all eight keys in raw_values.
- Include all eight keys in field_markers.
- Include all eight keys in field_issues.
- Include all eight keys in confidence.
- Preserve crossed-out rows.
- Preserve physical row order.
- Do not optimise for zero human-review records.
- Do not suppress visible corrections because the intended value seems obvious.
- Return JSON only.
"""


def normalise_row(item, row_number):

    if isinstance(item, list):

        if len(item) != len(FIELDS):
            raise ValueError(
                f"Row {row_number}: expected {len(FIELDS)} "
                f"values but received {len(item)}."
            )

        item = dict(zip(FIELDS, item))

    if not isinstance(item, dict):
        raise ValueError(
            f"Row {row_number}: invalid row type "
            f"{type(item).__name__}."
        )

    raw_source = item.get("raw_values")
    marker_source = item.get("field_markers")
    issue_source = item.get("field_issues")

    if not isinstance(raw_source, dict):
        raw_source = {}

    if not isinstance(marker_source, dict):
        marker_source = {}

    if not isinstance(issue_source, dict):
        issue_source = {}

    raw_values = {}
    field_markers = {}
    field_issues = {}

    for field in FIELDS:

        value = get_field(item, field)
        raw_value = get_field(raw_source, field)

        if value is None and raw_value is not None:
            value = raw_value

        marker = get_field(marker_source, field)

        if marker is None:
            marker = (
                "explicit"
                if value is not None and str(value).strip()
                else "blank"
            )

        marker = str(marker).strip().lower()
        marker = marker.replace(" ", "_")

        marker_aliases = {
            "value": "explicit",
            "quotation": "ditto",
            "quote": "ditto",
            '"': "ditto",
            "〃": "ditto",
            "/": "slash",
            "downarrow": "down_arrow",
            "↓": "down_arrow",
            "empty": "blank",
            "uncertain": "ambiguous",
        }

        marker = marker_aliases.get(marker, marker)

        allowed = {
            "explicit",
            "ditto",
            "slash",
            "down_arrow",
            "blank",
            "ambiguous",
        }

        if marker not in allowed:
            marker = "ambiguous"

        issues = get_field(issue_source, field)

        if isinstance(issues, str):
            issues = [issues]

        if not isinstance(issues, list):
            issues = []

        raw_values[field] = (
            raw_value if raw_value is not None else value
        )

        if marker == "explicit":
            item[field] = value
        else:
            item[field] = None

        field_markers[field] = marker
        field_issues[field] = list(issues)

    flags = item.get("flags")

    if not isinstance(flags, list):
        flags = []

    item["raw_values"] = raw_values
    item["field_markers"] = field_markers
    item["field_issues"] = field_issues
    item["flags"] = list(dict.fromkeys(flags))

    confidence = item.get("confidence")

    if not isinstance(confidence, dict):
        confidence = {}

    item["confidence"] = {
        field: get_field(confidence, field)
        for field in FIELDS
    }

    item["notes"] = str(item.get("notes") or "")

    return item


def extract_document(
    image_bytes: bytes,
    filename: str,
    api_key: str | None = None,
    model: str = "gpt-4o",
) -> dict[str, Any]:

    key = api_key or os.getenv("OPENAI_API_KEY")

    if not key:
        raise ValueError(
            "OpenAI API key is missing. Check your .env file."
        )

    if not image_bytes:
        raise ValueError(
            f"The uploaded file is empty: {filename}"
        )

    client = OpenAI(api_key=key)

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    extension = os.path.splitext(filename)[1].lower()

    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }

    mime_type = mime_types.get(
        extension, "image/png"
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Extract all transaction rows from "
                            f"{filename}. Follow the JSON schema "
                            "and all field-level instructions. "
                            "Inspect each handwritten cell for "
                            "overwrites, corrections, cross-outs, "
                            "ambiguous characters and repetition "
                            "symbols. Preserve the original "
                            "transcription and physical row order. "
                            "Do not resolve inheritance."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                f"data:{mime_type};base64,"
                                f"{image_base64}"
                            ),
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "The extraction model returned an empty response."
        )

    try:
        result = json.loads(content)

    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON extraction response: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "Extraction response must be a JSON object."
        )

    rows = result.get("line_items")

    if not isinstance(rows, list):
        raise ValueError(
            "Extraction response must contain a line_items list."
        )

    result["line_items"] = [
        normalise_row(item, index)
        for index, item in enumerate(rows, start=1)
    ]

    return result
