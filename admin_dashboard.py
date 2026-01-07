"""
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
