import socket
import threading
import flet as ft
from network import protocol as proto
import base64
import uuid
import os
import json
from pathlib import Path
import telechargement as dl

SERVER_IP = "127.0.0.1"
SERVER_PORT = 54321


def main(page: ft.Page):
    page.title = "Chat TCP - Flet"
    page.window_width = 500
    page.window_height = 600

    sclient = None
    pseudo = ""
    room = None  # room par défaut
    
    # Tracker les fichiers disponibles par room
    files_by_room = {}  # Format: {"room1": {"seq": "...", "filename": "...", "uploader": "..."}, ...}

    pseudo_field = ft.TextField(label="Pseudo", width=300)
    messages = ft.Column(scroll="auto", expand=True)
    status = ft.Text("Déconnecté", color="red")
    message_field = ft.TextField(label="Message", width=350)

    room_buttons = ft.Row([
        ft.Button(content=ft.Text("Room 1"), on_click=lambda e: changer_room("room1")),
        ft.Button(content=ft.Text("Room 2"), on_click=lambda e: changer_room("room2")),
        ft.Button(content=ft.Text("Room 3"), on_click=lambda e: changer_room("room3")),
    ])

    # TextField pour le chemin du fichier
    file_path_field = ft.TextField(label="Chemin du fichier à envoyer", width=350, read_only=True)
    selected_file_path = None
    
    def pick_file(e=None):
        nonlocal selected_file_path
        file_path = dl.pick_file()
        
        if file_path:
            selected_file_path = file_path
            file_path_field.value = file_path
            file_path_field.color = "green"
        else:
            selected_file_path = None
            file_path_field.value = ""
            file_path_field.color = None
        page.update()
    
    def send_file_from_path(e=None):
        nonlocal sclient
        if not sclient:
            status.value = "Connectez-vous d'abord"
            status.color = "red"
            page.update()
            return
        
        # Vérifier que le socket est toujours connecté
        if not dl.check_socket_connection(sclient):
            status.value = "Connexion perdue. Reconnectez-vous."
            status.color = "red"
            sclient = None
            page.update()
            return
        
        if not room:
            status.value = "Rejoignez une room d'abord"
            status.color = "red"
            page.update()
            return
        
        path = file_path_field.value.strip() if file_path_field.value else (selected_file_path if selected_file_path else None)
        
        if not path:
            status.value = "Sélectionnez un fichier d'abord"
            status.color = "red"
            page.update()
            return
        
        try:
            result = dl.send_file_to_room(sclient, room, path)
            if result["success"]:
                messages.controls.append(ft.Text(f"** Fichier envoyé : {result['filename']} ({result['size']} octets) **", italic=True, color="green"))
                file_path_field.value = ""
                file_path_field.color = None
                selected_file_path = None
            else:
                status.value = result["message"]
                status.color = "red"
            page.update()
        except (OSError, socket.error, ConnectionError) as ex:
            status.value = f"Erreur envoi fichier: {ex}"
            status.color = "red"
            sclient = None
            page.update()
        except Exception as ex:
            status.value = f"Erreur envoi fichier: {ex}"
            status.color = "red"
            page.update()


    # ----------------------------
    # Fonctions
    # ----------------------------
    def changer_room(new_room):
        nonlocal room, sclient
        if not sclient:
            status.value = "Connectez-vous d'abord"
            status.color = "red"
            page.update()
            return
        
        # Vérifier que le socket est toujours connecté
        if not dl.check_socket_connection(sclient):
            status.value = "Connexion perdue. Reconnectez-vous."
            status.color = "red"
            sclient = None
            page.update()
            return
        
        old_room = room
        room = new_room
        try:
            proto.send_message(sclient, f"ROOM|{room}".encode())
            status.value = f"Vous êtes dans {room}"
            status.color = "blue"
            if old_room:
                messages.controls.append(ft.Text(f"** Changement de room : {old_room} -> {room} **", italic=True, color="grey"))
            else:
                messages.controls.append(ft.Text(f"** Vous êtes dans {room} **", italic=True, color="grey"))
        except (OSError, socket.error, ConnectionError) as ex:
            status.value = f"Erreur envoi room: {ex}"
            status.color = "red"
            sclient = None
            print(f"[CLIENT] Erreur changer_room: {ex}")
        
        page.update()

    def recevoir():
        nonlocal sclient
        while True:
            try:
                if not sclient:
                    break
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
                        file_info = dl.handle_file_available(payload, files_by_room)

                        def on_download_click(e, seq=file_info["seq"], fname=file_info["filename"]):
                            nonlocal sclient
                            if not dl.check_socket_connection(sclient):
                                status.value = "Connexion perdue"
                                status.color = "red"
                                sclient = None
                                page.update()
                                return
                            try:
                                dl.request_file_download(sclient, seq, fname)
                            except (OSError, socket.error, ConnectionError) as ex:
                                status.value = f"Erreur téléchargement: {ex}"
                                status.color = "red"
                                page.update()

                        messages.controls.append(ft.Row([ft.Text(f"{file_info['uploader']} a partagé : {file_info['filename']}"), ft.Button("Télécharger", on_click=on_download_click)]))
                        page.update()

                    elif t == "SEND_FILE":
                        meta = payload.get("meta", {})
                        fname = meta.get("filename")
                        data_b64 = payload.get("data", "")
                        
                        result = dl.save_received_file(fname, data_b64)
                        if result["success"]:
                            messages.controls.append(ft.Text(f"** Fichier reçu et enregistré : {result['path']} **", italic=True, color="green"))
                        else:
                            messages.controls.append(ft.Text(f"Erreur sauvegarde fichier: {result['message']}", color="red"))
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
            except (ConnectionError, OSError, socket.error) as ex:
                print(f"[CLIENT] Connexion fermée: {ex}")
                status.value = "Connexion perdue"
                status.color = "red"
                sclient = None
                page.update()
                break
            except Exception as ex:
                print(f"[CLIENT] Erreur recevoir: {ex}")
                if sclient:
                    try:
                        sclient.close()
                    except:
                        pass
                sclient = None
                status.value = "Erreur de connexion"
                status.color = "red"
                page.update()
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
            sclient.settimeout(5)  # Timeout de 5 secondes
            sclient.connect((SERVER_IP, SERVER_PORT))
            sclient.settimeout(None)  # Retirer le timeout après connexion
        except (socket.timeout, ConnectionRefusedError, OSError) as ex:
            status.value = f"Erreur connexion: {ex}"
            status.color = "red"
            sclient = None
            page.update()
            return
        except Exception as ex:
            status.value = f"Erreur connexion: {ex}"
            status.color = "red"
            if sclient:
                try:
                    sclient.close()
                except:
                    pass
            sclient = None
            page.update()
            return

        # login sans room (use framing)
        try:
            proto.send_message(sclient, f"LOGIN|{pseudo}".encode())
            status.value = f"Connecté en tant que {pseudo}"
            status.color = "green"
            threading.Thread(target=recevoir, daemon=True).start()
        except (OSError, socket.error, ConnectionError) as ex:
            status.value = f"Erreur lors de l'envoi du login: {ex}"
            status.color = "red"
            try:
                sclient.close()
            except:
                pass
            sclient = None
        
        page.update()

    def envoyer(e):
        nonlocal sclient
        if not sclient:
            status.value = "Connectez-vous d'abord"
            status.color = "red"
            page.update()
            return
        msg = message_field.value.strip()
        if not msg:
            return
        
        # Vérifier que le socket est toujours connecté
        if not dl.check_socket_connection(sclient):
            status.value = "Connexion perdue. Reconnectez-vous."
            status.color = "red"
            sclient = None
            page.update()
            return
        
        try:
            proto.send_message(sclient, f"MSG|{msg}".encode())
            message_field.value = ""
        except (OSError, socket.error, ConnectionError) as ex:
            status.value = f"Erreur envoi message: {ex}"
            status.color = "red"
            sclient = None
            print(f"[CLIENT] Erreur envoyer: {ex}")
        
        page.update()

    # Layout
    page.add(ft.Column([
        ft.Text("Connexion", size=20, weight="bold"),
        pseudo_field,
        room_buttons,
        ft.Button(content=ft.Text("Se connecter"), on_click=connecter),
        ft.Divider(),
        ft.Text("Partage de fichiers", size=18, weight="bold"),
        file_path_field,
        ft.Row([
            ft.Button(content=ft.Text("Sélectionner un fichier"), on_click=pick_file),
            ft.Button(content=ft.Text("Envoyer un fichier"), on_click=send_file_from_path),
        ]),
        status,
        ft.Divider(),
        ft.Text("Messages", size=18),
        messages,
        ft.Row([message_field, ft.Button(content=ft.Text("Envoyer"), on_click=envoyer)])
    ], expand=True))

ft.run(main)
