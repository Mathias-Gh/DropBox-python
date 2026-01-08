import socket
import time
import random
import sys
import os

# Ensure project root is on sys.path so we can import `network` package
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from network import protocol as proto

HOST = "127.0.0.1"
PORT = 54321


def main():
    seq = str(int(time.time())) + str(random.randint(1, 999))
    msg = f"BEGIN_SEQUENCE|{seq}"
    print("Connecting to server...", HOST, PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(10)
        s.connect((HOST, PORT))
        print("Connected, sending BEGIN_SEQUENCE seq=", seq)
        proto.send_message(s, msg.encode())

        try:
            # wait for COMPLETE (server sends COMPLETE|<seq>|<result>)
            raw = proto.recv_message(s).decode()
            print("Received from server:", raw)
        except Exception as e:
            print("Error while waiting for response:", e)


if __name__ == "__main__":
    main()
