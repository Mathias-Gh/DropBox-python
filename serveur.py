import socket
import threading
import time
import json
import base64
import os
from datetime import datetime

from parser import ProtocolParser, ProtocolError
from network import protocol as proto
from network import state_machine as sm


class CustomServer:
    def __init__(self):
        self.clients = []
        self.clients_lock = threading.Lock()
        self.on_clients_change = None  # callback UI admin
        self.seq_mgr = sm.IntermediateStateManager()

    # ------------------------
    # BROADCAST
    # ------------------------
    def broadcast(self, message, room=None, sender_socket=None):
        """Broadcast a message to all clients in a room.
        If message is a dict, sends as JSON. Otherwise sends as encoded bytes."""
        with self.clients_lock:
            print(f"[DEBUG] Broadcast: room={room}, recipients={len(self.clients)}, is_dict={isinstance(message, dict)}")
            for client in self.clients:
                # If room is specified, only send to clients in that room
                # If room is None, send to all clients except the sender
                if room is not None:
                    match = client["socket"] != sender_socket and client["room"] == room
                else:
                    match = client["socket"] != sender_socket
                    
                print(f"  - Client {client['pseudo']} (room={client['room']}): match={match}")
                if match:
                    try:
                        if isinstance(message, dict):
                            print(f"    -> Envoi JSON à {client['pseudo']}")
                            proto.send_json(client["socket"], message)
                        else:
                            print(f"    -> Envoi message à {client['pseudo']}")
                            proto.send_message(client["socket"], str(message).encode())
                    except Exception as e:
                        print(f"    -> Erreur: {e}")

    # ------------------------
    # ADMIN BROADCAST
    # ------------------------
    def send_admin_broadcast(self, message, target_type="all", target=None):
        timestamp = datetime.now().strftime("%d/%m/%Y %Hh%M")
        formatted = f"ADMIN_BROADCAST|Message du serveur le {timestamp} : {message}"

        with self.clients_lock:
            for client in self.clients:
                try:
                    if target_type == "all":
                        proto.send_message(client["socket"], formatted.encode())
                    elif target_type == "room" and client["room"] == target:
                        proto.send_message(client["socket"], formatted.encode())
                    elif target_type == "mp" and client["pseudo"] == target:
                        proto.send_message(client["socket"], formatted.encode())
                except Exception:
                    pass

    # ------------------------
    # KICK
    # ------------------------
    def kick_client(self, client_socket, pseudo=None, room=None):
        try:
            proto.send_message(
                client_socket,
                "SYSTEM|Vous avez été kické par l'administrateur".encode()
            )
            client_socket.close()
        except Exception:
            pass

        with self.clients_lock:
            self.clients = [c for c in self.clients if c["socket"] != client_socket]

        if pseudo:
            self.broadcast(f"SYSTEM|{pseudo} a été kické", room=room)

        self._notify_ui()

    # ------------------------
    # UI NOTIFY
    # ------------------------
    def _notify_ui(self):
        if self.on_clients_change:
            try:
                self.on_clients_change()
            except Exception:
                pass

    # ------------------------
    # CLIENT HANDLER
    # ------------------------
    def dialoguer(self, sclient: socket.socket, adclient, callback_tchao):
        print(f"Connexion depuis {adclient}")

        pseudo = None
        room = None

        try:
            # ---- LOGIN ----
            raw = proto.recv_message(sclient)
            msg = ProtocolParser.parse(raw.decode())

            if msg.command != "LOGIN" or len(msg.args) != 1:
                proto.send_message(sclient, "ERROR|Pseudo requis".encode())
                return

            pseudo = msg.args[0]

            client_info = {
                "socket": sclient,
                "addr": adclient,
                "pseudo": pseudo,
                "room": None,
                "last_message_time": None
            }

            with self.clients_lock:
                self.clients.append(client_info)

            self._notify_ui()

            # ---- MESSAGE LOOP ----
            while True:
                raw = proto.recv_message(sclient)
                if not raw:
                    break

                # Try JSON first (for SEND_FILE and future structured messages)
                handled = False
                try:
                    payload = json.loads(raw.decode())
                except Exception:
                    payload = None

                if payload:
                    t = payload.get("type")
                    if t == "SEND_FILE":
                        meta = payload.get("meta", {})
                        fname = meta.get("filename", "file.bin")
                        seq_id = payload.get("seq", "")
                        room_name = payload.get("room", room)
                        
                        # If room_name is still None, try to get it from client info
                        if room_name is None:
                            with self.clients_lock:
                                for c in self.clients:
                                    if c["socket"] == sclient:
                                        room_name = c["room"]
                                        break
                        
                        data_b64 = payload.get("data", "")
                        
                        print(f"[DEBUG] SEND_FILE reçu: fname={fname}, seq_id={seq_id}, room_name={room_name}, pseudo={pseudo}")
                        
                        try:
                            os.makedirs("downloads", exist_ok=True)
                            data = base64.b64decode(data_b64)
                            dst = os.path.join("downloads", f"{seq_id}_{fname}") if seq_id else os.path.join("downloads", fname)
                            with open(dst, "wb") as f:
                                f.write(data)
                            print(f"[DEBUG] Fichier sauvegardé: {dst}")
                            
                            # Notify the room that a file has been uploaded via JSON notification
                            notify = {
                                "type": "FILE_AVAILABLE",
                                "seq": seq_id,
                                "room": room_name,
                                "meta": {"filename": fname, "size": len(data)},
                                "uploader": pseudo,
                            }
                            print(f"[DEBUG] Broadcasting FILE_AVAILABLE: {notify}")
                            self.broadcast(notify, room=room_name, sender_socket=sclient)
                        except Exception as e:
                            print(f"[DEBUG] Erreur SEND_FILE: {e}")
                            try:
                                proto.send_message(sclient, f"ERROR|Enregistrement fichier impossible".encode())
                            except Exception:
                                pass
                        handled = True
                    elif t == "GET_FILE":
                        # client requests a file by seq and filename
                        seq_id = payload.get("seq", "")
                        fname = payload.get("filename") or None
                        # find file on disk
                        try:
                            candidates = []
                            if seq_id:
                                # match prefix
                                for fn in os.listdir("downloads"):
                                    if fn.startswith(seq_id + "_"):
                                        candidates.append(fn)
                            if not candidates and fname:
                                # try direct filename
                                if os.path.exists(os.path.join("downloads", fname)):
                                    candidates.append(fname)
                            if not candidates:
                                proto.send_message(sclient, f"ERROR|Fichier introuvable".encode())
                            else:
                                target = os.path.join("downloads", candidates[0])
                                with open(target, "rb") as f:
                                    data = f.read()
                                b64 = base64.b64encode(data).decode("ascii")
                                resp = {"type": "SEND_FILE", "seq": seq_id, "meta": {"filename": os.path.basename(target), "size": len(data)}, "data": b64}
                                proto.send_json(sclient, resp)
                        except Exception as e:
                            print(f"[DEBUG] Erreur GET_FILE: {e}")
                            try:
                                proto.send_message(sclient, f"ERROR|Lecture fichier impossible".encode())
                            except Exception:
                                pass
                        handled = True

                if handled:
                    continue

                msg = ProtocolParser.parse(raw.decode())

                # MESSAGE
                if msg.command == "MSG":
                    # Mettre à jour le dernier temps de message
                    with self.clients_lock:
                        for c in self.clients:
                            if c["socket"] == sclient:
                                c["last_message_time"] = datetime.now()

                    self._notify_ui()
                    # diffuse dans la room actuelle
                    self.broadcast(f"MSG|{pseudo}|{msg.args[0]}", room=room, sender_socket=sclient)

                # CHANGE ROOM
                elif msg.command == "ROOM":
                    old_room = room
                    room = msg.args[0]

                    with self.clients_lock:
                        for c in self.clients:
                            if c["socket"] == sclient:
                                c["room"] = room

                    self._notify_ui()

                    if old_room:
                        self.broadcast(
                            f"SYSTEM|{pseudo} a quitté la room {old_room}",
                            room=old_room
                        )

                    self.broadcast(
                        f"SYSTEM|{pseudo} a rejoint la room {room}",
                        room=room
                    )

                # SEQUENCE
                elif msg.command == "BEGIN_SEQUENCE":
                    seq_id = msg.args[0] if msg.args else str(int(time.time()))

                    try:
                        self.seq_mgr.begin_sequence(seq_id)
                    except RuntimeError:
                        proto.send_message(
                            sclient,
                            f"ERROR|Sequence {seq_id} déjà existante".encode()
                        )
                        continue

                    def process_sequence(sock, sid):
                        time.sleep(2)
                        result = {"status": "ok"}
                        try:
                            proto.send_message(
                                sock,
                                f"COMPLETE|{sid}|{result}".encode()
                            )
                        except Exception:
                            pass
                        self.seq_mgr.complete_sequence(sid, result)

                    threading.Thread(
                        target=process_sequence,
                        args=(sclient, seq_id),
                        daemon=True
                    ).start()

                # QUIT
                elif msg.command == "QUIT":
                    break

        except (ProtocolError, ConnectionResetError):
            pass

        # ---- DISCONNECT ----
        with self.clients_lock:
            self.clients = [c for c in self.clients if c["socket"] != sclient]

        self._notify_ui()
        sclient.close()

        if pseudo:
            self.broadcast(f"SYSTEM|{pseudo} a quitté le chat", room=room)

        callback_tchao(adclient)

    # ------------------------
    # CALLBACK
    # ------------------------
    def au_revoir(self, adclient):
        print(f"Déconnexion {adclient}")

    # ------------------------
    # SOCKET LOOP
    # ------------------------
    def _run_socket_server(self, sserveur):
        while True:
            sclient, adclient = sserveur.accept()
            threading.Thread(
                target=self.dialoguer,
                args=(sclient, adclient, self.au_revoir),
                daemon=True
            ).start()

    # ------------------------
    # START SERVER
    # ------------------------
    def start(self, with_admin_ui=True):
        sserveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sserveur.bind(("127.0.0.1", 54321))
        sserveur.listen()
        print("Serveur démarré sur 127.0.0.1:54321")

        threading.Thread(
            target=self._run_socket_server,
            args=(sserveur,),
            daemon=True
        ).start()

        if with_admin_ui:
            from admin_dashboard import start_admin_ui
            start_admin_ui(self)
        else:
            while True:
                time.sleep(1)


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 LANCEMENT DU SERVEUR TCP")
    print("=" * 60)
    print("📝 Pour lancer le serveur : python serveur.py")
    print("👤 Pour lancer un client : python client.py")
    print("=" * 60)
    print()
    
    srv = CustomServer()
    srv.start()
