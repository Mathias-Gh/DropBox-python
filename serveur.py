import socket
import threading
from parser import ProtocolParser, ProtocolError

class CustomServer:
    clients = []
    clients_lock = threading.Lock()

    # Diffusion à tous les clients d'une room
    def broadcast(self, message, room=None, sender_socket=None):
        with self.clients_lock:
            for client in self.clients:
                # Si room est None, diffusion à tous
                if client["socket"] != sender_socket and (room is None or client["room"] == room):
                    try:
                        client["socket"].send(message.encode())
                    except:
                        pass

    # Dialogue client
    def dialoguer(self, sclient, adclient, callback_tchao):
        print(f"Connexion brute depuis {adclient}")

        pseudo = None
        room = None  # room par défaut = None

        try:
            # -------- HANDSHAKE LOGIN --------
            raw = sclient.recv(4096).decode()
            msg = ProtocolParser.parse(raw)

            if msg.command != "LOGIN" or len(msg.args) != 1:
                sclient.send("ERROR|Pseudo requis".encode())
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
                raw = sclient.recv(4096)
                if not raw:
                    break

                msg = ProtocolParser.parse(raw.decode())

                if msg.command == "MSG":
                    # diffuse dans la room actuelle
                    self.broadcast(f"MSG|{pseudo}|{msg.args[0]}", room=room)

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
