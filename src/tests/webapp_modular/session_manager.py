"""
📋 Session Manager Module
Gestione delle sessioni utente in memoria

Author: Map to GeoJSON Converter Project
"""

from typing import Dict
import os

# Storage sessioni (in memoria)
sessions: Dict[str, Dict] = {}


def get_session(session_id: str) -> Dict:
    """Recupera una sessione per ID"""
    return sessions.get(session_id)


def create_session(session_id: str, data: Dict) -> None:
    """Crea una nuova sessione"""
    sessions[session_id] = data


def delete_session(session_id: str) -> bool:
    """Elimina una sessione e i file temporanei associati"""
    if session_id in sessions:
        try:
            file_path = sessions[session_id].get("file_path")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass
        del sessions[session_id]
        return True
    return False


def session_exists(session_id: str) -> bool:
    """Verifica se una sessione esiste"""
    return session_id in sessions


def get_all_sessions() -> Dict[str, Dict]:
    """Restituisce tutte le sessioni attive"""
    return sessions


def clear_all_sessions() -> int:
    """Elimina tutte le sessioni e restituisce il conteggio"""
    count = len(sessions)
    for session_id in list(sessions.keys()):
        delete_session(session_id)
    return count
