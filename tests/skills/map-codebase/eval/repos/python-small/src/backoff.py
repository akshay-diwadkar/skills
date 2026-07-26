class BackoffPolicy:
    def schedule_retry(self) -> int:
        return 1
