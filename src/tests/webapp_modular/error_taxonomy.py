"""
Error taxonomy for operational observability.
"""

from __future__ import annotations

from typing import Tuple


def classify_error(exc: Exception) -> Tuple[str, str]:
    message = str(exc).lower()
    if "sessione non trovata" in message:
        return "SESSION_NOT_FOUND", "user_input"
    if "contorno non valido" in message or "confini geografici non validi" in message:
        return "INVALID_GEOMETRY_OR_BOUNDS", "user_input"
    if "quota superata" in message:
        return "QUOTA_EXCEEDED", "business_rule"
    if "timeout" in message:
        return "JOB_TIMEOUT", "operational"
    if "cv_auto" in message and "fallback" in message:
        return "CV_AUTO_FALLBACK", "quality"
    if "impossibile" in message or "errore" in message:
        return "PROCESSING_ERROR", "processing"
    return "UNCLASSIFIED_ERROR", "unknown"
