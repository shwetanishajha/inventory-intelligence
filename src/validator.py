
REQUIRED_FIELDS = [
    "quantity",
    "price",
    "description",
]

LOW_CONFIDENCE_VALUES = {
    "low",
    "medium",
}


def build_review_reasons(record):
    reasons = []

    flags = record.get("flags") or []

    flag_messages = {
        "CROSSED_OUT": "Crossed-out value — verify before approval",
        "AMBIGUOUS_HANDWRITING": "Ambiguous handwriting",
        "CORRECTION": "Handwritten correction/overwrite — verify",
        "MISSING_VALUE": "Blank or missing cell — inheritance not permitted",
        "INHERITANCE_UNRESOLVED": "Inheritance could not be resolved safely",
        "AMBIGUOUS_GROUP_BOUNDARY": "Uncertain transaction group boundary",
    }

    for flag in flags:
        message = flag_messages.get(flag)
        if message:
            reasons.append(message)

    # Required transaction fields must not be empty.
    for field in REQUIRED_FIELDS:
        value = record.get(field)

        if value is None or str(value).strip() == "":
            reasons.append(
                f"Missing {field.replace('_', ' ')}"
            )

    # Field-level issues are checked independently.
    field_issues = record.get("field_issues") or {}

    for field, issues in field_issues.items():
        for issue in issues or []:

            if issue == "CROSSED_OUT":
                reasons.append(
                    f"{field}: Crossed-out value — verify before approval"
                )

            elif issue == "CORRECTION":
                reasons.append(
                    f"{field}: Handwritten correction/overwrite — verify"
                )

            elif issue == "AMBIGUOUS_HANDWRITING":
                reasons.append(
                    f"{field}: Ambiguous handwriting"
                )

    # Check confidence only when the extractor supplies it.
    confidence = record.get("confidence") or {}

    for field, level in confidence.items():
        if str(level).strip().lower() in LOW_CONFIDENCE_VALUES:
            reasons.append(
                f"{field}: Low or medium extraction confidence — verify"
            )

    # Deduplicate while preserving order.
    return list(dict.fromkeys(reasons))


def validate_record(record):
    """Basic syntactic checks only; does not establish business correctness."""

    errors = []

    quantity = record.get("quantity")

    if quantity not in (None, ""):
        text = str(quantity).strip()

        if not any(ch.isdigit() for ch in text):
            errors.append(
                "Quantity contains no numeric character"
            )

    price = record.get("price")

    if price not in (None, ""):
        if not any(ch.isdigit() for ch in str(price)):
            errors.append(
                "Price contains no numeric character"
            )

    return errors
