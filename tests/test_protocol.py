import socket
import threading
import unittest

from network import protocol as proto


def make_socket_pair():
    # Try to use socketpair if available
    if hasattr(socket, "socketpair"):
        a, b = socket.socketpair()
        return a, b

    # Fallback: create a real TCP connection on localhost
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    pair = {}

    def acceptor():
        s, _ = listener.accept()
        pair['server'] = s

    t = threading.Thread(target=acceptor, daemon=True)
    t.start()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))
    t.join(1)
    server = pair.get('server')
    listener.close()
    return server, client


class ProtocolTest(unittest.TestCase):
    def test_send_recv_message(self):
        s1, s2 = make_socket_pair()
        try:
            proto.send_message(s1, b"hello world")
            data = proto.recv_message(s2)
            self.assertEqual(data, b"hello world")
        finally:
            s1.close()
            s2.close()

    def test_send_recv_json(self):
        s1, s2 = make_socket_pair()
        try:
            payload = {"type": "TEST", "value": 123}
            proto.send_json(s1, payload)
            obj = proto.recv_json(s2)
            self.assertEqual(obj, payload)
        finally:
            s1.close()
            s2.close()


if __name__ == "__main__":
    unittest.main()
