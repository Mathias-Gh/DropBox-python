import socket
import threading
import flet as ft

SERVER_IP = "127.0.0.1"
SERVER_PORT = 54321


def main(page: ft.Page):
    page.title = "Chat TCP - Flet"
    page.window_width = 500
    page.window_height = 600

    sclient = None
    pseudo = ""

    # ----------------------------
    # UI COMPONENTS
    # ----------------------------
    pseudo_field = ft.TextField(label="Pseudo", width=300)
    message_field = ft.TextField(label="Message", width=350)
    messages = ft.Column(scroll="auto", expand=True)

    status = ft.Text("Déconnecté", color="red")

    # ----------------------------
    # Réception serveur (thread)
    # ----------------------------
    def recevoir():
        while True:
            try:
                data = sclient.recv(4096).decode()
                if not data:
                    break

                parts = data.split("|")

                if parts[0] == "MSG":
                    # parts[1] = pseudo, parts[2] = message
                    messages.controls.append(ft.Text(f"{parts[1]} : {parts[2]}"))

                elif parts[0] == "SYSTEM":
                    messages.controls.append(ft.Text(parts[1], italic=True, color="grey"))

                page.update()
            except:
                break



    # ----------------------------
    # Connexion serveur
    # ----------------------------
    def connecter(e):
        nonlocal sclient, pseudo

        pseudo = pseudo_field.value.strip()
        if not pseudo:
            status.value = "Pseudo requis"
            status.color = "red"
            page.update()
            return

        try:
            sclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sclient.connect((SERVER_IP, SERVER_PORT))
        except Exception as ex:
            status.value = f"Erreur connexion: {ex}"
            status.color = "red"
            page.update()
            return

        status.value = f"Connecté en tant que {pseudo}"
        status.color = "green"

        # Message d'arrivée (simple texte, compatible serveur)
        sclient.send(f"LOGIN|{pseudo}".encode())


        threading.Thread(target=recevoir, daemon=True).start()

        page.update()

    # ----------------------------
    # Envoi message
    # ----------------------------
    def envoyer(e):
        if not sclient:
            return

        msg = message_field.value.strip()
        if not msg:
            return

        # Envoi du message réel
        sclient.send(f"MSG|{msg}".encode())

        # On peut aussi afficher directement dans notre interface
        messages.controls.append(ft.Text(f"{pseudo} : {msg}"))
        message_field.value = ""
        page.update()


    # ----------------------------
    # Layout
    # ----------------------------
    page.add(
        ft.Column(
            [
                ft.Text("Connexion", size=20, weight="bold"),
                pseudo_field,
                ft.ElevatedButton("Se connecter", on_click=connecter),
                status,
                ft.Divider(),
                ft.Text("Messages", size=18),
                messages,
                ft.Row(
                    [
                        message_field,
                        ft.ElevatedButton("Envoyer", on_click=envoyer)
                    ]
                ),
            ],
            expand=True,
        )
    )


ft.app(target=main)
