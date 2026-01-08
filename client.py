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

    # Text input for file path (no FilePicker to avoid compatibility issues)
    file_path_field = ft.TextField(label="Chemin du fichier à envoyer", width=350)

    def send_file_from_path(e=None):
        nonlocal sclient
        if not sclient:
            status.value = "Connectez-vous d'abord"
            status.color = "red"
            page.update()
            return
        if not room:
            status.value = "Rejoignez une room d'abord"
            status.color = "red"
            page.update()
            return
        path = file_path_field.value.strip()
        if not path:
            status.value = "Chemin vide"
            status.color = "red"
            page.update()
            return
        if not os.path.isfile(path):
            status.value = f"Fichier introuvable: {path}"
            status.color = "red"
            page.update()
            return
        try:
            with open(path, "rb") as f:
                b = f.read()
            b64 = base64.b64encode(b).decode("ascii")
            seq_id = uuid.uuid4().hex
            obj = {
                "type": "SEND_FILE",
                "seq": seq_id,
                "room": room,
                "meta": {"filename": os.path.basename(path), "size": len(b)},
                "data": b64,
            }
            print(f"[CLIENT] Envoi SEND_FILE: seq={seq_id}, room={room}, filename={os.path.basename(path)}")
            proto.send_json(sclient, obj)
            messages.controls.append(ft.Text(f"** Fichier envoyé : {os.path.basename(path)} ({len(b)} octets) **", italic=True, color="green"))
            file_path_field.value = ""
            page.update()
        except Exception as ex:
            status.value = f"Erreur envoi fichier: {ex}"
            status.color = "red"
            page.update()
            print(f"[CLIENT] Erreur: {ex}")


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
                raw = proto.recv_message(sclient)
                if not raw:
                    break
                text = None
                try:
                    payload = json.loads(raw.decode())
                except Exception as e:
                    payload = None
                    print(f"[CLIENT] Erreur JSON decode: {e}")

                if payload:
                    t = payload.get("type")
                    print(f"[CLIENT] Reçu: type={t}, payload={payload}")
                    if t == "FILE_AVAILABLE":
                        seq = payload.get("seq")
                        meta = payload.get("meta", {})
                        fname = meta.get("filename")
                        uploader = payload.get("uploader")
                        print(f"[CLIENT] FILE_AVAILABLE: uploader={uploader}, fname={fname}, seq={seq}")

                        def on_download_click(e, seq=seq, fname=fname):
                            req = {"type": "GET_FILE", "seq": seq, "filename": fname}
                            try:
                                proto.send_json(sclient, req)
                                print(f"[CLIENT] GET_FILE envoyé pour {fname}")
                            except Exception as ex:
                                print(f"[CLIENT] Erreur GET_FILE: {ex}")

                        messages.controls.append(ft.Row([ft.Text(f"{uploader} a partagé : {fname}"), ft.ElevatedButton("Télécharger", on_click=on_download_click)]))
                        page.update()

                    elif t == "SEND_FILE":
                        meta = payload.get("meta", {})
                        fname = meta.get("filename")
                        data_b64 = payload.get("data", "")
                        try:
                            os.makedirs("downloads_client", exist_ok=True)
                            data = base64.b64decode(data_b64)
                            dst = os.path.join("downloads_client", fname)
                            with open(dst, "wb") as f:
                                f.write(data)
                            print(f"[CLIENT] Fichier reçu et sauvegardé: {dst}")
                            messages.controls.append(ft.Text(f"** Fichier reçu et enregistré : {dst} **", italic=True, color="green"))
                            page.update()
                        except Exception as ex:
                            print(f"[CLIENT] Erreur sauvegarde: {ex}")
                            messages.controls.append(ft.Text(f"Erreur sauvegarde fichier: {ex}", color="red"))
                            page.update()

                    else:
                        text = str(payload)

                else:
                    text = raw.decode()

                if text:
                    parts = text.split("|")
                    if parts[0] == "MSG":
                        messages.controls.append(ft.Text(f"{parts[1]} : {parts[2]}"))
                    elif parts[0] == "SYSTEM":
                        messages.controls.append(ft.Text(parts[1], italic=True, color="grey"))
                    page.update()
            except Exception as ex:
                print(f"[CLIENT] Erreur recevoir: {ex}")
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
        file_path_field,
        ft.ElevatedButton(content=ft.Text("Envoyer un fichier"), on_click=send_file_from_path),
        status,
        ft.Divider(),
        ft.Text("Messages", size=18),
        messages,
        ft.Row([message_field, ft.ElevatedButton(content=ft.Text("Envoyer"), on_click=envoyer)])
    ], expand=True))

ft.app(target=main)
