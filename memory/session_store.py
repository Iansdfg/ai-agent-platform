from typing import Dict, List


class SessionStore:
    def __init__(self):
        self._store: Dict[str, List[dict]] = {}

    def get_history(self, session_id: str) -> List[dict]:
        return self._store.get(session_id, [])

    def append(self, session_id: str, role: str, content: str):
        if session_id not in self._store:
            self._store[session_id] = []

        self._store[session_id].append({
            "role": role,
            "content": content
        })

    def clear(self, session_id: str):
        if session_id in self._store:
            del self._store[session_id]