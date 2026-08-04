import threading

_claims = {}
_lock = threading.Lock()

def claim_job(job_id: str) -> bool:
    with _lock:
        if job_id in _claims:
            return False
        _claims[job_id] = True
        return True
