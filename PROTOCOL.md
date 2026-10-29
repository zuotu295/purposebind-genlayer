# Protocol

## Input and bounds

`payload` has exactly `purpose`, `requirements`, `fields`. Purpose is 20–1000 characters; 1–4 distinct requirement strings each 12–400 characters; 2–6 field objects each with exactly `id` and `description` (20–600 characters). IDs are unique, 1–40 ASCII letters/digits/hyphen/underscore. JSON payload is at most 7000 characters. Text is stripped before storage; accepted text is not truncated. Recipient must be a nonzero hexadecimal address distinct from owner. Addresses are lowercased.

One accepted consensus matrix contains one cell for each field/requirement pair in field-major order. Fields and requirements cannot be omitted, reordered or duplicated. Labels are YES/NO/UNKNOWN. Quotes are 8–300 exact characters from their respective source strings; reason is 12–350 characters. Validator reruns the same classification independently, compares every label, then separately audits all proposed quotations against original metadata. Only literal boolean true passes the audit. Schema-only validation is insufficient. No requirement for identical explanation wording exists.

## Cover calculation

Each YES edge connects a field to a requirement it independently satisfies. A cover is a nonempty field subset whose union reaches every requirement. Enumerate masks 1 through 2^N−1, count set bits and retain all covers of minimum cardinality. Field order within each option follows catalog order; option order follows numeric mask order.

Compute a second optimistic minimum allowing UNKNOWN as well as YES. If that optimistic minimum is smaller than the confirmed minimum, or no confirmed cover exists but an optimistic one does, return REVIEW with no options. If even the optimistic matrix has no cover, return UNSATISFIABLE. Otherwise return READY and all confirmed minimum covers. This proves a cardinality optimum only under the accepted matrix, not that the descriptions match a real dataset.

## Commitments

Canonicalization is Python `json.dumps(value, sort_keys=True, separators=(",", ":"))`, including its default ASCII escaping. SHA-256 covers the UTF-8 bytes.

`input_digest` binds `{owner, id, recipient, input}`. `grant_digest` binds `{input_digest, cells, options, status}` at assessment. After claim, the digest remains the READY-state commitment and the record adds selected fields and CLAIMED status. Recompute using READY when checking a CLAIMED record. The digest alone does not prove a signature or a claim; read authenticated finalized state.

## Integration

A data service should fix a trusted deployment source digest and check its finality, protocol, exact catalog owner, intended recipient, input digest, grant digest, CLAIMED status and selected canonical option. Recalculate cover arithmetic if implementing an independent client. Verify the caller controls the recipient wallet outside this public read API. Neither the claim nor this specification grants underlying data rights. Never release a dataset based on an arbitrary user-supplied deployment or a JSON file alone.

All writes use zero value and full consensus (`leaderOnly:false`). Preserve a returned transaction hash before polling. A FINALIZED status must be accompanied by MAJORITY_AGREE, successful leader execution and matching state readback. Unknown send outcomes remain locked. A failure must be inspected before a new explicit attempt; no automatic resend or Appeal is provided.
