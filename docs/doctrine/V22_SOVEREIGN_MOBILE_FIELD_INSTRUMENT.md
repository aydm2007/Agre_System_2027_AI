# V22: Sovereign Mobile Field Instrument Protocol

## 1. Overview
The AgriAsset Mobile Field Instrument (V21.5-FINAL) is a governed, decentralized edge agent designed for high-integrity operations in low-connectivity environments (Northern Yemen). It transcends simple data entry by acting as a first-class evidence collection and reconciliation tool.

## 2. Core Operational Pillars

### A. Governed Inbox (Axis 28)
- Navigation is non-linear and workload-driven.
- Users are presented with role-aware "Lanes" (Pending, Returned, Local Drafts).
- Prioritization is based on the system state, not user preference.

### B. AI-Enhanced Field Archaeology (Axis 29)
- All physical artifacts (field photos) undergo the **Sovereign Processing Pipeline**.
- **Auto-Clarity Pass**: Automated enhancement of brightness and contrast to ensure legibility in field environments.
- **Smart Resolution Scaling**: Dynamic scaling based on file size to optimize for bandwidth without losing forensic integrity.
- **EXIF Sanitization**: Mandatory stripping of GPS (unless enabled by policy) and camera metadata.

### C. Forensic Local Vault (Axis 23, 27)
- **Local Retention**: High-resolution originals and forensic metadata are retained locally for **7 days** post-sync to provide a physical field backup.
- **Approval Timeline**: Every record displays a visual forensic audit trail of its lifecycle (Created -> Reviewed -> Settled).

### D. GIS Stock Reconciliation (Axis 26)
- The mobile instrument is the source of truth for physical biological asset counts.
- Dedicated surfaces for location-based tree stock verification and variance reporting.

### E. Analytical Field Purity (Axis 22)
- Simple Mode surfaces must expose high-order ratios (Achievement per Worker, Burn-rate) to empower decentralized decision-making without leaking sensitive financial ledger details.

## 3. Deployment & Retention Logic
- **Sync Protocol**: Incremental Delta-sync (Axis 20) with persistent `last_synced_at` tracking.
- **Purge Logic**: Automated purge of metadata older than 30 days and media older than 7 days (post-sync verified).
