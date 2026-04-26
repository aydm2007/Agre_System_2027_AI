# V11 Attachment Evidence Lifecycle

## Objective
Provide a governed attachment lifecycle that protects audit evidence while preventing uncontrolled storage growth.

## Attachment Classes
### `transient`
Examples:
- draft uploads
- duplicate temporary copies
- offline cache copies
- pre-approval working scans

Policy:
- may be compressed, archived, or purged after TTL
- may be replaced by a single authoritative archived copy
- default TTL suggestion: `30 days from final approval` or stricter policy value

### `operational`
Examples:
- field photos
- daily execution support evidence
- agronomy support images

Policy:
- retained per operational retention schedule
- may be summarized or archived after policy age
- not all operational evidence must remain in hot storage

### `financial_record`
Examples:
- final purchase invoice
- final sales invoice
- approved receipt/deposit evidence
- approved supplier settlement evidence
- final fixed-asset capitalization support

Policy:
- archive and retain as authoritative evidence
- do not rapidly delete after 30 days
- hot-storage copy may be replaced by archived copy plus metadata, hash, and preview

### `legal_hold`
Examples:
- disputed files
- litigation or investigation evidence
- regulator-requested holds

Policy:
- no expiry until explicit release
- purge blocked regardless of standard TTL

## Required Metadata
- evidence class
- related farm
- related workflow and entity id
- uploader and upload timestamp
- final-approval timestamp when applicable
- retention class / legal hold state
- content hash where supported
- storage tier (hot / warm / archive)

## Required Controls
- allowed extension list
- max file size by class
- storage outside unsafe public paths
- duplicate detection by hash where feasible
- preview generation separate from the authoritative file
- policy-aware purge worker
- policy-aware archive worker

## Purge Principles
- purge local cache or duplicate transient copies, not the authoritative approved record
- do not purge `financial_record` evidence merely to save storage
- archive approved evidence to cheaper storage where possible
- all purge actions must be auditable
