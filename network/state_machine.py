"""Simple state machine manager for intermediate sequences (Story 6).

This provides a blocking wait API (synchronous) and a non-blocking check API.
It is intentionally lightweight so it can be integrated in threaded or asyncio apps.
"""
import threading
import time
from typing import Dict, Optional


class SequenceEntry:
    def __init__(self, seq_id: str):
        self.seq_id = seq_id
        self.event = threading.Event()
        self.result = None
        self.created_at = time.time()


class IntermediateStateManager:
    """Manage sequences that block senders until completion.

    Usage:
      mgr = IntermediateStateManager()
      mgr.begin_sequence('42')
      # elsewhere, when COMPLETE arrives:
      mgr.complete_sequence('42', result={'status':'ok'})
      # sender can wait:
      res = mgr.wait('42', timeout=30)
    """

    def __init__(self):
        self._seqs: Dict[str, SequenceEntry] = {}
        self._lock = threading.Lock()

    def begin_sequence(self, seq_id: str) -> None:
        with self._lock:
            if seq_id in self._seqs:
                raise RuntimeError(f"sequence {seq_id} already exists")
            self._seqs[seq_id] = SequenceEntry(seq_id)

    def complete_sequence(self, seq_id: str, result: Optional[dict] = None) -> None:
        with self._lock:
            ent = self._seqs.get(seq_id)
            if not ent:
                return
            ent.result = result
            ent.event.set()
            # keep entry for short time; cleanup can remove it later

    def wait(self, seq_id: str, timeout: Optional[float] = None) -> Optional[dict]:
        ent = None
        with self._lock:
            ent = self._seqs.get(seq_id)
        if not ent:
            raise KeyError(f"unknown sequence {seq_id}")
        finished = ent.event.wait(timeout=timeout)
        res = ent.result if finished else None
        # cleanup after wait
        with self._lock:
            self._seqs.pop(seq_id, None)
        return res

    def is_pending(self, seq_id: str) -> bool:
        with self._lock:
            return seq_id in self._seqs
