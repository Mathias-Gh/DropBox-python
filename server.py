"""
Serveur DropBox avec dashboard admin Flet
Gère les connexions clients et fournit une interface d'administration
"""

import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class Client:
    """Représente un client connecté"""
    pseudo: str
    address: tuple
    socket: socket.socket
    connected_at: datetime = field(default_factory=datetime.now)
    current_room: Optional[str] = None
    
    def connection_duration(self) -> str:
        """Retourne la durée de connexion formatée"""
        delta = datetime.now() - self.connected_at
        minutes, seconds = divmod(int(delta.total_seconds()), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


class DropBoxServer:
    """Serveur TCP pour gérer les connexions clients DropBox"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[str, Client] = {}  # pseudo -> Client
        self.rooms: Dict[str, List[str]] = {}  # room_name -> [pseudo, ...]
        self.running = False
        self.lock = threading.Lock()
        self._listeners: List[callable] = []
        
        # Rooms par défaut
        self.available_rooms = ["General", "Tech", "Random", "Music", "Gaming"]
    
    def add_listener(self, callback: callable):
        """Ajoute un listener pour les événements du serveur"""
        self._listeners.append(callback)
    
    def _notify_listeners(self, event: str, data: dict = None):
        """Notifie tous les listeners d'un événement"""
        for listener in self._listeners:
            try:
                listener(event, data or {})
            except Exception as e:
                print(f"Erreur listener: {e}")
    
    def start(self):
        """Démarre le serveur en arrière-plan"""
        if self.running:
            return
        
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.running = True
        
        # Thread pour accepter les connexions
        thread = threading.Thread(target=self._accept_connections, daemon=True)
        thread.start()
        
        self._notify_listeners("server_started", {"host": self.host, "port": self.port})
    
    def stop(self):
        """Arrête le serveur"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # Déconnecter tous les clients
        with self.lock:
            for pseudo in list(self.clients.keys()):
                self._disconnect_client(pseudo)
        
        self._notify_listeners("server_stopped", {})
    
    def _accept_connections(self):
        """Accepte les connexions entrantes"""
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, address = self.server_socket.accept()
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Erreur accept: {e}")
                break
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """Gère un client connecté"""
        pseudo = None
        try:
            while self.running:
                data = client_socket.recv(4096).decode('utf-8').strip()
                if not data:
                    break
                
                response = self._process_command(data, client_socket, address, pseudo)
                
                # Mettre à jour le pseudo si LOGIN réussi
                if data.startswith("LOGIN") and response.startswith("DISPLAY_ROOM"):
                    parts = data.split('"')
                    if len(parts) >= 2:
                        pseudo = parts[1]
                
                client_socket.send(f"{response}\n".encode('utf-8'))
                
        except Exception as e:
            print(f"Erreur client {address}: {e}")
        finally:
            if pseudo:
                self._disconnect_client(pseudo)
            client_socket.close()
    
    def _process_command(self, data: str, client_socket: socket.socket, 
                         address: tuple, current_pseudo: str) -> str:
        """Traite une commande client"""
        parts = data.split('"')
        command = data.split()[0] if data else ""
        
        if command == "LOGIN":
            if len(parts) >= 2:
                pseudo = parts[1]
                return self._handle_login(pseudo, client_socket, address)
            return "KO"
        
        elif command == "JOIN_ROOM":
            if len(parts) >= 2:
                room = parts[1]
                return self._handle_join_room(current_pseudo, room)
            return "KO"
        
        elif command == "MSG":
            if len(parts) >= 6:
                room, pseudo_msg, msg = parts[1], parts[3], parts[5]
                return self._handle_message(room, pseudo_msg, msg)
            return "KO"
        
        elif command == "BYE":
            if len(parts) >= 4:
                room, pseudo_bye = parts[1], parts[3]
                return self._handle_bye(room, pseudo_bye)
            return "KO"
        
        return "KO"
    
    def _handle_login(self, pseudo: str, client_socket: socket.socket, 
                      address: tuple) -> str:
        """Gère la connexion d'un client"""
        with self.lock:
            if pseudo in self.clients:
                return "KO"
            
            client = Client(
                pseudo=pseudo,
                address=address,
                socket=client_socket
            )
            self.clients[pseudo] = client
        
        self._notify_listeners("client_connected", {"pseudo": pseudo, "address": address})
        
        # Retourner les rooms disponibles
        rooms_str = ' '.join(f'"{r}"' for r in self.available_rooms)
        return f"DISPLAY_ROOM {rooms_str}"
    
    def _handle_join_room(self, pseudo: str, room: str) -> str:
        """Gère l'entrée dans une room"""
        with self.lock:
            if pseudo not in self.clients:
                return "KO"
            if room not in self.available_rooms:
                return "KO"
            
            # Quitter l'ancienne room
            old_room = self.clients[pseudo].current_room
            if old_room and old_room in self.rooms:
                if pseudo in self.rooms[old_room]:
                    self.rooms[old_room].remove(pseudo)
            
            # Rejoindre la nouvelle room
            if room not in self.rooms:
                self.rooms[room] = []
            self.rooms[room].append(pseudo)
            self.clients[pseudo].current_room = room
        
        self._notify_listeners("client_joined_room", {"pseudo": pseudo, "room": room})
        return "OK"
    
    def _handle_message(self, room: str, pseudo: str, msg: str) -> str:
        """Gère l'envoi d'un message"""
        with self.lock:
            if room not in self.rooms:
                return "KO"
            if pseudo not in self.clients:
                return "KO"
        
        self._notify_listeners("message_sent", {"room": room, "pseudo": pseudo, "message": msg})
        return "OK"
    
    def _handle_bye(self, room: str, pseudo: str) -> str:
        """Gère la déconnexion d'une room"""
        with self.lock:
            if room in self.rooms and pseudo in self.rooms[room]:
                self.rooms[room].remove(pseudo)
            if pseudo in self.clients:
                self.clients[pseudo].current_room = None
        
        self._notify_listeners("client_left_room", {"pseudo": pseudo, "room": room})
        return "OK"
    
    def _disconnect_client(self, pseudo: str):
        """Déconnecte un client"""
        with self.lock:
            if pseudo in self.clients:
                client = self.clients[pseudo]
                try:
                    client.socket.close()
                except:
                    pass
                
                # Retirer de toutes les rooms
                for room_members in self.rooms.values():
                    if pseudo in room_members:
                        room_members.remove(pseudo)
                
                del self.clients[pseudo]
        
        self._notify_listeners("client_disconnected", {"pseudo": pseudo})
    
    def kick_client(self, pseudo: str) -> bool:
        """Force la déconnexion d'un client (action admin)"""
        if pseudo in self.clients:
            self._disconnect_client(pseudo)
            return True
        return False
    
    def get_clients_info(self) -> List[dict]:
        """Retourne les infos de tous les clients connectés"""
        with self.lock:
            return [
                {
                    "pseudo": c.pseudo,
                    "address": f"{c.address[0]}:{c.address[1]}",
                    "room": c.current_room or "-",
                    "duration": c.connection_duration()
                }
                for c in self.clients.values()
            ]
    
    def get_rooms_info(self) -> List[dict]:
        """Retourne les infos de toutes les rooms"""
        with self.lock:
            return [
                {
                    "name": room,
                    "count": len(self.rooms.get(room, [])),
                    "members": self.rooms.get(room, [])
                }
                for room in self.available_rooms
            ]
    
    def _send_to_client(self, pseudo: str, message: str) -> bool:
        """Envoie un message à un client spécifique"""
        with self.lock:
            if pseudo not in self.clients:
                return False
            client = self.clients[pseudo]
        
        try:
            client.socket.send(f"ADMIN_MSG \"{message}\"\n".encode('utf-8'))
            return True
        except Exception as e:
            print(f"Erreur envoi à {pseudo}: {e}")
            return False
    
    def broadcast_all(self, message: str) -> int:
        """Envoie un message à tous les clients connectés"""
        count = 0
        with self.lock:
            pseudos = list(self.clients.keys())
        
        for pseudo in pseudos:
            if self._send_to_client(pseudo, message):
                count += 1
        
        self._notify_listeners("broadcast_sent", {
            "type": "all", 
            "message": message, 
            "recipients": count
        })
        return count
    
    def broadcast_room(self, room: str, message: str) -> int:
        """Envoie un message à tous les clients d'une room"""
        count = 0
        with self.lock:
            if room not in self.rooms:
                return 0
            pseudos = list(self.rooms[room])
        
        for pseudo in pseudos:
            if self._send_to_client(pseudo, message):
                count += 1
        
        self._notify_listeners("broadcast_sent", {
            "type": "room", 
            "room": room,
            "message": message, 
            "recipients": count
        })
        return count
    
    def send_private_message(self, pseudo: str, message: str) -> bool:
        """Envoie un message privé à un client spécifique"""
        success = self._send_to_client(pseudo, message)
        
        self._notify_listeners("broadcast_sent", {
            "type": "private", 
            "pseudo": pseudo,
            "message": message, 
            "recipients": 1 if success else 0
        })
        return success
