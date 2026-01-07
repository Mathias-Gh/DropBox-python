import threading
import time
import unittest

from network.state_machine import IntermediateStateManager


class StateMachineTest(unittest.TestCase):
    def test_begin_complete_wait(self):
        mgr = IntermediateStateManager()
        seq = "s1"
        mgr.begin_sequence(seq)
        self.assertTrue(mgr.is_pending(seq))

        # Complete from another thread after short delay
        def completer():
            time.sleep(0.1)
            mgr.complete_sequence(seq, {"ok": True})

        threading.Thread(target=completer, daemon=True).start()
        res = mgr.wait(seq, timeout=1.0)
        self.assertIsNotNone(res)
        self.assertEqual(res, {"ok": True})

    def test_timeout_wait(self):
        mgr = IntermediateStateManager()
        seq = "s2"
        mgr.begin_sequence(seq)
        # wait with small timeout -> should return None
        res = mgr.wait(seq, timeout=0.01)
        self.assertIsNone(res)


if __name__ == "__main__":
    unittest.main()
