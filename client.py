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
import socket
import threading
import flet as ft
from network import protocol as proto
import base64
import uuid
import os
import json

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
        ft.ElevatedButton(content=ft.Text("Room 1"), on_click=lambda e: changer_room("room1")),
        ft.ElevatedButton(content=ft.Text("Room 2"), on_click=lambda e: changer_room("room2")),
        ft.ElevatedButton(content=ft.Text("Room 3"), on_click=lambda e: changer_room("room3")),
    ])

    # File picker for sending files (may not be available in older flet)
    file_picker = None
    file_path_field = None
    def on_file_result(e: ft.FilePickerResultEvent):
        nonlocal sclient
        if not sclient:
            status.value = "Connectez-vous d'abord"
            status.color = "red"
            page.update()
            return
        if not e.files:
            return
        path = e.files[0].path
        try:
            with open(path, "rb") as f:
                b = f.read()
            b64 = base64.b64encode(b).decode("ascii")
            obj = {
                "type": "SEND_FILE",
                "seq": uuid.uuid4().hex,
                "room": room,
                "meta": {"filename": os.path.basename(path), "size": len(b)},
                "data": b64,
            }
            proto.send_json(sclient, obj)
            messages.controls.append(ft.Text(f"** Fichier envoyé : {os.path.basename(path)} ({len(b)} octets) **", italic=True, color="green"))
            page.update()
        except Exception as ex:
            status.value = f"Erreur envoi fichier: {ex}"
            status.color = "red"
            page.update()

    file_picker.on_result = on_file_result

    # If FilePicker control is not available in this flet version, provide a fallback
    try:
        if file_picker is None:
            file_picker = ft.FilePicker()
            page.overlay.append(file_picker)
            file_picker.on_result = on_file_result
    except Exception:
        # Fallback UI: text field to paste a path and a button to send
        file_path_field = ft.TextField(label="Chemin fichier (fallback)", width=300)

        def send_file_from_path(e=None):
            nonlocal sclient
            if not sclient:
                status.value = "Connectez-vous d'abord"
                status.color = "red"
                page.update()
                return
            path = file_path_field.value
            if not path or not os.path.isfile(path):
                status.value = "Chemin invalide"
                status.color = "red"
                page.update()
                return
            try:
                with open(path, "rb") as f:
                    b = f.read()
                b64 = base64.b64encode(b).decode("ascii")
                obj = {
                    "type": "SEND_FILE",
                    "seq": uuid.uuid4().hex,
                    "room": room,
                    "meta": {"filename": os.path.basename(path), "size": len(b)},
                    "data": b64,
                }
                proto.send_json(sclient, obj)
                messages.controls.append(ft.Text(f"** Fichier envoyé : {os.path.basename(path)} ({len(b)} octets) **", italic=True, color="green"))
                page.update()
            except Exception as ex:
                status.value = f"Erreur envoi fichier: {ex}"
                status.color = "red"
                page.update()


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
        proto.send_message(sclient, f"ROOM|{room}".encode())
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
                data = proto.recv_message(sclient).decode()
                if not data:
                    break
                parts = data.split("|")
                if parts[0] == "MSG":
                    messages.controls.append(ft.Text(f"{parts[1]} : {parts[2]}"))
                elif parts[0] == "SYSTEM":
                    messages.controls.append(ft.Text(parts[1], italic=True, color="grey"))
                page.update()
            except Exception:
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

        # login sans room (use framing)
        proto.send_message(sclient, f"LOGIN|{pseudo}".encode())
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
        proto.send_message(sclient, f"MSG|{msg}".encode())
        message_field.value = ""
        page.update()

    # Layout
    page.add(ft.Column([
        ft.Text("Connexion", size=20, weight="bold"),
        pseudo_field,
        room_buttons,
        ft.ElevatedButton(content=ft.Text("Se connecter"), on_click=connecter),
        ft.ElevatedButton(content=ft.Text("Envoyer un fichier"), on_click=lambda e: (file_picker.pick_files() if file_picker else send_file_from_path(e))),
        status,
        ft.Row([file_path_field, ft.ElevatedButton(content=ft.Text("Envoyer (path)"), on_click=send_file_from_path)]) if file_path_field else ft.Container(),
        ft.Divider(),
        ft.Text("Messages", size=18),
        messages,
        ft.Row([message_field, ft.ElevatedButton(content=ft.Text("Envoyer"), on_click=envoyer)])
    ], expand=True))

ft.app(target=main)
