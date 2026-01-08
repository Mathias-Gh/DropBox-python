"""Module de gestion du téléchargement et envoi de fichiers.

Ce module contient toutes les fonctions liées à la sélection,
l'envoi et la réception de fichiers dans les rooms.
"""

import os
import base64
import uuid
import socket
import tkinter as tk
from tkinter import filedialog
from network import protocol as proto


def pick_file():
    """Ouvre un dialogue de sélection de fichier et retourne le chemin.
    
    Returns:
        str: Le chemin du fichier sélectionné, ou None si annulé
    """
    # Créer une fenêtre tkinter invisible pour le dialogue de fichier
    root = tk.Tk()
    root.withdraw()  # Cacher la fenêtre principale
    root.attributes('-topmost', True)  # Mettre au premier plan
    
    file_path = filedialog.askopenfilename(
        title="Sélectionner un fichier",
        filetypes=[("Tous les fichiers", "*.*")]
    )
    root.destroy()
    
    return file_path if file_path else None


def send_file_to_room(sclient, room, file_path):
    """Envoie un fichier à une room spécifique.
    
    Args:
        sclient: Le socket client connecté
        room: Le nom de la room
        file_path: Le chemin du fichier à envoyer
    
    Returns:
        dict: {"success": bool, "message": str, "filename": str, "size": int}
    
    Raises:
        OSError, socket.error, ConnectionError: Si erreur de connexion
        Exception: Pour toutes autres erreurs
    """
    if not os.path.isfile(file_path):
        return {
            "success": False,
            "message": f"Fichier introuvable: {file_path}",
            "filename": None,
            "size": 0
        }
    
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        
        b64 = base64.b64encode(data).decode("ascii")
        seq_id = uuid.uuid4().hex
        filename = os.path.basename(file_path)
        
        obj = {
            "type": "SEND_FILE",
            "seq": seq_id,
            "room": room,
            "meta": {"filename": filename, "size": len(data)},
            "data": b64,
        }
        
        print(f"[TELECHARGEMENT] Envoi SEND_FILE: seq={seq_id}, room={room}, filename={filename}")
        proto.send_json(sclient, obj)
        
        return {
            "success": True,
            "message": f"Fichier envoyé avec succès",
            "filename": filename,
            "size": len(data)
        }
    except (OSError, socket.error, ConnectionError) as ex:
        print(f"[TELECHARGEMENT] Erreur envoi: {ex}")
        raise
    except Exception as ex:
        print(f"[TELECHARGEMENT] Erreur: {ex}")
        raise


def request_file_download(sclient, seq, filename):
    """Demande le téléchargement d'un fichier au serveur.
    
    Args:
        sclient: Le socket client connecté
        seq: L'identifiant de séquence du fichier
        filename: Le nom du fichier
    
    Returns:
        dict: {"success": bool, "message": str}
    
    Raises:
        OSError, socket.error, ConnectionError: Si erreur de connexion
    """
    req = {"type": "GET_FILE", "seq": seq, "filename": filename}
    try:
        proto.send_json(sclient, req)
        print(f"[TELECHARGEMENT] GET_FILE envoyé pour {filename}")
        return {
            "success": True,
            "message": f"Demande de téléchargement envoyée pour {filename}"
        }
    except (OSError, socket.error, ConnectionError) as ex:
        print(f"[TELECHARGEMENT] Erreur GET_FILE: {ex}")
        raise


def save_received_file(filename, data_b64, downloads_dir=None):
    """Sauvegarde un fichier reçu dans le dossier Téléchargements.
    
    Args:
        filename: Le nom du fichier
        data_b64: Les données encodées en base64
        downloads_dir: Répertoire de téléchargement (None = dossier Downloads Windows)
    
    Returns:
        dict: {"success": bool, "message": str, "path": str}
    """
    try:
        # Utiliser le dossier Téléchargements Windows par défaut
        if downloads_dir is None:
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        else:
            downloads_path = downloads_dir
        
        os.makedirs(downloads_path, exist_ok=True)
        
        # Décoder et sauvegarder
        data = base64.b64decode(data_b64)
        dst = os.path.join(downloads_path, filename)
        
        with open(dst, "wb") as f:
            f.write(data)
        
        print(f"[TELECHARGEMENT] Fichier reçu et sauvegardé: {dst}")
        
        return {
            "success": True,
            "message": f"Fichier enregistré avec succès",
            "path": dst
        }
    except Exception as ex:
        print(f"[TELECHARGEMENT] Erreur sauvegarde: {ex}")
        return {
            "success": False,
            "message": f"Erreur lors de la sauvegarde: {ex}",
            "path": None
        }


def handle_file_available(payload, files_by_room):
    """Traite une notification FILE_AVAILABLE.
    
    Args:
        payload: Le dictionnaire JSON du message
        files_by_room: Le dictionnaire de suivi des fichiers par room
    
    Returns:
        dict: Informations sur le fichier disponible
    """
    seq = payload.get("seq")
    meta = payload.get("meta", {})
    fname = meta.get("filename")
    uploader = payload.get("uploader")
    room_name = payload.get("room")
    
    print(f"[TELECHARGEMENT] FILE_AVAILABLE: uploader={uploader}, fname={fname}, seq={seq}, room={room_name}")
    
    # Stocker les infos du fichier pour cette room
    if room_name:
        files_by_room[room_name] = {
            "seq": seq,
            "filename": fname,
            "uploader": uploader,
        }
    
    return {
        "seq": seq,
        "filename": fname,
        "uploader": uploader,
        "room": room_name
    }


def check_socket_connection(sclient):
    """Vérifie si un socket est toujours connecté.
    
    Args:
        sclient: Le socket à vérifier
    
    Returns:
        bool: True si connecté, False sinon
    """
    if not sclient:
        return False
    
    try:
        sclient.getpeername()
        return True
    except (OSError, socket.error):
        return False
