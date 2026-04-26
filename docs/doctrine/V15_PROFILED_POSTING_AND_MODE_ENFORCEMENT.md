# V15 Profiled Posting and Mode Enforcement

## Purpose
This doctrine captures the V15 production contract introduced after V14 phase-2.

## 1. SIMPLE / STRICT enforcement
- Financial route trees must follow the effective farm mode.
- Admin or superuser status is not by itself a reason to re-open full finance authoring in SIMPLE.
- SIMPLE may expose posture, anomalies, approvals summary, and operational tracking only.

## 2. Profiled posting authority
- If `FarmSettings.approval_profile = strict_finance`, final posting actions require sector-final authority.
- Otherwise, governed STRICT cycle authority is sufficient.

## 3. Financial cycles covered
- supplier settlement final approve/payment
- petty cash approve/disburse/settle
- fixed asset capitalization/disposal
- fuel reconciliation approve-and-post
- rental/contract payment posting

## 4. Rationale
The project needed to close the gap between role modeling and actual posting authority. V15 narrows that gap by binding final posting paths to the farm's approval profile.
