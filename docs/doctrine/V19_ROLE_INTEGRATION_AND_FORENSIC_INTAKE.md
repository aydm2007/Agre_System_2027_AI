# V19 Role Integration and Forensic Intake

## Scope
V19 closes the next practical gap after V18 by tightening three production-facing areas:

1. making farm-finance and sector-director attention visible inside the approval workbench,
2. exposing remote-review escalation ownership for small remote farms, and
3. hardening documentary intake against hidden executable filenames and oversized compressed payloads.

## Functional changes
- The approval workbench now classifies rows as `farm` or `sector` owned, and flags items requiring `director_attention`.
- The approval inbox surfaces dedicated counts for farm finance rows and director-attention rows.
- Remote review reporting now emits `review_status`, `days_overdue`, `block_strict_finance`, and `sector_owner_role`.

## Forensic intake changes
- Filename validation rejects control characters and hidden executable double extensions such as `invoice.php.pdf`.
- XLSX container checks now reject excessive total uncompressed size in addition to VBA payloads and high compression ratios.
- Runtime attachment summary now exposes hot/archive tier counts and quarantine backend metadata.

## Expected assurance impact
- raises practical visibility for the farm finance manager and sector director,
- improves remote-farm enforcement evidence, and
- narrows the residual gap in file-upload hardening without claiming a full AV/CDR pipeline.
