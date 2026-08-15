from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TabbedContent,
    TabPane,
)


class FileOpenModal(ModalScreen[str]):
    """Modal screen displaying Group 1 (File Level Metadata & Selector)."""

    BINDINGS = [
        ("escape", "cancel_modal", "Cancel (Esc)"),
    ]

    def __init__(self, current_file: str, file_details: dict) -> None:
        super().__init__()
        self.current_file = current_file
        self.file_details = file_details

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("📂 Open GRIB File", id="modal-title")
            yield Label(f"[b]Path:[/b] {self.current_file}", classes="meta-line")
            yield Label(f"[b]Size:[/b] {self.file_details['size']}", classes="meta-line")
            yield Label(f"[b]Total Messages:[/b] {self.file_details['total_msgs']}", classes="meta-line")
            yield Label(f"[b]GRIB Edition:[/b] {self.file_details['edition']}", classes="meta-line")
            yield Label(f"[b]Center:[/b] {self.file_details['center']}", classes="meta-line")
            yield Label(f"[b]Ref Time:[/b] {self.file_details['ref_time']}", classes="meta-line")
            yield Label(f"[b]Master Tables:[/b] {self.file_details['tables_version']}", classes="meta-line")

            yield Label("\nSelect or enter new file path:")
            yield Input(
                placeholder="Enter GRIB file path...",
                id="file-input",
                value=self.current_file,
            )
            with Horizontal(classes="button-bar"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Open File", id="btn-open", variant="primary")

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


class VariableRow(ListItem):
    """Custom compact row widget representing GRIB Variable Selection."""

    def __init__(self, msg_id: str, data: dict, is_selected: bool = False) -> None:
        super().__init__()
        self.msg_id = msg_id
        self.data = data
        self.is_selected = is_selected

    def compose(self) -> ComposeResult:
        with Horizontal(classes="row-container"):
            yield Checkbox(value=self.is_selected, classes="row-checkbox", id=f"chk-{self.msg_id}")
            yield Label(f"#{self.msg_id}", classes="col-msg")
            yield Label(self.data["shortName"], classes="col-shortname")
            yield Label(self.data["name"], classes="col-name")
            yield Label(self.data["level"], classes="col-level")
            yield Label(self.data["typeOfLevel"], classes="col-leveltype")
            yield Label(self.data["step"], classes="col-time")

    def toggle(self) -> None:
        chk = self.query_one(Checkbox)
        chk.toggle()


class MetSel(App):
    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("o", "open_file_modal", "Open File (O)"),
        ("f", "focus_filter", "Filter (F)"),
        ("space", "toggle_current_row", "Toggle (Space)"),
        ("escape", "focus_table", "Focus Table (Esc)"),
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle Dark"),
    ]

    FILE_DETAILS = {
        "path": "gdas.t00z.pgrb2.0p25.f000",
        "size": "190.4 MB (199,693,439 bytes)",
        "total_msgs": 352,
        "edition": "GRIB Edition 2",
        "center": "7 (US National Weather Service - NCEP)",
        "ref_time": "2026-08-14 00:00:00 UTC",
        "tables_version": "Version 4",
    }

    DUMMY_VARS = {
        "1": {
            "shortName": "tmp",
            "name": "Temperature",
            "paramId": 130,
            "cfVarName": "t",
            "units": "K",
            "level": "500 hPa",
            "typeOfLevel": "isobaricInhPa",
            "levelVal": 500,
            "step": "0h (Instant)",
            "stepType": "instant",
            "refTime": "2026-08-14 00:00:00",
            "gridType": "regular_ll",
            "gridTemplate": "Template 3.0",
            "points": "1,038,240 (1440 x 721)",
            "latRange": "90.0°N to -90.0°S (dx: 0.25°)",
            "lonRange": "0.0°E to 359.75°E (dy: 0.25°)",
            "scanningMode": "+i -j",
            "earthShape": "6371229.0 m sphere",
            "dataPacking": "JPEG 2000 (Template 5.40)",
            "msgSize": "938,307 bytes",
            "precision": "16-bit float",
            "bitmap": "None (Full Grid)",
            "discipline": "0 (Meteorological)",
            "category": "0 (Temperature)",
        },
        "2": {
            "shortName": "ugrd",
            "name": "U-component of wind",
            "paramId": 131,
            "cfVarName": "u",
            "units": "m s**-1",
            "level": "10 m",
            "typeOfLevel": "heightAboveGround",
            "levelVal": 10,
            "step": "0h (Instant)",
            "stepType": "instant",
            "refTime": "2026-08-14 00:00:00",
            "gridType": "regular_ll",
            "gridTemplate": "Template 3.0",
            "points": "1,038,240 (1440 x 721)",
            "latRange": "90.0°N to -90.0°S (dx: 0.25°)",
            "lonRange": "0.0°E to 359.75°E (dy: 0.25°)",
            "scanningMode": "+i -j",
            "earthShape": "6371229.0 m sphere",
            "dataPacking": "JPEG 2000 (Template 5.40)",
            "msgSize": "521,959 bytes",
            "precision": "16-bit float",
            "bitmap": "None (Full Grid)",
            "discipline": "0 (Meteorological)",
            "category": "2 (Momentum)",
        },
        "3": {
            "shortName": "vgrd",
            "name": "V-component of wind",
            "paramId": 132,
            "cfVarName": "v",
            "units": "m s**-1",
            "level": "10 m",
            "typeOfLevel": "heightAboveGround",
            "levelVal": 10,
            "step": "0h (Instant)",
            "stepType": "instant",
            "refTime": "2026-08-14 00:00:00",
            "gridType": "regular_ll",
            "gridTemplate": "Template 3.0",
            "points": "1,038,240 (1440 x 721)",
            "latRange": "90.0°N to -90.0°S (dx: 0.25°)",
            "lonRange": "0.0°E to 359.75°E (dy: 0.25°)",
            "scanningMode": "+i -j",
            "earthShape": "6371229.0 m sphere",
            "dataPacking": "JPEG 2000 (Template 5.40)",
            "msgSize": "516,580 bytes",
            "precision": "16-bit float",
            "bitmap": "None (Full Grid)",
            "discipline": "0 (Meteorological)",
            "category": "2 (Momentum)",
        },
        "4": {
            "shortName": "prmsl",
            "name": "Pressure reduced to MSL",
            "paramId": 2,
            "cfVarName": "prmsl",
            "units": "Pa",
            "level": "0 (MSL)",
            "typeOfLevel": "meanSea",
            "levelVal": 0,
            "step": "0h (Instant)",
            "stepType": "instant",
            "refTime": "2026-08-14 00:00:00",
            "gridType": "regular_ll",
            "gridTemplate": "Template 3.0",
            "points": "1,038,240 (1440 x 721)",
            "latRange": "90.0°N to -90.0°S (dx: 0.25°)",
            "lonRange": "0.0°E to 359.75°E (dy: 0.25°)",
            "scanningMode": "+i -j",
            "earthShape": "6371229.0 m sphere",
            "dataPacking": "JPEG 2000 (Template 5.40)",
            "msgSize": "274,904 bytes",
            "precision": "16-bit float",
            "bitmap": "None (Full Grid)",
            "discipline": "0 (Meteorological)",
            "category": "3 (Mass)",
        },
        "5": {
            "shortName": "rh",
            "name": "Relative Humidity",
            "paramId": 157,
            "cfVarName": "r",
            "units": "%",
            "level": "2 m",
            "typeOfLevel": "heightAboveGround",
            "levelVal": 2,
            "step": "0h (Instant)",
            "stepType": "instant",
            "refTime": "2026-08-14 00:00:00",
            "gridType": "regular_ll",
            "gridTemplate": "Template 3.0",
            "points": "1,038,240 (1440 x 721)",
            "latRange": "90.0°N to -90.0°S (dx: 0.25°)",
            "lonRange": "0.0°E to 359.75°E (dy: 0.25°)",
            "scanningMode": "+i -j",
            "earthShape": "6371229.0 m sphere",
            "dataPacking": "JPEG 2000 (Template 5.40)",
            "msgSize": "550,860 bytes",
            "precision": "16-bit float",
            "bitmap": "None (Full Grid)",
            "discipline": "0 (Meteorological)",
            "category": "1 (Moisture)",
        },
        "6": {
            "shortName": "gh",
            "name": "Geopotential Height",
            "paramId": 156,
            "cfVarName": "z",
            "units": "gpm",
            "level": "500 hPa",
            "typeOfLevel": "isobaricInhPa",
            "levelVal": 500,
            "step": "0h (Instant)",
            "stepType": "instant",
            "refTime": "2026-08-14 00:00:00",
            "gridType": "regular_ll",
            "gridTemplate": "Template 3.0",
            "points": "1,038,240 (1440 x 721)",
            "latRange": "90.0°N to -90.0°S (dx: 0.25°)",
            "lonRange": "0.0°E to 359.75°E (dy: 0.25°)",
            "scanningMode": "+i -j",
            "earthShape": "6371229.0 m sphere",
            "dataPacking": "JPEG 2000 (Template 5.40)",
            "msgSize": "491,301 bytes",
            "precision": "16-bit float",
            "bitmap": "None (Full Grid)",
            "discipline": "0 (Meteorological)",
            "category": "3 (Mass)",
        },
    }

    current_file: str = "gdas.t00z.pgrb2.0p25.f000"
    selected_msg_ids: set[str] = {"1", "4"}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)

        with Container(id="app-box"):
            with Horizontal(id="top-bar"):
                yield Label(
                    f"📁 [b]Active File:[/b] [cyan]{self.current_file}[/cyan] (Size: 190.4MB | Msgs: 352 | GRIB2)  [dim][Press 'O' for File Details Modal][/dim]",
                    id="file-info-header",
                )

            with Container(id="content-container"):
                # Left Pane: Variable Selector
                with Vertical(id="variables-pane"):
                    yield Label("🔍 GRIB Variables Selector (Press ENTER/SPACE to select)", classes="pane-header")
                    yield Input(placeholder="Filter by shortName, name, level, levelType, step...", id="filter-input")

                    with Horizontal(id="table-header"):
                        yield Label("Sel", classes="col-chk")
                        yield Label("Msg#", classes="col-msg")
                        yield Label("ShortName", classes="col-shortname")
                        yield Label("Name / Description", classes="col-name")
                        yield Label("Level", classes="col-level")
                        yield Label("LevelType", classes="col-leveltype")
                        yield Label("Step/Time", classes="col-time")

                    yield ListView(
                        *[
                            VariableRow(msg_id, data, is_selected=(msg_id in self.selected_msg_ids))
                            for msg_id, data in self.DUMMY_VARS.items()
                        ],
                        id="var-listview",
                    )

                    yield Label(f"Selected: {len(self.selected_msg_ids)} variables", id="selection-summary-label", classes="selection-summary")

                # Right Pane: Detailed Inspector Tabs
                with Vertical(id="inspector-pane"):
                    yield Label("📊 Variable Details & Encoding Inspector", classes="pane-header")

                    with TabbedContent(initial="tab-variable-details"):
                        with TabPane("Variable Details", id="tab-variable-details"):
                            with VerticalScroll():
                                yield Static(id="var-details-content")

                        with TabPane("Spatial & Grid", id="tab-spatial"):
                            with VerticalScroll():
                                yield Static(id="spatial-content")

                        with TabPane("Data Encoding", id="tab-encoding"):
                            with VerticalScroll():
                                yield Static(id="encoding-content")

                    yield Label("⚡ Generated Python Snippet", classes="pane-header")
                    with Vertical(id="code-output-pane"):
                        yield Static(id="code-snippet-content", classes="code-snippet")

        yield Footer()

    def on_mount(self) -> None:
        self.title = "MetSel - GRIB Inspector & Code Generator"
        self.update_inspector("1")
        self.update_code_snippet()
        # Default focus on the Variable Selection Table
        self.query_one("#var-listview", ListView).focus()

    def action_focus_table(self) -> None:
        """Hotkey ESC moves focus back to Variable Selection Table."""
        self.query_one("#var-listview", ListView).focus()

    def action_focus_filter(self) -> None:
        """Hotkey F moves focus to Filter Input box."""
        self.query_one("#filter-input", Input).focus()

    def action_open_file_modal(self) -> None:
        def handle_file(selected_file: str | None) -> None:
            if selected_file:
                self.current_file = selected_file
                self.FILE_DETAILS["path"] = selected_file
                header = self.query_one("#file-info-header", Label)
                header.update(
                    f"📁 [b]Active File:[/b] [cyan]{self.current_file}[/cyan] (Size: 190.4MB | Msgs: 352 | GRIB2)  [dim][Press 'O' for File Details Modal][/dim]"
                )

        self.push_screen(FileOpenModal(self.current_file, self.FILE_DETAILS), handle_file)

    def action_toggle_current_row(self) -> None:
        list_view = self.query_one("#var-listview", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, VariableRow):
            list_view.highlighted_child.toggle()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, VariableRow):
            event.item.toggle()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        chk_id = event.checkbox.id
        if chk_id and chk_id.startswith("chk-"):
            msg_id = chk_id.replace("chk-", "")
            if event.value:
                self.selected_msg_ids.add(msg_id)
            else:
                self.selected_msg_ids.discard(msg_id)

            self.update_summary_and_code()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, VariableRow):
            self.update_inspector(event.item.msg_id)

    def update_summary_and_code(self) -> None:
        lbl = self.query_one("#selection-summary-label", Label)
        lbl.update(f"Selected: {len(self.selected_msg_ids)} variables")
        self.update_code_snippet()

    def update_inspector(self, msg_id: str) -> None:
        data = self.DUMMY_VARS.get(msg_id, self.DUMMY_VARS["1"])

        # Grp 2: Variable Details Tab
        var_details = self.query_one("#var-details-content", Static)
        var_details.update(
            f"[bold cyan]Msg #:[/bold cyan] {msg_id}\n"
            f"[bold cyan]Short Name:[/bold cyan] {data['shortName']}\n"
            f"[bold cyan]Name (Description):[/bold cyan] {data['name']}\n"
            f"[bold cyan]paramId:[/bold cyan] {data['paramId']}\n"
            f"[bold cyan]cfVarName:[/bold cyan] {data['cfVarName']}\n"
            f"[bold cyan]Units:[/bold cyan] {data['units']}\n"
            f"[bold cyan]Level:[/bold cyan] {data['level']} (Value: {data['levelVal']})\n"
            f"[bold cyan]Type of Level:[/bold cyan] {data['typeOfLevel']}\n"
            f"[bold cyan]Forecast Step / Lead Time:[/bold cyan] {data['step']}\n"
            f"[bold cyan]Step Type:[/bold cyan] {data['stepType']}\n"
            f"[bold cyan]Reference Time:[/bold cyan] {data['refTime']}\n"
            f"[bold cyan]Discipline / Category:[/bold cyan] {data['discipline']} / {data['category']}"
        )

        # Grp 3: Spatial & Grid Tab
        spatial = self.query_one("#spatial-content", Static)
        spatial.update(
            f"[bold yellow]Grid Type:[/bold yellow] {data['gridType']} ({data['gridTemplate']})\n"
            f"[bold yellow]Total Grid Points:[/bold yellow] {data['points']}\n"
            f"[bold yellow]Latitude Range:[/bold yellow] {data['latRange']}\n"
            f"[bold yellow]Longitude Range:[/bold yellow] {data['lonRange']}\n"
            f"[bold yellow]Scanning Mode:[/bold yellow] {data['scanningMode']}\n"
            f"[bold yellow]Earth Shape:[/bold yellow] {data['earthShape']}"
        )

        # Grp 3: Data Encoding Tab
        encoding = self.query_one("#encoding-content", Static)
        encoding.update(
            f"[bold green]Data Packing:[/bold green] {data['dataPacking']}\n"
            f"[bold green]Message Size:[/bold green] {data['msgSize']}\n"
            f"[bold green]Precision / Bit Depth:[/bold green] {data['precision']}\n"
            f"[bold green]Bitmap Indicator:[/bold green] {data['bitmap']}"
        )

    def update_code_snippet(self) -> None:
        code_static = self.query_one("#code-snippet-content", Static)

        selected_shortnames = [
            self.DUMMY_VARS[m]["shortName"] for m in sorted(self.selected_msg_ids, key=int) if m in self.DUMMY_VARS
        ]

        snippet = (
            "[dim]# Generated Python code to load selected variables[/dim]\n"
            "[bold green]import[/bold green] xarray [bold green]as[/bold green] xr\n\n"
            "ds = xr.open_dataset(\n"
            f'    "{self.current_file}",\n'
            '    engine="cfgrib",\n'
            f'    backend_kwargs={{"filter_by_keys": {{"shortName": {selected_shortnames}}}}}\n'
            ")\n"
            "print(ds)"
        )
        code_static.update(snippet)


def main() -> None:
    app = MetSel()
    app.run()


if __name__ == "__main__":
    main()
