from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    Static,
    TabbedContent,
    TabPane,
)
from textual.widgets.option_list import Option

from rich.text import Text

from metsel.grib_parser import GribParser, fuzzy_filter_variables, fuzzy_search_files


class FileOpenModal(ModalScreen[str]):
    """Modal screen displaying Group 1 File Metadata & Fuzzy File Selector."""

    BINDINGS = [
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
            yield Label(f"[b]Path:[/b] {self.current_file}", classes="meta-line", id="modal-path")
            yield Label(f"[b]Size:[/b] {self.file_details['size']}", classes="meta-line", id="modal-size")
            yield Label(f"[b]Total Messages:[/b] {self.file_details['total_msgs']}", classes="meta-line", id="modal-msgs")
            yield Label(f"[b]GRIB Edition:[/b] {self.file_details['edition']}", classes="meta-line", id="modal-edition")
            yield Label(f"[b]Center:[/b] {self.file_details['center']}", classes="meta-line", id="modal-center")
            yield Label(f"[b]Ref Time:[/b] {self.file_details['ref_time']}", classes="meta-line", id="modal-reftime")

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

    def __init__(self) -> None:
        super().__init__()
        self.current_file: str = ""
        self.file_details: dict = {
            "path": "None",
            "size": "0 B",
            "total_msgs": 0,
            "edition": "N/A",
            "center": "N/A",
            "ref_time": "N/A",
            "tables_version": "N/A",
        }
        self.all_variables: dict[str, dict] = {}
        self.filtered_variables: dict[str, dict] = {}
        self.selected_msg_ids: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)

        with Container(id="app-box"):
            with Horizontal(id="top-bar"):
                yield Label(
                    "📁 [b]Active File:[/b] [dim]No file loaded [Press 'O' to Open File][/dim]",
                    id="file-info-header",
                )

            with Container(id="content-container"):
                # Left Pane: Variable Selector
                with Vertical(id="variables-pane"):
                    yield Label("🔍 GRIB Variables Selector (Press ENTER/SPACE to select)", classes="pane-header")
                    yield Input(placeholder="Fuzzy search shortName, description, level, levelType, step...", id="filter-input")

                    with Horizontal(id="table-header"):
                        yield Label("Sel", classes="col-chk")
                        yield Label("Msg#", classes="col-msg")
                        yield Label("ShortName", classes="col-shortname")
                        yield Label("Name / Description", classes="col-name")
                        yield Label("Level", classes="col-level")
                        yield Label("LevelType", classes="col-leveltype")
                        yield Label("Step/Time", classes="col-time")

                    yield OptionList(id="var-optionlist")

                    yield Label("Selected: 0 variables", id="selection-summary-label", classes="selection-summary")

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
        self.action_open_file_modal()

    def load_grib_file(self, filepath: str) -> None:
        """Parse real GRIB file and populate TUI elements."""
        try:
            parsed_data = GribParser.inspect_file(filepath)
            self.current_file = filepath
            self.file_details = parsed_data["file_meta"]
            self.all_variables = parsed_data["variables"]
            self.filtered_variables = dict(self.all_variables)
            self.selected_msg_ids = set()

            # Update Header bar
            header = self.query_one("#file-info-header", Label)
            header.update(
                f"📁 [b]Active File:[/b] [cyan]{self.current_file}[/cyan] ({self.file_details['size']} | Msgs: {self.file_details['total_msgs']} | {self.file_details['edition']})  [dim][Press 'O' for File Details Modal][/dim]"
            )

            # Re-populate ListView
            self.populate_variable_list()

            if self.all_variables:
                first_msg_id = next(iter(self.all_variables))
                self.update_inspector(first_msg_id)
            self.update_summary_and_code()

        except Exception as e:
            header = self.query_one("#file-info-header", Label)
            header.update(f"📁 [bold red]Error opening file:[/bold red] {e}")

    def populate_variable_list(self) -> None:
        opt_list = self.query_one("#var-optionlist", OptionList)
        opt_list.clear_options()

        options = []
        for msg_id, data in self.filtered_variables.items():
            options.append(Option(self.format_variable_label(msg_id, data), id=msg_id))

        opt_list.add_options(options)

    def format_variable_label(self, msg_id: str, data: dict) -> Text:
        chk_icon = "[X]" if msg_id in self.selected_msg_ids else "[ ]"
        msg_str = f"#{msg_id}"
        short_name = data["shortName"]
        name_str = data["name"][:28]
        level_str = data["level"]
        level_type = data["typeOfLevel"]
        step_str = data["step"]
        raw_str = f"{chk_icon:<5} {msg_str:<6} {short_name:<10} {name_str:<30} {level_str:<10} {level_type:<16} {step_str:<8}"
        return Text(raw_str)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Filter Variables table on Enter/Submit for butter-smooth UI performance."""
        if event.input.id == "filter-input":
            query = event.value
            self.filtered_variables = fuzzy_filter_variables(query, self.all_variables)
            self.populate_variable_list()
            self.query_one("#var-optionlist", OptionList).focus()

    def action_focus_table(self) -> None:
        """Hotkey ESC applies current filter query (if in filter input) and moves focus back to Variable Selection Table."""
        filter_input = self.query_one("#filter-input", Input)
        if filter_input.has_focus:
            query = filter_input.value
            self.filtered_variables = fuzzy_filter_variables(query, self.all_variables)
            self.populate_variable_list()

        self.query_one("#var-optionlist", OptionList).focus()

    def action_focus_filter(self) -> None:
        """Hotkey F moves focus to Filter Input box."""
        self.query_one("#filter-input", Input).focus()

    def action_open_file_modal(self) -> None:
        def handle_file(selected_file: str | None) -> None:
            if selected_file:
                self.load_grib_file(selected_file)

        self.push_screen(FileOpenModal(self.current_file, self.file_details), handle_file)

    def action_toggle_current_row(self) -> None:
        opt_list = self.query_one("#var-optionlist", OptionList)
        if opt_list.highlighted is not None:
            option = opt_list.get_option_at_index(opt_list.highlighted)
            self.toggle_variable_selection(option.id, opt_list.highlighted)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "var-optionlist" and event.option.id:
            idx = event.option_list.get_option_index(event.option.id)
            self.toggle_variable_selection(event.option.id, idx)

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_list.id == "var-optionlist" and event.option and event.option.id:
            self.update_inspector(event.option.id)

    def toggle_variable_selection(self, msg_id: str, index: int | None = None) -> None:
        if msg_id in self.selected_msg_ids:
            self.selected_msg_ids.remove(msg_id)
        else:
            self.selected_msg_ids.add(msg_id)

        opt_list = self.query_one("#var-optionlist", OptionList)
        if index is not None and msg_id in self.filtered_variables:
            new_label = self.format_variable_label(msg_id, self.filtered_variables[msg_id])
            opt_list.replace_option_prompt_at_index(index, new_label)
        else:
            self.populate_variable_list()

        self.update_summary_and_code()

    def update_summary_and_code(self) -> None:
        lbl = self.query_one("#selection-summary-label", Label)
        lbl.update(f"Selected: {len(self.selected_msg_ids)} variables")
        self.update_code_snippet()

    def update_inspector(self, msg_id: str) -> None:
        data = self.all_variables.get(msg_id)
        if not data:
            return

        # Variable Details Tab (Grp 1 & 2)
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

        # Spatial & Grid Tab (Grp 3)
        spatial = self.query_one("#spatial-content", Static)
        spatial.update(
            f"[bold yellow]Grid Type:[/bold yellow] {data['gridType']} ({data['gridTemplate']})\n"
            f"[bold yellow]Total Grid Points:[/bold yellow] {data['points']}\n"
            f"[bold yellow]Latitude Range:[/bold yellow] {data['latRange']}\n"
            f"[bold yellow]Longitude Range:[/bold yellow] {data['lonRange']}\n"
            f"[bold yellow]Scanning Mode:[/bold yellow] {data['scanningMode']}\n"
            f"[bold yellow]Earth Shape:[/bold yellow] {data['earthShape']}"
        )

        # Data Encoding Tab (Grp 3)
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
            self.all_variables[m]["shortName"] for m in sorted(self.selected_msg_ids, key=int) if m in self.all_variables
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
