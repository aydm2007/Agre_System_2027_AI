# Golden V25 Notes (2026-03-16)

## What was improved
- Rebuilt `start_dev_stack.bat` to be resilient on Windows.
- Added `scripts/clean_project.bat` so `clean` is real, not a broken hook.
- Reduced noisy npm install output by using `--loglevel=error --no-audit --no-fund`.
- Added frontend `engines` hints and a `clean` script.
- Added generated launcher helpers under `scripts/windows/` instead of fragile inline `start ... cmd /k` quoting.
- Updated `.gitignore` for local gate and launcher artifacts.

## Practical result
This version is easier to start locally and less likely to fail because of missing helper scripts or broken quoting in `start_dev_stack.bat`.

## Honest status
This is a stronger developer-operability release, not a claim that every runtime/DB/frontend issue is gone.
