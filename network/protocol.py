"""Utilities for message framing and simple JSON messages.

Format on the wire:
  [4 bytes length (uint32 network order)] [payload bytes]
payload is UTF-8 JSON by convention.

Functions:
- send_message(sock, obj)
- recv_message(sock) -> bytes
- send_json(sock, dict)
- recv_json(sock) -> dict

This module is minimal and safe to integrate alongside existing code.
"""
import json
import struct
import socket
from typing import Any, Dict


def send_message(sock: socket.socket, payload: bytes) -> None:
    length = struct.pack("!I", len(payload))
    sock.sendall(length + payload)


def recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed while reading")
        buf.extend(chunk)
    return bytes(buf)


def recv_message(sock: socket.socket) -> bytes:
    header = recv_exact(sock, 4)
    (length,) = struct.unpack("!I", header)
    return recv_exact(sock, length)


def send_json(sock: socket.socket, obj: Dict[str, Any]) -> None:
    payload = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    send_message(sock, payload)


def recv_json(sock: socket.socket) -> Dict[str, Any]:
    data = recv_message(sock)
    return json.loads(data.decode("utf-8"))
