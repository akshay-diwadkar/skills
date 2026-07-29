from __future__ import annotations


class PaymentAttemptRepository:
    def __init__(self) -> None:
        self._attempts: set[str] = set()

    def reserve(self, attempt_key: str) -> bool:
        if attempt_key in self._attempts:
            return False
        self._attempts.add(attempt_key)
        return True
