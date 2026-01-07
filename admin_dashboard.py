"""
<<<<<<< HEAD
Admin Dashboard - Interface Flet pour l'administration du serveur
"""
import flet as ft
from datetime import datetime


def start_admin_ui(server):
    """Lance l'interface admin Flet (appelé depuis le serveur)"""

    def main(page: ft.Page):
        page.title = "Admin Dashboard - DropBox Server"
        page.window_width = 900
        page.window_height = 600
        page.theme_mode = ft.ThemeMode.DARK

        # ================================
        # Tableau des clients
        # ================================
        clients_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("IP:Port", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Pseudo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Room", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Dernier msg", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.GREY_700),
            heading_row_color=ft.Colors.BLUE_GREY_900,
            data_row_max_height=50,
        )

        def refresh_clients():
            """Met à jour le tableau des clients"""
            clients_table.rows.clear()
            with server.clients_lock:
                for client in server.clients:
                    addr = f"{client['addr'][0]}:{client['addr'][1]}"
                    pseudo = client["pseudo"] or "-"
                    room = client["room"] or "(lobby)"
                    last_msg = "-"
                    if client["last_message_time"]:
                        last_msg = client["last_message_time"].strftime("%H:%M:%S")

                    # Bouton kick pour ce client
                    kick_btn = ft.IconButton(
                        icon=ft.Icons.PERSON_REMOVE,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Kick",
                        data=client["socket"],
                        on_click=lambda e: kick_client(e.control.data),
                    )

                    clients_table.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(addr, size=12)),
                                ft.DataCell(ft.Text(pseudo, weight=ft.FontWeight.W_500)),
                                ft.DataCell(ft.Text(room, color=ft.Colors.CYAN_200)),
                                ft.DataCell(ft.Text(last_msg, size=12)),
                                ft.DataCell(kick_btn),
                            ]
                        )
                    )
            clients_count.value = f"Clients connectés: {len(server.clients)}"
            page.update()

        def kick_client(client_socket):
            """Kick un client"""
            server.kick_client(client_socket)
            refresh_clients()

        # ================================
        # Broadcast
        # ================================
        broadcast_message = ft.TextField(
            label="Message broadcast",
            expand=True,
            multiline=False,
        )

        broadcast_target_type = ft.Dropdown(
            label="Cible",
            options=[
                ft.dropdown.Option("all", "Tous"),
                ft.dropdown.Option("room", "Room"),
                ft.dropdown.Option("mp", "MP"),
            ],
            value="all",
            width=120,
        )

        broadcast_target = ft.TextField(
            label="Room/Pseudo",
            width=150,
            visible=False,
        )

        def on_target_type_change(e):
            broadcast_target.visible = broadcast_target_type.value in ["room", "mp"]
            page.update()

        broadcast_target_type.on_change = on_target_type_change

        def send_broadcast(e):
            msg = broadcast_message.value.strip()
            if not msg:
                return
            target = broadcast_target.value if broadcast_target.visible else None
            server.send_admin_broadcast(msg, broadcast_target_type.value, target)
            broadcast_message.value = ""
            page.update()

        broadcast_btn = ft.ElevatedButton(
            "Envoyer",
            icon=ft.Icons.SEND,
            on_click=send_broadcast,
            bgcolor=ft.Colors.BLUE_700,
        )

        # ================================
        # Callback de mise à jour
        # ================================
        server.on_clients_change = refresh_clients

        # ================================
        # Layout
        # ================================
        clients_count = ft.Text("Clients connectés: 0", size=16, weight=ft.FontWeight.BOLD)

        page.add(
            ft.Container(
                content=ft.Column(
                    [
                        # Header
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS, size=30, color=ft.Colors.BLUE_400),
                                ft.Text("Admin Dashboard", size=24, weight=ft.FontWeight.BOLD),
                                ft.Container(expand=True),
                                clients_count,
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Divider(height=10),

                        # Tableau clients
                        ft.Container(
                            content=ft.Column(
                                [clients_table],
                                scroll=ft.ScrollMode.AUTO,
                            ),
                            expand=True,
                            border=ft.border.all(1, ft.Colors.GREY_800),
                            border_radius=8,
                            padding=10,
                        ),

                        ft.Divider(height=10),

                        # Broadcast panel
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text("📢 Broadcast Admin", weight=ft.FontWeight.BOLD),
                                    ft.Row(
                                        [
                                            broadcast_message,
                                            broadcast_target_type,
                                            broadcast_target,
                                            broadcast_btn,
                                        ],
                                        alignment=ft.MainAxisAlignment.START,
                                    ),
                                ]
                            ),
                            bgcolor=ft.Colors.GREY_900,
                            padding=15,
                            border_radius=8,
                        ),
                    ],
                    expand=True,
                ),
                padding=20,
                expand=True,
            )
        )

        # Premier refresh
        refresh_clients()

    ft.app(target=main)
