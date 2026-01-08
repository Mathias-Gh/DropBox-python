"""Demo client that starts a sequence and waits for COMPLETE.

Usage: run server, then run this client. It sends a `BEGIN_SEQUENCE` and waits
for a `COMPLETE` message with the same `seq`.
"""
import socket
import random
from network import protocol as proto


HOST = "127.0.0.1"
PORT = 9000


def main():
    seq = random.randint(1, 1000000)
    msg = {"type": "BEGIN_SEQUENCE", "seq": seq, "action": "VOTE", "room": "demo", "details": {}}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Connected to server {HOST}:{PORT}")
        print(f"Sending BEGIN_SEQUENCE seq={seq}")
        proto.send_json(s, msg)

        # wait for COMPLETE
        while True:
            resp = proto.recv_json(s)
            print("Received:", resp)
            if resp.get("seq") == seq and resp.get("type") == "COMPLETE":
                print("Sequence completed with result:", resp.get("result"))
                break


if __name__ == "__main__":
    main()
