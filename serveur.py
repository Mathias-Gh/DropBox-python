import socket
import threading
import time
import json
import base64
import os
from parser import ProtocolParser, ProtocolError
from network import protocol as proto
from network import state_machine as sm


class CustomServer:
    clients = []
    import socket
    import threading
    import time
    from parser import ProtocolParser, ProtocolError
    from network import protocol as proto
    from network import state_machine as sm


    class CustomServer:
        clients = []
        clients_lock = threading.Lock()

        def __init__(self):
            self.seq_mgr = sm.IntermediateStateManager()

        # Diffusion à tous les clients d'une room (utilise framing)
        def broadcast(self, message: str, room=None, sender_socket=None):
            with self.clients_lock:
                for client in self.clients:
                    if client["socket"] != sender_socket and (room is None or client["room"] == room):
                        try:
                            proto.send_message(client["socket"], message.encode())
                        except Exception:
                            pass

        # Dialogue client
        def dialoguer(self, sclient: socket.socket, adclient, callback_tchao):
            print(f"Connexion depuis {adclient}")

            pseudo = None
            room = None  # room par défaut = None

            try:
                # -------- HANDSHAKE LOGIN --------
                raw = proto.recv_message(sclient).decode()
                msg = ProtocolParser.parse(raw)

                if msg.command != "LOGIN" or len(msg.args) != 1:
                    proto.send_message(sclient, "ERROR|Pseudo requis".encode())
                    sclient.close()
                    return

                pseudo = msg.args[0]

                client_info = {
                    "socket": sclient,
                    "addr": adclient,
                    "pseudo": pseudo,
                    "room": room
                }

                with self.clients_lock:
                    self.clients.append(client_info)

                # -------- BOUCLE MESSAGES --------
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
                            data_b64 = payload.get("data", "")
                            try:
                                os.makedirs("downloads", exist_ok=True)
                                data = base64.b64decode(data_b64)
                                dst = os.path.join("downloads", f"{seq_id}_{fname}") if seq_id else os.path.join("downloads", fname)
                                with open(dst, "wb") as f:
                                    f.write(data)
                                # Notify the room that a file has been uploaded
                                self.broadcast(f"SYSTEM|{pseudo} a envoyé un fichier: {fname}", room=room_name, sender_socket=sclient)
                            except Exception:
                                try:
                                    proto.send_message(sclient, f"ERROR|Enregistrement fichier impossible".encode())
                                except Exception:
                                    pass
                            handled = True

                    if handled:
                        continue

                    msg = ProtocolParser.parse(raw.decode())

                    if msg.command == "MSG":
                        # diffuse dans la room actuelle
                        self.broadcast(f"MSG|{pseudo}|{msg.args[0]}", room=room, sender_socket=sclient)

                    elif msg.command == "ROOM":
                        old_room = room
                        room = msg.args[0]
                        with self.clients_lock:
                            for c in self.clients:
                                if c["socket"] == sclient:
                                    c["room"] = room
                        # notification système dans les rooms concernées
                        if old_room:
                            self.broadcast(f"SYSTEM|{pseudo} a quitté la room {old_room}", room=old_room)
                        self.broadcast(f"SYSTEM|{pseudo} a rejoint la room {room}", room=room, sender_socket=sclient)

                    elif msg.command == "BEGIN_SEQUENCE":
                        # Exemple minimal : début d'une séquence qui aboutira à COMPLETE
                        seq = msg.args[0] if msg.args else str(int(time.time()))
                        try:
                            self.seq_mgr.begin_sequence(seq)
                        except RuntimeError:
                            # déjà en cours
                            proto.send_message(sclient, f"ERROR|Sequence {seq} deja existante".encode())
                            continue

                        # lancer traitement asynchrone (ex: vote, confirmation fichier, ...)
                        def process_sequence(sock, seq_id, sender_pseudo):
                            # Simuler un traitement
                            time.sleep(2)
                            result = {"status": "ok"}
                            # notifier l'émetteur
                            try:
                                proto.send_message(sock, f"COMPLETE|{seq_id}|{result}".encode())
                            except Exception:
                                pass
                            self.seq_mgr.complete_sequence(seq_id, result)

                        threading.Thread(target=process_sequence, args=(sclient, seq, pseudo), daemon=True).start()

                    elif msg.command == "QUIT":
                        break

            except (ProtocolError, ConnectionResetError):
                pass

            # -------- DÉCONNEXION --------
            with self.clients_lock:
                self.clients = [c for c in self.clients if c["socket"] != sclient]

            sclient.close()
            if pseudo:
                self.broadcast(f"SYSTEM|{pseudo} a quitté le chat", room=room)
            callback_tchao(adclient)

        # Callback
        def au_revoir(self, adclient):
            print(f"Déconnexion {adclient}")

        # Démarrage serveur
        def start(self):
            sserveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sserveur.bind(("127.0.0.1", 54321))
            sserveur.listen()
            print("Serveur démarré...")

            while True:
                sclient, adclient = sserveur.accept()
                threading.Thread(
                    target=self.dialoguer,
                    args=(sclient, adclient, self.au_revoir),
                    daemon=True
                ).start()


    if __name__ == "__main__":
        srv = CustomServer()
        srv.start()
    import socket
