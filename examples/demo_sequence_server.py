"""Demo server for BEGIN_SEQUENCE / COMPLETE flow.

Run this server, then run the client in another terminal. The server uses
`network/protocol.py` to receive framed JSON messages and replies with a
`COMPLETE` message for `BEGIN_SEQUENCE` after a short delay.
"""
import socket
import threading
import time
from network import protocol as proto


HOST = "127.0.0.1"
PORT = 9000


def handle_client(conn, addr):
    print(f"Client connected: {addr}")
    try:
        while True:
            msg = proto.recv_json(conn)
            print("Received:", msg)
            t = msg.get("type")
            seq = msg.get("seq")
            if t == "BEGIN_SEQUENCE":
                # simulate processing (e.g. voting, file confirmation, ...)
                print(f"Begin sequence {seq}, processing...")
                time.sleep(2)
                resp = {"type": "COMPLETE", "seq": seq, "result": {"status": "ok"}}
                proto.send_json(conn, resp)
                print(f"Sent COMPLETE for seq {seq}")
            else:
                proto.send_json(conn, {"type": "ACK", "seq": seq})
    except Exception as e:
        print("Connection closed:", e)
    finally:
        conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f"Demo server listening on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
