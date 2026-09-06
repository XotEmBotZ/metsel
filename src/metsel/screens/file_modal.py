from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    ListItem,
    ListView,
)

from metsel.grib_parser import fuzzy_search_files


class FileOpenModal(ModalScreen[str | None]):
    """Modal screen displaying Group 1 File Metadata & Fuzzy File Selector."""

    CSS_PATH = "file_modal.tcss"

    BINDINGS = [  # noqa: RUF012
        ("escape", "cancel_modal", "Cancel (Esc)"),
    ]

    def __init__(self, current_file: str, file_details: dict) -> None:
        super().__init__()
        self.current_file = current_file
        self.file_details = file_details
        self.matching_files: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("📂 Open GRIB File", id="modal-title")
            yield Label(
                f"[b]Path:[/b] {self.current_file}",
                classes="meta-line",
                id="modal-path",
            )
            yield Label(
                f"[b]Size:[/b] {self.file_details.get('size', '0 B')}",
                classes="meta-line",
                id="modal-size",
            )
            yield Label(
                f"[b]Total Messages:[/b] {self.file_details.get('total_msgs', 0)}",
                classes="meta-line",
                id="modal-msgs",
            )
            yield Label(
                f"[b]GRIB Edition:[/b] {self.file_details.get('edition', 'N/A')}",
                classes="meta-line",
                id="modal-edition",
            )
            yield Label(
                f"[b]Center:[/b] {self.file_details.get('center', 'N/A')}",
                classes="meta-line",
                id="modal-center",
            )
            yield Label(
                f"[b]Ref Time:[/b] {self.file_details.get('ref_time', 'N/A')}",
                classes="meta-line",
                id="modal-reftime",
            )

            yield Label("\nSearch / Enter file path (Fuzzy Search):")
            yield Input(
                placeholder="Type file name (e.g. gdas, .grb)...",
                id="file-input",
                value=self.current_file,
            )
            yield ListView(id="file-results-list")

            with Horizontal(classes="button-bar"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Open File", id="btn-open", variant="primary")

    def on_mount(self) -> None:
        self.perform_fuzzy_file_search(self.current_file)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "file-input":
            # Debounce search updates by 200ms to eliminate typing lag
            self.set_timer(0.2, lambda: self.perform_fuzzy_file_search(event.value))

    def perform_fuzzy_file_search(self, query: str) -> None:
        results_list = self.query_one("#file-results-list", ListView)
        results_list.clear()

        # If query is exact existing path, list it first
        candidates = []
        if Path(query).is_file():
            candidates.append(query)

        fuzzy_matches = fuzzy_search_files(query)
        for f in fuzzy_matches:
            if f not in candidates:
                candidates.append(f)

        self.matching_files = candidates
        for f_path in candidates:
            results_list.append(ListItem(Label(f"📄 {f_path}")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "file-results-list" and event.item:
            idx = event.list_view.index
            if idx is not None and idx < len(self.matching_files):
                selected_path = self.matching_files[idx]
                self.dismiss(selected_path)

    def action_cancel_modal(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-open":
            val = self.query_one("#file-input", Input).value
            self.dismiss(val)
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)
