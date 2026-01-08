import socket
import threading
import flet as ft
from network import protocol as proto

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
                elif parts[0] == "ADMIN_BROADCAST":
                    # Afficher une notification/dialog pour les messages admin
                    admin_message = parts[1] if len(parts) > 1 else "Message du serveur"
                    
                    def close_notification(e):
                        notification_dialog.open = False
                        page.update()
                    
                    notification_dialog = ft.AlertDialog(
                        modal=True,
                        title=ft.Row([
                            ft.Icon(ft.Icons.CAMPAIGN, color=ft.Colors.ORANGE_400),
                            ft.Text("📢 Notification Admin", weight=ft.FontWeight.BOLD),
                        ]),
                        content=ft.Container(
                            content=ft.Text(admin_message, size=14, color=ft.Colors.BLACK),
                            padding=10,
                            bgcolor=ft.Colors.AMBER_100,
                            border_radius=8,
                        ),
                        actions=[
                            ft.ElevatedButton(
                                "OK",
                                on_click=close_notification,
                                bgcolor=ft.Colors.BLUE_700,
                                color=ft.Colors.WHITE,
                            ),
                        ],
                        actions_alignment=ft.MainAxisAlignment.CENTER,
                    )
                    
                    page.overlay.append(notification_dialog)
                    notification_dialog.open = True
                    
                    # les messages sont ajouté dans le chat pour historique
                    messages.controls.append(
                        ft.Text(f"🔔 {admin_message}", italic=True, color="orange", weight=ft.FontWeight.BOLD)
                    )
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
        status,
        ft.Divider(),
        ft.Text("Messages", size=18),
        messages,
        ft.Row([message_field, ft.ElevatedButton(content=ft.Text("Envoyer"), on_click=envoyer)])
    ], expand=True))

ft.app(target=main)
