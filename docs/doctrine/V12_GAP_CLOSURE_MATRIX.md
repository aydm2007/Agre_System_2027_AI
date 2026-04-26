# V12 Gap Closure Matrix

| Gap | V11 | V12 action | Expected effect |
|---|---:|---|---|
| Approval granularity | 84 | stateful multi-stage approval chain + approval history + self-approval block | high |
| Sector final approval design | 83 | sector stages encoded in service and API | high |
| Small-farm controls | 84 | RemoteReviewLog + due review command + stronger threshold semantics | medium |
| Attachment lifecycle | 81 | archive/purge commands + state fields + transition logic | high |
| File-upload hardening | 76 | file signature sniffing + MIME checks + quarantine metadata | medium |
