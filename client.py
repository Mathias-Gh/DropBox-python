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
    room = None  # room par défaut

    pseudo_field = ft.TextField(label="Pseudo", width=300)
    messages = ft.Column(scroll="auto", expand=True)
    status = ft.Text("Déconnecté", color="red")
    message_field = ft.TextField(label="Message", width=350)

    room_buttons = ft.Row([
        ft.ElevatedButton("Room 1", on_click=lambda e: changer_room("room1")),
        ft.ElevatedButton("Room 2", on_click=lambda e: changer_room("room2")),
        ft.ElevatedButton("Room 3", on_click=lambda e: changer_room("room3")),
    ])

    # ----------------------------
    # Fonctions
    # ----------------------------
    def changer_room(new_room):
        nonlocal room
        if not sclient:
            status.value = "Connectez-vous d'abord"
            status.color = "red"
            page.update()
            return
        old_room = room
        room = new_room
        sclient.send(f"ROOM|{room}".encode())
        status.value = f"Vous êtes dans {room}"
        status.color = "blue"
        if old_room:
            messages.controls.append(ft.Text(f"** Changement de room : {old_room} -> {room} **", italic=True, color="grey"))
        else:
            messages.controls.append(ft.Text(f"** Vous êtes dans {room} **", italic=True, color="grey"))
        page.update()

    def recevoir():
        while True:
            try:
                data = sclient.recv(4096).decode()
                if not data:
                    break
                parts = data.split("|")
                if parts[0] == "MSG":
                    messages.controls.append(ft.Text(f"{parts[1]} : {parts[2]}"))
                elif parts[0] == "SYSTEM":
                    messages.controls.append(ft.Text(parts[1], italic=True, color="grey"))
                page.update()
            except:
                break

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

        # login sans room
        sclient.send(f"LOGIN|{pseudo}".encode())
        status.value = f"Connecté en tant que {pseudo}"
        status.color = "green"
        threading.Thread(target=recevoir, daemon=True).start()
        page.update()

    def envoyer(e):
        if not sclient:
            return
        msg = message_field.value.strip()
        if not msg:
            return
        sclient.send(f"MSG|{msg}".encode())
        message_field.value = ""
        page.update()

    # Layout
    page.add(ft.Column([
        ft.Text("Connexion", size=20, weight="bold"),
        pseudo_field,
        room_buttons,
        ft.ElevatedButton("Se connecter", on_click=connecter),
        status,
        ft.Divider(),
        ft.Text("Messages", size=18),
        messages,
        ft.Row([message_field, ft.ElevatedButton("Envoyer", on_click=envoyer)])
    ], expand=True))

ft.app(target=main)
