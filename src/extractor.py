import base64
import json
from openai import OpenAI

SYSTEM_PROMPT = """
You extract handwritten inventory removal/sign-out sheets into structured records.
Be conservative: never invent or silently complete a value. Preserve what is visibly written.
Return ONLY valid JSON with this exact top-level shape:
{
  "line_items": [
    {
      "source_page": 1,
      "source_row": "visible row number or a concise position label",
      "quantity": "string or null",
      "price": "string or null",
      "description": "string or null",
      "person_name": "string or null",
      "job_site": "string or null",
      "job_name": "string or null",
      "job_number": "string or null",
      "date": "string or null",
      "raw_values": {"quantity":"as seen", "price":"as seen"},
      "flags": ["AMBIGUOUS_HANDWRITING", "INHERITED_VALUE", "CORRECTION", "CROSSED_OUT", "MISSING_VALUE"],
      "confidence": {"quantity":"high|medium|low", "price":"high|medium|low"},
      "notes": "brief explanation"
    }
  ],
  "document_notes": ["..."]
}
Rules:
- Identify the table structure, headers, groups and line items before extracting values.
- Return one record per apparent line item. Do not merge separate rows.
- Preserve fractional quantities exactly (e.g. 1/2, 1.5, 1½); do not round.
- Preserve price exactly as written. Do not assume whether it is a unit price or line total; do not calculate totals.
- A blank field may be inherited only when there is clear visual evidence such as ditto marks, arrows, or an unambiguous grouped heading. Add INHERITED_VALUE and explain the basis in notes. Do not infer across an uncertain group boundary.
- If handwriting is ambiguous, return null for that field, add AMBIGUOUS_HANDWRITING and explain what is unclear. Do not guess.
- A readable overwrite/correction may be returned as the current value, with CORRECTION and an explanation. If unclear, return null and flag it.
- Crossed-out rows should still be returned for audit with CROSSED_OUT. Do not treat them as approved transactions.
- Capture person, site, job name, job number and date at the appropriate group level. Do not carry values into a new group unless the layout supports it.
- Use null when information is not present or cannot be read. Do not manufacture job numbers or dates.
- Use source_row to identify the visible row number; if none exists, use a stable position such as "group 2 row 3".
"""

def extract_document(image_bytes: bytes, filename: str, api_key: str, model: str = "gpt-4o"):
    client = OpenAI(api_key=api_key)
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    suffix = filename.lower().rsplit(".", 1)[-1]
    mime = "image/jpeg" if suffix in ("jpg", "jpeg") else "image/png"
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": f"Extract all line items from this inventory sheet. Source filename: {filename}"},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}", "detail": "high"}},
            ]},
        ],
    )
    content = response.choices[0].message.content
    result = json.loads(content)
    if not isinstance(result.get("line_items"), list):
        raise ValueError("Model response did not contain a line_items array.")
    return result
