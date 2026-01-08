import argparse
import json
import random
import flet as ft


def main_factory(rooms):
    def main(page: ft.Page):
        page.title = "Rooms"
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.auto_scroll = True

        def on_click(e: ft.ControlEvent):
            room_name = e.control.data if hasattr(e.control, "data") else None
            page.snack_bar = ft.SnackBar(ft.Text(f"Clique sur: {room_name}"))
            page.snack_bar.open = True
            page.update()

        # Use `content` and `data` to be compatible with different flet versions
        buttons = [
            ft.ElevatedButton(content=ft.Text(str(r)), on_click=on_click, data=r)
            for r in rooms
        ]

        if not buttons:
            page.add(ft.Text("Aucune room à afficher"))
        else:
            page.add(ft.Column(buttons, spacing=8, width=300))

    return main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flet demo: create buttons from a Python array")
    parser.add_argument(
        "--rooms",
        help='JSON array of room names, e.g. "[\"A\", \"B\"]" (if omitted, a random number of rooms is created)',
        default=None,
    )
    args = parser.parse_args()

    if args.rooms is None:
        # Generate a random number of rooms between 1 and 6 each launch
        n = random.randint(1, 6)
        rooms = [f"Room {i+1}" for i in range(n)]
    else:
        try:
            rooms = json.loads(args.rooms)
            if not isinstance(rooms, list):
                rooms = [rooms]
        except Exception:
            rooms = [args.rooms]

    ft.app(target=main_factory(rooms))
