
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

MARKER_ALIASES = {
    "explicit": "explicit",
    "value": "explicit",
    "ditto": "ditto",
    '"': "ditto",
    "〃": "ditto",
    "slash": "slash",
    "/": "slash",
    "down_arrow": "down_arrow",
    "down arrow": "down_arrow",
    "↓": "down_arrow",
    "blank": "blank",
    "empty": "blank",
    "ambiguous": "ambiguous",
    "uncertain": "ambiguous",
}


def normalize_marker(marker):
    if marker is None:
        return None

    marker = str(marker).strip().lower()
    return MARKER_ALIASES.get(marker, "ambiguous")


def resolve_inheritance(line_items):
    """Resolve inheritance safely, field by field, top-to-bottom."""

    resolved_records = []
    previous_record = None

    for item in line_items:
        record = dict(item)

        # Rebuild inheritance-related flags for this run.
        flags = list(record.get("flags") or [])
        flags = [
            flag for flag in flags
            if flag not in {
                "INHERITED_VALUE",
                "MISSING_VALUE",
                "INHERITANCE_UNRESOLVED",
            }
        ]

        record["flags"] = flags

        raw_values = dict(record.get("raw_values") or {})
        field_markers = dict(record.get("field_markers") or {})
        field_issues = dict(record.get("field_issues") or {})

        group_id = record.get("group_id")
        record["inheritance_provenance"] = {}

        same_group = (
            previous_record is not None
            and group_id is not None
            and group_id == previous_record.get("group_id")
        )

        for field in FIELDS:
            value = record.get(field)
            marker = normalize_marker(field_markers.get(field))
            raw_value = raw_values.get(field)
            issues = field_issues.get(field) or []

            # Corrected or crossed-out fields require review.
            if any(issue in {"CORRECTION", "CROSSED_OUT"} for issue in issues):
                record[field] = None
                record["inheritance_provenance"][field] = {
                    "type": "review_required",
                    "reason": "Corrected or crossed-out source value",
                }
                continue

            # Infer marker only when the extractor did not provide one.
            if marker is None:
                marker = (
                    "explicit"
                    if value is not None and str(value).strip()
                    else "blank"
                )

            # Explicit value.
            if marker == "explicit":
                if value is None or not str(value).strip():
                    record[field] = None
                    record["flags"].append("MISSING_VALUE")
                    record["inheritance_provenance"][field] = {
                        "type": "missing_explicit_value",
                    }
                else:
                    record[field] = str(value).strip()
                    record["inheritance_provenance"][field] = {
                        "type": "explicit",
                        "source_row": record.get("source_row"),
                    }
                continue

            # Genuine blank: never inherit.
            if marker == "blank":
                record[field] = None
                record["flags"].append("MISSING_VALUE")
                record["inheritance_provenance"][field] = {
                    "type": "blank",
                    "source_row": record.get("source_row"),
                }
                continue

            # Ambiguous handwriting.
            if marker == "ambiguous":
                record[field] = None
                record["flags"].append("AMBIGUOUS_HANDWRITING")
                record["inheritance_provenance"][field] = {
                    "type": "ambiguous",
                    "raw_value": raw_value,
                }
                continue

            # Ditto, slash or downward arrow.
            if marker in {"ditto", "slash", "down_arrow"}:
                if not same_group:
                    record[field] = None
                    record["flags"].append("INHERITANCE_UNRESOLVED")
                    record["inheritance_provenance"][field] = {
                        "type": "unresolved",
                        "marker": marker,
                        "reason": "No preceding row in the same group",
                    }
                    continue

                previous_value = previous_record.get(field)

                if previous_value is None or not str(previous_value).strip():
                    record[field] = None
                    record["flags"].append("INHERITANCE_UNRESOLVED")
                    record["inheritance_provenance"][field] = {
                        "type": "unresolved",
                        "marker": marker,
                        "reason": "Previous row has no usable value",
                    }
                    continue

                record[field] = previous_value
                record["flags"].append("INHERITED_VALUE")
                record["inheritance_provenance"][field] = {
                    "type": "inherited",
                    "marker": marker,
                    "inherited_from_row": previous_record.get("source_row"),
                    "group_id": group_id,
                }
                continue

        # Deduplicate flags.
        record["flags"] = list(dict.fromkeys(record["flags"]))

        resolved_records.append(record)
        previous_record = record

    return resolved_records