=======
Dashboard Admin DropBox
Interface Flet pour administrer le serveur et visualiser les clients connectés
"""

import flet as ft
from server import DropBoxServer
import threading


class AdminDashboard:
    """Interface d'administration Flet"""
    
    def __init__(self, server: DropBoxServer):
        self.server = server
        self.page: ft.Page = None
        self.clients_table: ft.DataTable = None
        self.rooms_column: ft.Column = None
        self.status_text: ft.Text = None
        self.server_button: ft.Button = None
        self.logs_column: ft.Column = None
        
        # Composants broadcast
        self.broadcast_type: ft.Dropdown = None
        self.broadcast_target: ft.TextField = None
        self.broadcast_message: ft.TextField = None
        
        # S'abonner aux événements du serveur
        self.server.add_listener(self._on_server_event)
    
    def _on_server_event(self, event: str, data: dict):
        """Callback pour les événements du serveur"""
        if self.page:
            # Ajouter un log
            self._add_log(event, data)
            # Rafraîchir les données
            self._refresh_data()
    
    def _add_log(self, event: str, data: dict):
        """Ajoute une ligne de log"""
        if not self.logs_column:
            return
        
        event_icons = {
            "server_started": "🟢",
            "server_stopped": "🔴",
            "client_connected": "👤➡️",
            "client_disconnected": "👤⬅️",
            "client_joined_room": "🚪",
            "client_left_room": "🚶",
            "message_sent": "💬",
            "broadcast_sent": "📢"
        }
        
        icon = event_icons.get(event, "📋")
        msg = f"{icon} {event}"
        if "pseudo" in data:
            msg += f" - {data['pseudo']}"
        if "room" in data:
            msg += f" [{data['room']}]"
        
        log_text = ft.Text(msg, size=12, color=ft.Colors.GREY_400)
        self.logs_column.controls.insert(0, log_text)
        
        # Garder seulement les 20 derniers logs
        if len(self.logs_column.controls) > 20:
            self.logs_column.controls.pop()
        
        try:
            self.page.update()
        except:
            pass
    
    def _refresh_data(self):
        """Rafraîchit les données affichées"""
        if not self.page:
            return
        
        try:
            # Rafraîchir la table des clients
            self._update_clients_table()
            # Rafraîchir les rooms
            self._update_rooms()
            self.page.update()
        except:
            pass
    
    def _update_clients_table(self):
        """Met à jour la table des clients"""
        if not self.clients_table:
            return
        
        clients = self.server.get_clients_info()
        
        rows = []
        for client in clients:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(client["pseudo"])),
                        ft.DataCell(ft.Text(client["address"])),
                        ft.DataCell(ft.Text(client["room"])),
                        ft.DataCell(ft.Text(client["duration"])),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.Icons.LOGOUT,
                                icon_color=ft.Colors.RED_400,
                                tooltip="Déconnecter",
                                data=client["pseudo"],
                                on_click=self._kick_client
                            )
                        ),
                    ]
                )
            )
        
        self.clients_table.rows = rows
    
    def _update_rooms(self):
        """Met à jour la liste des rooms"""
        if not self.rooms_column:
            return
        
        rooms = self.server.get_rooms_info()
        
        self.rooms_column.controls = [
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.MEETING_ROOM, color=ft.Colors.BLUE_300),
                    ft.Text(f"{room['name']}", weight=ft.FontWeight.BOLD),
                    ft.Container(
                        content=ft.Text(str(room['count']), size=12),
                        bgcolor=ft.Colors.BLUE_700,
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=8, vertical=2),
                    ),
                ], spacing=10),
                padding=10,
                border_radius=8,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                margin=ft.margin.only(bottom=5),
            )
            for room in rooms
        ]
    
    def _kick_client(self, e):
        """Déconnecte un client"""
        pseudo = e.control.data
        if self.server.kick_client(pseudo):
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Client '{pseudo}' déconnecté"),
                bgcolor=ft.Colors.ORANGE_700
            )
            self.page.snack_bar.open = True
            self._refresh_data()
    
    def _on_broadcast_type_change(self, e):
        """Gère le changement de type de broadcast"""
        broadcast_type = self.broadcast_type.value
        if broadcast_type == "all":
            self.broadcast_target.visible = False
            self.broadcast_target.label = ""
        elif broadcast_type == "room":
            self.broadcast_target.visible = True
            self.broadcast_target.label = "Nom de la room"
        else:  # private
            self.broadcast_target.visible = True
            self.broadcast_target.label = "Pseudo du client"
        self.page.update()
    
    def _send_broadcast(self, e):
        """Envoie un message broadcast"""
        message = self.broadcast_message.value
        if not message:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text("❌ Veuillez entrer un message"),
                bgcolor=ft.Colors.RED_700
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        
        broadcast_type = self.broadcast_type.value
        target = self.broadcast_target.value
        
        if broadcast_type == "all":
            count = self.server.broadcast_all(message)
            result_msg = f"📢 Message envoyé à {count} client(s)"
        elif broadcast_type == "room":
            if not target:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("❌ Veuillez spécifier une room"),
                    bgcolor=ft.Colors.RED_700
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            count = self.server.broadcast_room(target, message)
            result_msg = f"📢 Message envoyé à {count} client(s) dans {target}"
        else:  # private
            if not target:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text("❌ Veuillez spécifier un pseudo"),
                    bgcolor=ft.Colors.RED_700
                )
                self.page.snack_bar.open = True
                self.page.update()
                return
            success = self.server.send_private_message(target, message)
            result_msg = f"📢 Message privé {'envoyé' if success else 'échoué'} à {target}"
        
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(result_msg),
            bgcolor=ft.Colors.GREEN_700 if "envoyé" in result_msg else ft.Colors.RED_700
        )
        self.page.snack_bar.open = True
        self.broadcast_message.value = ""
        self.page.update()
    
    def _toggle_server(self, e):
        """Démarre/arrête le serveur"""
        if self.server.running:
            self.server.stop()
            self.server_button.content = ft.Text("▶️ Démarrer le serveur")
            self.server_button.bgcolor = ft.Colors.GREEN_700
            self.status_text.value = "🔴 Serveur arrêté"
            self.status_text.color = ft.Colors.RED_400
        else:
            try:
                self.server.start()
                self.server_button.content = ft.Text("⏹️ Arrêter le serveur")
                self.server_button.bgcolor = ft.Colors.RED_700
                self.status_text.value = f"🟢 Serveur actif sur le port {self.server.port}"
                self.status_text.color = ft.Colors.GREEN_400
            except OSError as err:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"❌ Erreur: {err}"),
                    bgcolor=ft.Colors.RED_700
                )
                self.page.snack_bar.open = True
                self.status_text.value = f"❌ Port {self.server.port} déjà utilisé"
                self.status_text.color = ft.Colors.ORANGE_400
        
        self.page.update()
    
    def build(self, page: ft.Page):
        """Construit l'interface"""
        self.page = page
        page.title = "🛠️ Admin Dashboard - DropBox Server"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 20
        page.bgcolor = ft.Colors.GREY_900
        
        # Header
        self.status_text = ft.Text(
            "🔴 Serveur arrêté",
            size=14,
            color=ft.Colors.RED_400
        )
        
        self.server_button = ft.Button(
            content=ft.Text("▶️ Démarrer le serveur"),
            on_click=self._toggle_server,
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            style=ft.ButtonStyle(padding=15)
        )
        
        header = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text("🛠️ Dashboard Admin", size=28, weight=ft.FontWeight.BOLD),
                    self.status_text,
                ], spacing=5),
                self.server_button,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=20,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=12,
        )
        
        # Table des clients
        self.clients_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Pseudo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Adresse", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Room", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Durée", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.border.all(1, ft.Colors.GREY_700),
            border_radius=10,
            heading_row_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            data_row_max_height=50,
        )
        
        clients_section = ft.Container(
            content=ft.Column([
                ft.Text("👥 Clients connectés", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.clients_table,
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=10,
                    padding=10,
                ),
            ], spacing=10),
            expand=2,
        )
        
        # Rooms
        self.rooms_column = ft.Column(spacing=5)
        self._update_rooms()
        
        rooms_section = ft.Container(
            content=ft.Column([
                ft.Text("🚪 Rooms", size=20, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.rooms_column,
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=10,
                    padding=15,
                ),
            ], spacing=10),
            width=250,
        )
        
        # Section Broadcast
        self.broadcast_type = ft.Dropdown(
            label="Type",
            value="all",
            options=[
                ft.dropdown.Option("all", "📢 Tous"),
                ft.dropdown.Option("room", "🚪 Room"),
                ft.dropdown.Option("private", "👤 Privé"),
            ],
            width=150,
        )
        
        self.broadcast_target = ft.TextField(
            label="Cible (room ou pseudo)",
            hint_text="Optionnel pour 'Tous'",
            width=180,
        )
        
        self.broadcast_message = ft.TextField(
            label="Message",
            expand=True,
            multiline=False,
        )
        
        broadcast_section = ft.Container(
            content=ft.Column([
                ft.Text("📢 Broadcast", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Row([
                        self.broadcast_type,
                        self.broadcast_target,
                        self.broadcast_message,
                        ft.IconButton(
                            icon=ft.Icons.SEND,
                            icon_color=ft.Colors.BLUE_400,
                            tooltip="Envoyer",
                            on_click=self._send_broadcast,
                        ),
                    ], spacing=10),
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=10,
                    padding=15,
                ),
            ], spacing=5),
        )
        
        # Logs
        self.logs_column = ft.Column(
            spacing=3,
            scroll=ft.ScrollMode.AUTO,
            height=150,
        )
        
        logs_section = ft.Container(
            content=ft.Column([
                ft.Text("📋 Logs", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=self.logs_column,
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=10,
                    padding=10,
                ),
            ], spacing=5),
        )
        
        # Layout principal
        main_content = ft.Row([
            clients_section,
            rooms_section,
        ], spacing=20, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
        
        page.add(
            header,
            ft.Container(height=20),
            main_content,
            ft.Container(height=15),
            broadcast_section,
            ft.Container(height=15),
            logs_section,
        )


def main(page: ft.Page):
    """Point d'entrée de l'application"""
    server = DropBoxServer(host="0.0.0.0", port=5000)
    dashboard = AdminDashboard(server)
    dashboard.build(page)


if __name__ == "__main__":
    ft.run(main)
>>>>>>> origin/adminBranch
