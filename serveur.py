import socket
import threading
from datetime import datetime
from parser import ProtocolParser, ProtocolError
import time
from network import protocol as proto
import socket
import threading
import time
from network import state_machine as sm



class CustomServer:
    clients = []
    clients_lock = threading.Lock()
    on_clients_change = None  # Callback pour notifier l'UI admin

    def __init__(self):
        self.seq_mgr = sm.IntermediateStateManager()

    # Diffusion à tous les clients d'une room (utilise framing)
    def broadcast(self, message: str, room=None):
        with self.clients_lock:
            for client in self.clients:
                try:
                    proto.send_message(client["socket"], message.encode())
                except Exception:
                    pass

    # Envoi d'un message admin (broadcast all / room / MP)
    def send_admin_broadcast(self, message, target_type="all", target=None):
        """
        target_type: "all", "room", "mp"
        target: nom de la room ou pseudo (selon target_type)
        Envoie un message avec format spécial pour afficher une notification côté client
        """
        # Format avec date/heure pour la notification
        timestamp = datetime.now().strftime("%d/%m/%Y %Hh%M")
        formatted_msg = f"ADMIN_BROADCAST|Message du serveur le {timestamp} : {message}"
        
        with self.clients_lock:
            for client in self.clients:
                try:
                    if target_type == "all":
                        client["socket"].send(formatted_msg.encode())
                    elif target_type == "room" and client["room"] == target:
                        client["socket"].send(formatted_msg.encode())
                    elif target_type == "mp" and client["pseudo"] == target:
                        client["socket"].send(formatted_msg.encode())
                except:
                    pass

    # Kick un client
    def kick_client(self, client_socket, pseudo=None, room=None):
        """Déconnecte un client par son socket et notifie les autres"""
        try:
            # Envoyer un message de kick avant fermeture
            client_socket.send("SYSTEM|Vous avez été kické par l'administrateur".encode())
            client_socket.close()
        except:
            pass
        
        # Retirer le client de la liste
        with self.clients_lock:
            self.clients = [c for c in self.clients if c["socket"] != client_socket]
        
        # Notifier les autres clients
        if pseudo:
            kick_msg = f"SYSTEM|{pseudo} a été kické"
            self.broadcast(kick_msg, room=room)
        
        # Mettre à jour l'UI
        self._notify_ui()

    # Notifier l'UI d'un changement
    def _notify_ui(self):
        if self.on_clients_change:
            try:
                self.on_clients_change()
            except:
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
                "room": room,
                "last_message_time": None
            }

            with self.clients_lock:
                self.clients.append(client_info)
            self._notify_ui()

            # -------- BOUCLE MESSAGES --------
            while True:
                raw = proto.recv_message(sclient)
                if not raw:
                    break

                msg = ProtocolParser.parse(raw.decode())

                if msg.command == "MSG":
                    # Met à jour le timestamp du dernier message
                    with self.clients_lock:
                        for c in self.clients:
                            if c["socket"] == sclient:
                                c["last_message_time"] = datetime.now()
                    self._notify_ui()
                    # diffuse dans la room actuelle
                    self.broadcast(f"MSG|{pseudo}|{msg.args[0]}", room=room)

                elif msg.command == "ROOM":
                    old_room = room
                    room = msg.args[0]
                    with self.clients_lock:
                        for c in self.clients:
                            if c["socket"] == sclient:
                                c["room"] = room
                    self._notify_ui()
                    # notification système dans les rooms concernées
                    if old_room:
                        self.broadcast(f"SYSTEM|{pseudo} a quitté la room {old_room}", room=old_room)
                    self.broadcast(f"SYSTEM|{pseudo} a rejoint la room {room}", room=room)

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
        self._notify_ui()

        sclient.close()
        if pseudo:
            self.broadcast(f"SYSTEM|{pseudo} a quitté le chat", room=room)
        callback_tchao(adclient)

    # Callback
    def au_revoir(self, adclient):
        print(f"Déconnexion {adclient}")

    # Démarrage serveur socket (boucle accept)
    def _run_socket_server(self, sserveur):
        while True:
            sclient, adclient = sserveur.accept()
            threading.Thread(
                target=self.dialoguer,
                args=(sclient, adclient, self.au_revoir),
                daemon=True
            ).start()

    # Démarrage serveur
    def start(self, with_admin_ui=True):
        sserveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sserveur.bind(("127.0.0.1", 54321))
        sserveur.listen()
        print("Serveur démarré...")

        # Lancer le socket server dans un thread séparé
        threading.Thread(target=self._run_socket_server, args=(sserveur,), daemon=True).start()

        # Lancer l'UI admin dans le main thread (Flet nécessite le main thread)
        if with_admin_ui:
            from admin_dashboard import start_admin_ui
            start_admin_ui(self)
        else:
            # Si pas d'UI, boucle infinie pour maintenir le serveur
            import time
            while True:
                time.sleep(1)


if __name__ == "__main__":
    serveur = CustomServer()
    serveur.start()
