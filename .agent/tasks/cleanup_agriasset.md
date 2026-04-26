# AgriAsset Verification & Cleanup Protocol
**Standard**: Agri-Guardian Protocol Zero
**Strictness**: 100/100

## 1. File System Hygiene
- [x] **Purge Backup Files**: Delete all `*.bak`, `*.old`, `*.tmp` files.
- [x] **Clear Python Cache**: Remove `__pycache__` directories.
- [ ] **Verify Artifacts**: Ensure no `todo.md` or temp notes are left in source roots.

## 2. Database Hygiene (Schema Sentinel)
- [x] **Run Zombie Detector**:
    ```bash
    python .agent/skills/schema_sentinel/scripts/detect_zombies.py
    ```
    *Must accept Exit Code 0 only.*

## 3. Localization Audit (The Auditor)
- [ ] **Scan for Hardcoded English**:
    *   Grep for `ValidationError("` followed by English text.
    *   Grep for `throw new Error("` followed by English text (Frontend).
- [ ] **Verify Arabization**: Ensure key Service docstrings are in Arabic.

## 4. Operational Check
- [ ] **Dependency Check**: Verify `package.json` matches `node_modules` (e.g. `dexie`).
- [ ] **Test Suite**: Run `vitest` to ensure no regression.

---
*Authorized by Agri-Guardian AI*
