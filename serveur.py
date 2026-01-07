import socket
import threading
from parser import ProtocolParser, ProtocolError


class CustomServer:
    clients = []
    clients_lock = threading.Lock()

    # ----------------------------
    # Diffusion à tous sauf l'envoyeur
    # ----------------------------
    def broadcast(self, message, sender_socket=None):
        with self.clients_lock:
            for client in self.clients:
                if client["socket"] != sender_socket:  # ne pas renvoyer au même client
                    try:
                        client["socket"].send(message.encode())
                    except:
                        pass

    # ----------------------------
    # Dialogue client
    # ----------------------------
    def dialoguer(self, sclient, adclient, callback_tchao):
        print(f"Connexion brute depuis {adclient}")

        try:
            # -------- HANDSHAKE LOGIN --------
            raw = sclient.recv(4096).decode()
            msg = ProtocolParser.parse(raw)

            if msg.command != "LOGIN" or len(msg.args) != 1:
                sclient.send("ERROR|LOGIN requis".encode())
                sclient.close()
                return

            pseudo = msg.args[0]

            client_info = {
                "socket": sclient,
                "addr": adclient,
                "pseudo": pseudo
            }

            with self.clients_lock:
                self.clients.append(client_info)

            print(f"{pseudo} connecté")
            self.broadcast(f"SYSTEM|{pseudo} a rejoint le chat", sender_socket=sclient)

            # -------- BOUCLE MESSAGES --------
            while True:
                raw = sclient.recv(4096)
                if not raw:
                    break

                msg = ProtocolParser.parse(raw.decode())

                if msg.command == "MSG":
                    self.broadcast(f"MSG|{pseudo}|{msg.args[0]}", sender_socket=sclient)

                elif msg.command == "QUIT":
                    break

        except (ProtocolError, ConnectionResetError):
            pass

        # -------- DÉCONNEXION --------
        with self.clients_lock:
            self.clients = [
                c for c in self.clients if c["socket"] != sclient
            ]

        sclient.close()
        self.broadcast(f"SYSTEM|{pseudo} a quitté le chat", sender_socket=sclient)
        callback_tchao(adclient)

    # ----------------------------
    def au_revoir(self, adclient):
        print(f"Déconnexion {adclient}")

    # ----------------------------
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
