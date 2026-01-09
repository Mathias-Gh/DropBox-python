import socket
import threading
import time
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
    def broadcast(self, message: str, room=None):
        """Diffuse un message à tous les clients ou à une room"""
        with self.clients_lock:
            for client in self.clients:
                if room is None or client["room"] == room:
                    try:
                        proto.send_message(client["socket"], message.encode())
                    except Exception:
                        pass

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

        self.command_handlers = {
            "MSG": self.handle_msg,
            "ROOM": self.handle_room,
            "QUIT": self.handle_quit,
        }


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

                msg = ProtocolParser.parse(raw.decode())

                handler = self.command_handlers.get(msg.command)
                if not handler:
                    proto.send_message(sclient, b"ERROR|Commande inconnue")
                    continue

                should_quit = handler(sclient, msg, client_info)
                if should_quit:
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
        sserveur.bind(("10.160.32.75", 54321))
        sserveur.listen()
        print("Serveur démarré sur 10.160.32.75 :54321")

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
    serveur = CustomServer()
    serveur.start()
