import sys

from textual.app import App

from metsel.screens.main_screen import MainScreen


class MetSel(App):
    CSS_PATH = "app.tcss"

    BINDINGS = [  # noqa: RUF012
        ("q", "quit", "Quit"),
    ]

    def __init__(self, initial_file: str | None = None) -> None:
        super().__init__()
        self.initial_file = initial_file

    def on_mount(self) -> None:
        self.title = "MetSel - GRIB Inspector & Code Generator"
        self.push_screen(MainScreen(initial_file=self.initial_file))


app = MetSel


def main() -> None:
    initial_file = sys.argv[1] if len(sys.argv) > 1 else None
    app_instance = MetSel(initial_file=initial_file)
    app_instance.run()
