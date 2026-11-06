REQUIRED_FIELDS = ["quantity", "price", "description"]

def build_review_reasons(record):
    reasons = []
    flags = record.get("flags") or []
    for flag in flags:
        if flag == "CROSSED_OUT":
            reasons.append("Crossed-out row — exclude from approved transactions")
        elif flag == "AMBIGUOUS_HANDWRITING":
            reasons.append("Ambiguous handwriting")
        elif flag == "INHERITED_VALUE":
            reasons.append("Inherited value — verify group boundary and source")
        elif flag == "CORRECTION":
            reasons.append("Handwritten correction/overwrite — verify")
        elif flag == "MISSING_VALUE":
            reasons.append("One or more values missing")
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or str(value).strip() == "":
            reasons.append(f"Missing {field.replace('_', ' ')}")
    # Deduplicate while preserving order.
    return list(dict.fromkeys(reasons))

def validate_record(record):
    """Basic syntactic checks only; does not establish business correctness."""
    errors = []
    quantity = record.get("quantity")
    if quantity not in (None, ""):
        # Fraction formats are intentionally preserved rather than coerced here.
        text = str(quantity).strip()
        if not any(ch.isdigit() for ch in text):
            errors.append("Quantity contains no numeric character")
    price = record.get("price")
    if price not in (None, "") and not any(ch.isdigit() for ch in str(price)):
        errors.append("Price contains no numeric character")
    return errors
