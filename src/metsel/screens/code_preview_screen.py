from pathlib import Path

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    Static,
)


class CodePreviewModal(ModalScreen[None]):
    """Modal screen displaying generated code preview with Export & Clipboard tools."""

    CSS_PATH = "code_preview_screen.tcss"

    BINDINGS = [  # noqa: RUF012
        ("escape", "dismiss_modal", "Close (Esc)"),
        ("c", "copy_code", "Copy Code (C)"),
        ("s", "save_code", "Save to File (S)"),
    ]

    def __init__(self, code: str, default_filename: str = "load_grib.py") -> None:
        super().__init__()
        self.code = code
        self.default_filename = default_filename

    def compose(self) -> ComposeResult:
        with Vertical(id="code-dialog"):
            with Horizontal(id="code-dialog-header"):
                yield Label(
                    "⚡ Generated xarray Loading Pipeline", id="code-modal-title"
                )
                yield Label("[dim]Press ESC to close[/dim]", id="code-modal-hint")

            with VerticalScroll(id="code-preview-scroll"):
                syntax = Syntax(
                    self.code,
                    "python",
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True,
                )
                yield Static(syntax, id="code-syntax-view")

            with Container(id="export-controls-box"):
                with Horizontal(classes="export-file-row"):
                    yield Label("Save Script As:", classes="lbl-save-as")
                    yield Input(value=self.default_filename, id="input-save-filename")
                    yield Button(
                        "💾 Save to Disk (S)", id="btn-save-code", variant="primary"
                    )
                    yield Button(
                        "📋 Copy Code (C)", id="btn-copy-code", variant="success"
                    )
                    yield Button("Close (Esc)", id="btn-close-code", variant="default")

                yield Label("", id="status-feedback-label", classes="status-label")

    def action_dismiss_modal(self) -> None:
        self.dismiss(None)

    def action_copy_code(self) -> None:
        try:
            self.app.copy_to_clipboard(self.code)
            lbl = self.query_one("#status-feedback-label", Label)
            lbl.update("✅ Code successfully copied to clipboard!")
            self.notify(
                "Code copied to clipboard!", title="Copied", severity="information"
            )
        except Exception as e:  # noqa: BLE001
            lbl = self.query_one("#status-feedback-label", Label)
            lbl.update(f"⚠️ Clipboard error: {e}")

    def action_save_code(self) -> None:
        filename_input = self.query_one("#input-save-filename", Input)
        filename = filename_input.value.strip() or self.default_filename
        lbl = self.query_one("#status-feedback-label", Label)
        try:
            target_path = Path(filename)
            target_path.write_text(self.code, encoding="utf-8")
            lbl.update(
                f"✅ Successfully saved Python script to: [b]{target_path.resolve()}[/b]"
            )
            self.notify(
                f"Saved to {target_path.name}",
                title="File Saved",
                severity="information",
            )
        except Exception as e:  # noqa: BLE001
            lbl.update(f"❌ Error saving file: {e}")
            self.notify(f"Error saving: {e}", title="Error", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-close-code":
            self.dismiss(None)
        elif event.button.id == "btn-copy-code":
            self.action_copy_code()
        elif event.button.id == "btn-save-code":
            self.action_save_code()
