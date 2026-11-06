# Deployment strategy (prototype-to-production)

## Prototype architecture
Streamlit UI -> Python orchestration -> vision model API -> structured JSON -> deterministic validation -> human review -> XLSX/CSV export.

## Production evolution
1. Establish a labelled baseline across document layouts, handwriting quality, sites and job types.
2. Benchmark vision models against a document-intelligence/OCR alternative using field accuracy, complete-row accuracy, critical-field accuracy, latency and cost.
3. Add a client-owned job master and validate job number/name/site combinations; AI may suggest candidates but must not silently assign them.
4. Add secure storage, access controls, retention rules, encryption, secrets management and audit events.
5. Introduce duplicate detection at document and transaction level; flag likely duplicates rather than automatically deleting legitimate repeat withdrawals.
6. Integrate with ERP first through reconciled controlled imports, then assisted API import, then narrowly scoped automated posting for eligible approved records.
7. Monitor technical health, extraction quality, correction rates, backlog, allocation errors, cost and time-to-billing.
8. Keep human approval for financially material records. Reviewer corrections become evaluation examples only after governance approval; do not automatically train on them.

## Key assumptions to confirm with the client
- Does Price mean unit price or line total?
- What is the authoritative job master and who owns updates?
- Are crossed-out entries void, amended, or retained for a separate reason?
- What is the policy for ditto marks and inherited group metadata?
- What accuracy and turnaround targets are commercially meaningful?
