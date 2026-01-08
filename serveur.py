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
    clients_lock = threading.Lock()

    def __init__(self):
        self.seq_mgr = sm.IntermediateStateManager()

    # Diffusion à tous les clients d'une room (utilise framing)
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
