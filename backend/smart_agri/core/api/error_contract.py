"""
Runtime API error contract helpers.

Non-breaking payload shape:
    {
        "detail": "<human readable>",
        "code": "<optional machine code>",
        "request_id": "<optional request correlation id>"
    }
"""


def request_id_from_request(request):
    if not request:
        return None
    return (
        request.headers.get("X-Request-Id")
        or request.headers.get("X-Request-ID")
        or request.META.get("HTTP_X_REQUEST_ID")
    )


def build_error_payload(detail, *, request=None, code=None, **extra):
    payload = {"detail": detail}
    if code:
        payload["code"] = code
    request_id = request_id_from_request(request)
    if request_id:
        payload["request_id"] = request_id
    payload.update(extra)
    return payload
