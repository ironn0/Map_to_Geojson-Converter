"""
📋 Session Manager Module
Gestione delle sessioni utente in memoria

Author: Map to GeoJSON Converter Project
"""

import os
import threading
import time
from typing import Dict, Optional

from config import SESSION_TTL_SECONDS

# Storage sessioni (in memoria)
sessions: Dict[str, Dict] = {}
session_lock = threading.RLock()

_META_CREATED = "_created_ts"
_META_LAST_ACCESS = "_last_access_ts"
_META_EXPIRES_AT = "_expires_at_ts"


def _now() -> float:
    return time.time()


def _attach_metadata(session_data: Dict) -> Dict:
    now = _now()
    session_data[_META_CREATED] = now
    session_data[_META_LAST_ACCESS] = now
    session_data[_META_EXPIRES_AT] = now + SESSION_TTL_SECONDS
    return session_data


def _touch(session_data: Dict) -> None:
    now = _now()
    session_data[_META_LAST_ACCESS] = now
    session_data[_META_EXPIRES_AT] = now + SESSION_TTL_SECONDS


def _is_expired(session_data: Dict) -> bool:
    expires_at = float(session_data.get(_META_EXPIRES_AT, 0))
    return expires_at > 0 and _now() > expires_at


def _delete_session_unlocked(session_id: str) -> bool:
    if session_id not in sessions:
        return False
    try:
        file_path = sessions[session_id].get("file_path")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    del sessions[session_id]
    return True


def prune_expired_sessions() -> int:
    """Rimuove sessioni scadute e restituisce quante sono state eliminate."""
    deleted = 0
    with session_lock:
        expired_ids = [sid for sid, data in sessions.items() if _is_expired(data)]
        for session_id in expired_ids:
            if _delete_session_unlocked(session_id):
                deleted += 1
    return deleted


def get_session(session_id: str) -> Optional[Dict]:
    """Recupera una sessione per ID"""
    prune_expired_sessions()
    with session_lock:
        data = sessions.get(session_id)
        if data is None:
            return None
        _touch(data)
        return data


def create_session(session_id: str, data: Dict) -> None:
    """Crea una nuova sessione"""
    prune_expired_sessions()
    with session_lock:
        sessions[session_id] = _attach_metadata(data)


def delete_session(session_id: str) -> bool:
    """Elimina una sessione e i file temporanei associati"""
    with session_lock:
        return _delete_session_unlocked(session_id)


def session_exists(session_id: str) -> bool:
    """Verifica se una sessione esiste"""
    return get_session(session_id) is not None


def get_all_sessions() -> Dict[str, Dict]:
    """Restituisce tutte le sessioni attive"""
    prune_expired_sessions()
    with session_lock:
        return dict(sessions)


def clear_all_sessions() -> int:
    """Elimina tutte le sessioni e restituisce il conteggio"""
    with session_lock:
        ids = list(sessions.keys())
    for session_id in ids:
        delete_session(session_id)
    return len(ids)
