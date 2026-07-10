import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk

from file_loader import load_file
from search_pattern import SearchPatternError, compile_pattern, find_matches
from viewer_model import ViewerModel


DEFAULT_BYTES_PER_LINE = 16


class HexViewerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Hex Viewer")
        self.geometry("1100x720")

        self.model = ViewerModel()
        self.file_path = tk.StringVar(value="")
        self.bytes_per_line_var = tk.StringVar(value=str(DEFAULT_BYTES_PER_LINE))
        self.search_var = tk.StringVar(value="")
        self.jump_var = tk.StringVar(value="")
        self.offset_base_var = tk.StringVar(value="10")
        self.status_var = tk.StringVar(value="请选择文件。")

        self.bytes_per_line = DEFAULT_BYTES_PER_LINE
        self.top_line = 0
        self.matches: list[int] = []
        self.current_match_index = -1
        self.current_match_length = 0
        self.visible_rows = 30
        self.formatting_search = False

        self._build_ui()
        self._bind_events()
        self._render()

    def _build_ui(self) -> None:
        controls = ttk.Frame(self, padding=(10, 10, 10, 6))
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Button(controls, text="打开", command=self._open_file).grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(controls, textvariable=self.file_path, state="readonly").grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Label(controls, text="每行字节").grid(row=0, column=2, padx=(0, 4))
        self.bytes_entry = ttk.Entry(controls, textvariable=self.bytes_per_line_var, width=8)
        self.bytes_entry.grid(row=0, column=3, padx=(0, 10))
        ttk.Label(controls, text="搜索").grid(row=0, column=4, padx=(0, 4))
        self.search_entry = ttk.Entry(controls, textvariable=self.search_var, width=28)
        self.search_entry.grid(row=0, column=5, padx=(0, 6))
        ttk.Button(controls, text="搜索", command=self._search).grid(row=0, column=6, padx=(0, 4))
        ttk.Button(controls, text="上一个", command=self._previous_match).grid(row=0, column=7, padx=(0, 4))
        ttk.Button(controls, text="下一个", command=self._next_match).grid(row=0, column=8, padx=(0, 10))
        ttk.Label(controls, text="偏移").grid(row=0, column=9, padx=(0, 4))
        self.jump_entry = ttk.Entry(controls, textvariable=self.jump_var, width=12)
        self.jump_entry.grid(row=0, column=10, padx=(0, 4))
        self.offset_base = ttk.Combobox(
            controls,
            textvariable=self.offset_base_var,
            values=("10", "16"),
            width=4,
            state="readonly",
        )
        self.offset_base.grid(row=0, column=11, padx=(0, 4))
        ttk.Button(controls, text="跳转", command=self._jump_to_offset).grid(row=0, column=12)

        body = ttk.Frame(self, padding=(10, 0, 10, 4))
        body.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.text_font = font.Font(family="Consolas", size=10)
        self.text = tk.Text(body, wrap="none", font=self.text_font, undo=False, height=20)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.configure(state="disabled")
        self.text.tag_configure("current_match", background="#F9D65C", foreground="#111111")
        self.text.tag_configure("header", foreground="#666666")

        y_scroll = ttk.Scrollbar(body, orient="vertical", command=self._on_vertical_scroll)
        y_scroll.grid(row=0, column=1, sticky="ns")
        self.y_scroll = y_scroll

        x_scroll = ttk.Scrollbar(body, orient="horizontal", command=self.text.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.text.configure(xscrollcommand=x_scroll.set)

        status = ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 4))
        status.grid(row=2, column=0, sticky="ew")

    def _bind_events(self) -> None:
        self.bytes_per_line_var.trace_add("write", self._on_bytes_per_line_changed)
        self.search_var.trace_add("write", self._on_search_changed)
        self.offset_base_var.trace_add("write", self._on_offset_base_changed)
        self.text.bind("<Configure>", self._on_text_configure)
        self.text.bind("<MouseWheel>", self._on_mouse_wheel)
        self.text.bind("<Prior>", lambda _event: self._move_lines(-self.visible_rows))
        self.text.bind("<Next>", lambda _event: self._move_lines(self.visible_rows))
        self.text.bind("<Home>", lambda _event: self._set_top_line(0))
        self.text.bind("<End>", lambda _event: self._set_top_line(self._max_top_line()))
        self.bind("<F3>", lambda _event: self._next_match())
        self.bind("<Shift-F3>", lambda _event: self._previous_match())
        self.search_entry.bind("<Return>", lambda _event: self._search())
        self.jump_entry.bind("<Return>", lambda _event: self._jump_to_offset())

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(title="打开二进制或 Intel HEX 文件")
        if not path:
            return

        try:
            loaded = load_file(path)
        except OSError as exc:
            messagebox.showerror("打开失败", str(exc))
            return

        self.model = ViewerModel(loaded.data, loaded.base_address)
        self.file_path.set(path)
        self.matches = []
        self.current_match_index = -1
        self.current_match_length = 0
        self.top_line = 0
        self.status_var.set(self._file_status(loaded.source_type))
        self._render()

    def _on_bytes_per_line_changed(self, *_args: object) -> None:
        text = self.bytes_per_line_var.get().strip()
        if not text:
            return

        try:
            value = int(text, 10)
        except ValueError:
            self.status_var.set("每行字节数必须是正整数。")
            return

        if value <= 0:
            self.status_var.set("每行字节数必须是正整数。")
            return

        self.bytes_per_line = value
        self.top_line = min(self.top_line, self._max_top_line())
        self._render()

    def _on_search_changed(self, *_args: object) -> None:
        if self.formatting_search:
            return

        text = self.search_var.get()
        formatted = format_search_text(text)
        if formatted == text:
            return

        self.formatting_search = True
        self.search_var.set(formatted)
        self.formatting_search = False
        self.search_entry.icursor("end")

    def _on_offset_base_changed(self, *_args: object) -> None:
        self._render()

    def _search(self) -> None:
        try:
            pattern = compile_pattern(self.search_var.get())
        except SearchPatternError as exc:
            messagebox.showwarning("搜索格式错误", str(exc))
            return

        self.matches = find_matches(self.model.data, pattern)
        self.current_match_length = pattern.length

        if not self.matches:
            self.current_match_index = -1
            self.status_var.set("未找到匹配结果。")
            self._render()
            return

        self.current_match_index = 0
        self._jump_to_match()

    def _previous_match(self) -> None:
        if not self.matches:
            self.status_var.set("没有搜索结果。")
            return

        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        self._jump_to_match()

    def _next_match(self) -> None:
        if not self.matches:
            self.status_var.set("没有搜索结果。")
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        self._jump_to_match()

    def _jump_to_match(self) -> None:
        data_index = self.matches[self.current_match_index]
        line = self.model.line_for_data_index(data_index, self.bytes_per_line)
        self._set_top_line(max(0, line - self.visible_rows // 2))
        address = self.model.base_address + data_index
        self.status_var.set(f"结果 {self.current_match_index + 1}/{len(self.matches)}，偏移 {self._format_offset(address)}。")

    def _jump_to_offset(self) -> None:
        text = self.jump_var.get().strip()
        if not text:
            return

        try:
            address = self._parse_offset(text)
        except ValueError:
            messagebox.showwarning("偏移格式错误", "偏移请输入当前进制下的有效整数。")
            return

        data_index = self.model.data_index_for_address(address)
        line = self.model.line_for_data_index(data_index, self.bytes_per_line)
        self._set_top_line(line)
        actual = self.model.base_address + data_index
        self.status_var.set(f"已跳转到偏移 {self._format_offset(actual)}。")

    def _render(self) -> None:
        self.visible_rows = self._calculate_visible_rows()
        x_position = self.text.xview()[0] if self.text.winfo_ismapped() else 0.0
        total_lines = self.model.total_lines(self.bytes_per_line)
        self.top_line = max(0, min(self.top_line, self._max_top_line()))
        offset_width = self._offset_width()
        rendered_lines = []

        for row_index in range(self.visible_rows):
            line_index = self.top_line + row_index
            if line_index >= total_lines:
                break
            rendered_lines.append(self.model.line_at(line_index, self.bytes_per_line))

        # Column width follows rendered content, so an oversized row setting does not
        # allocate a huge blank header before real bytes exist.
        hex_width = max([len("hex bytes")] + [len(line.hex_text) for line in rendered_lines])

        rows: list[str] = []
        rows.append(f"{'offset'.ljust(offset_width)}  {'hex bytes'.ljust(hex_width)}  ASCII")
        for line in rendered_lines:
            rows.append(f"{self._format_offset_for_table(line.address, offset_width)}  {line.hex_text.ljust(hex_width)}  {line.ascii_text}")

        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", "\n".join(rows))
        self.text.tag_add("header", "1.0", "1.end")
        self._highlight_current_match(offset_width, hex_width)
        self.text.configure(state="disabled")
        self.text.xview_moveto(x_position)
        self._update_vertical_scrollbar()

    def _highlight_current_match(self, offset_width: int, hex_width: int) -> None:
        self.text.tag_remove("current_match", "1.0", "end")
        if self.current_match_index < 0 or not self.matches:
            return

        start = self.matches[self.current_match_index]
        end = start + self.current_match_length
        hex_start = offset_width + 2
        ascii_start = hex_start + hex_width + 2

        for data_index in range(start, end):
            line_index = data_index // self.bytes_per_line
            visible_line = line_index - self.top_line + 2
            if visible_line < 2 or visible_line > self.visible_rows + 1:
                continue

            byte_column = data_index % self.bytes_per_line
            hex_column = hex_start + byte_column * 3
            ascii_column = ascii_start + byte_column
            self.text.tag_add("current_match", f"{visible_line}.{hex_column}", f"{visible_line}.{hex_column + 2}")
            self.text.tag_add("current_match", f"{visible_line}.{ascii_column}", f"{visible_line}.{ascii_column + 1}")

    def _on_vertical_scroll(self, *args: str) -> None:
        if args[0] == "moveto":
            self._set_top_line(round(float(args[1]) * self._max_top_line()))
        elif args[0] == "scroll":
            amount = int(args[1])
            unit = self.visible_rows if args[2] == "pages" else 1
            self._move_lines(amount * unit)

    def _on_mouse_wheel(self, event: tk.Event) -> str:
        step = -1 if event.delta > 0 else 1
        self._move_lines(step * 3)
        return "break"

    def _on_text_configure(self, _event: tk.Event) -> None:
        rows = self._calculate_visible_rows()
        if rows != self.visible_rows:
            self.visible_rows = rows
            self._render()

    def _calculate_visible_rows(self) -> int:
        line_height = self.text_font.metrics("linespace")
        height = self.text.winfo_height()
        if height <= 1:
            return self.visible_rows
        return max(1, height // max(1, line_height) - 1)

    def _move_lines(self, delta: int) -> str:
        self._set_top_line(self.top_line + delta)
        return "break"

    def _set_top_line(self, value: int) -> None:
        self.top_line = max(0, min(value, self._max_top_line()))
        self._render()

    def _max_top_line(self) -> int:
        return max(0, self.model.total_lines(self.bytes_per_line) - self.visible_rows)

    def _update_vertical_scrollbar(self) -> None:
        total = self.model.total_lines(self.bytes_per_line)
        if total <= self.visible_rows:
            self.y_scroll.set(0.0, 1.0)
            return

        first = self.top_line / total
        last = min(1.0, (self.top_line + self.visible_rows) / total)
        self.y_scroll.set(first, last)

    def _offset_width(self) -> int:
        if self.offset_base_var.get() == "16":
            return max(8, len(f"{self.model.last_address:X}"))
        return max(8, len(str(self.model.last_address)))

    def _file_status(self, source_type: str) -> str:
        kind = "Intel HEX" if source_type == "intel_hex" else "二进制"
        return f"已加载 {kind} 数据，大小 {self.model.size} 字节，起始偏移 {self._format_offset(self.model.base_address)}。"

    def _parse_offset(self, text: str) -> int:
        if text.lower().startswith("0x"):
            return int(text[2:], 16)
        return int(text, int(self.offset_base_var.get()))

    def _format_offset(self, value: int) -> str:
        if self.offset_base_var.get() == "16":
            return f"0x{value:X}"
        return str(value)

    def _format_offset_for_table(self, value: int, width: int) -> str:
        if self.offset_base_var.get() == "16":
            return f"{value:0{width}X}"
        return f"{value:0{width}d}"


def format_search_text(text: str) -> str:
    # The search box groups nibbles as bytes while keeping an unfinished trailing
    # nibble visible, so typing 49F becomes "49 F" and searches as 49 F?.
    compact = "".join(char for char in text if not char.isspace())
    groups = [compact[index : index + 2] for index in range(0, len(compact), 2)]
    return " ".join(groups)


if __name__ == "__main__":
    app = HexViewerApp()
    app.mainloop()
