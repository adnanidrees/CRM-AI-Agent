from __future__ import annotations
from typing import Any, Dict, Optional

def detect_channel(payload: Dict[str, Any]) -> str:
    obj = payload.get("object", "")
    if obj == "whatsapp_business_account":
        return "whatsapp"
    if obj == "page":
        return "messenger"
    if obj == "instagram":
        return "instagram"
    return "unknown"

def extract_routing_key(payload: Dict[str, Any]) -> Optional[str]:
    ch = detect_channel(payload)
    try:
        if ch == "whatsapp":
            entry = (payload.get("entry") or [])[0]
            change = (entry.get("changes") or [])[0]
            value = change.get("value") or {}
            meta = value.get("metadata") or {}
            return meta.get("phone_number_id")
        entry = (payload.get("entry") or [])[0]
        return entry.get("id")
    except Exception:
        return None
