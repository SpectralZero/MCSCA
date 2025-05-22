# core/session.py
"""
Maintains session data (user_id, role) for the logged-in user.

"""

_session_data = {
    "user_id": None,
    "role": None
}

def set_session(user_id: int, role: str) -> None:
    """
    Sets the session data with the current user's ID and role.
    """
    global _session_data
    _session_data["user_id"] = user_id
    _session_data["role"] = role

def get_session() -> dict:
    """
    1. >>>retrieves the current session data.
    2. return: A dictionary containing user_id and role.
    """
    return _session_data

def reset_session() -> None:
    """
    * clears the session data (used upon logout).
    """
    global _session_data
    _session_data = {
        "user_id": None,
        "role": None
    }
