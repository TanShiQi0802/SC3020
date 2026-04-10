import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import time
import preprocessing
import annotation

# ═══════════════════════════════════════════════════════════════════════════════
#  Theme constants
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    "bg_dark":       "#0f0f1a",
    "bg_surface":    "#1a1a2e",
    "bg_card":       "#242442",
    "bg_input":      "#16213e",
    "bg_hover":      "#2a2a4a",
    "accent":        "#7c3aed",
    "accent_hover":  "#6d28d9",
    "accent_light":  "#a78bfa",
    "cyan":          "#06b6d4",
    "green":         "#22c55e",
    "red":           "#ef4444",
    "amber":         "#f59e0b",
    "text_primary":  "#e2e8f0",
    "text_secondary":"#94a3b8",
    "text_muted":    "#64748b",
    "border":        "#334155",
    "border_focus":  "#7c3aed",
}

FONT_FAMILY = "Helvetica"
FONT_MONO = "Courier"

# SQL keyword color map for syntax highlighting
SQL_KEYWORDS = {
    "SELECT": "#c084fc", "FROM": "#c084fc", "WHERE": "#c084fc",
    "JOIN": "#c084fc", "INNER": "#c084fc", "LEFT": "#c084fc",
    "RIGHT": "#c084fc", "OUTER": "#c084fc", "CROSS": "#c084fc",
    "ON": "#c084fc", "AND": "#c084fc", "OR": "#c084fc",
    "GROUP": "#c084fc", "BY": "#c084fc", "ORDER": "#c084fc",
    "HAVING": "#c084fc", "LIMIT": "#c084fc", "OFFSET": "#c084fc",
    "AS": "#c084fc", "IN": "#c084fc", "NOT": "#c084fc",
    "NULL": "#c084fc", "IS": "#c084fc", "LIKE": "#c084fc",
    "BETWEEN": "#c084fc", "EXISTS": "#c084fc", "DISTINCT": "#c084fc",
    "UNION": "#c084fc", "INTERSECT": "#c084fc", "EXCEPT": "#c084fc",
    "INSERT": "#c084fc", "UPDATE": "#c084fc", "DELETE": "#c084fc",
    "CREATE": "#c084fc", "DROP": "#c084fc", "ALTER": "#c084fc",
    "WITH": "#c084fc", "FETCH": "#c084fc", "INTO": "#c084fc",
    "VALUES": "#c084fc", "SET": "#c084fc", "DESC": "#c084fc",
    "ASC": "#c084fc", "CASE": "#c084fc", "WHEN": "#c084fc",
    "THEN": "#c084fc", "ELSE": "#c084fc", "END": "#c084fc",
    # Aggregate functions
    "SUM": "#fbbf24", "COUNT": "#fbbf24", "AVG": "#fbbf24",
    "MIN": "#fbbf24", "MAX": "#fbbf24",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Tooltip helper
# ═══════════════════════════════════════════════════════════════════════════════

class ToolTip:
    """Hover tooltip for canvas items."""
    def __init__(self, canvas, item_id, text):
        self.canvas = canvas
        self.item_id = item_id
        self.text = text
        self.tip_window = None
        canvas.tag_bind(item_id, "<Enter>", self.show)
        canvas.tag_bind(item_id, "<Leave>", self.hide)

    def show(self, event):
        x = event.x_root + 15
        y = event.y_root + 10
        self.tip_window = tw = tk.Toplevel(self.canvas)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=COLORS["bg_card"])

        frame = tk.Frame(tw, bg=COLORS["bg_card"], bd=1, relief=tk.SOLID,
                         highlightbackground=COLORS["border"], highlightthickness=1)
        frame.pack()
        label = tk.Label(frame, text=self.text, justify=tk.LEFT,
                         bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                         font=(FONT_FAMILY, 10), padx=8, pady=6, wraplength=350)
        label.pack()

    def hide(self, event):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ═══════════════════════════════════════════════════════════════════════════════
#  Main application class
# ═══════════════════════════════════════════════════════════════════════════════

class QueryAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("SC3020 — Query Plan Annotator")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        self.root.configure(bg=COLORS["bg_dark"])

        self.current_qep = None
        self.last_query = ""
        self.last_annotations = []
        self.last_annotated_sql = ""
        self.conn = None
        self.tooltips = []

        # Try to maximize
        try:
            self.root.state("zoomed")
        except Exception:
            try:
                self.root.attributes("-zoomed", True)
            except Exception:
                pass

        self._configure_styles()
        self._create_widgets()

    # ──────────────────────────────────────────────────────────────────────────
    #  Theme / style configuration
    # ──────────────────────────────────────────────────────────────────────────

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # General
        style.configure(".", background=COLORS["bg_dark"], foreground=COLORS["text_primary"],
                        fieldbackground=COLORS["bg_input"], font=(FONT_FAMILY, 11))

        # Frames
        style.configure("Dark.TFrame", background=COLORS["bg_dark"])
        style.configure("Surface.TFrame", background=COLORS["bg_surface"])
        style.configure("Card.TFrame", background=COLORS["bg_card"])

        # Labels
        style.configure("Dark.TLabel", background=COLORS["bg_dark"], foreground=COLORS["text_primary"],
                        font=(FONT_FAMILY, 11))
        style.configure("Surface.TLabel", background=COLORS["bg_surface"], foreground=COLORS["text_primary"],
                        font=(FONT_FAMILY, 11))
        style.configure("Title.TLabel", background=COLORS["bg_dark"], foreground=COLORS["text_primary"],
                        font=(FONT_FAMILY, 14, "bold"))
        style.configure("SectionTitle.TLabel", background=COLORS["bg_dark"],
                        foreground=COLORS["accent_light"], font=(FONT_FAMILY, 12, "bold"))
        style.configure("Status.TLabel", background=COLORS["bg_surface"],
                        foreground=COLORS["text_secondary"], font=(FONT_FAMILY, 10))
        style.configure("StatusGreen.TLabel", background=COLORS["bg_surface"],
                        foreground=COLORS["green"], font=(FONT_FAMILY, 10))
        style.configure("StatusRed.TLabel", background=COLORS["bg_surface"],
                        foreground=COLORS["red"], font=(FONT_FAMILY, 10))

        # Entries
        style.configure("Dark.TEntry", fieldbackground=COLORS["bg_input"],
                        foreground=COLORS["text_primary"], insertcolor=COLORS["text_primary"],
                        borderwidth=1, relief="solid")
        style.map("Dark.TEntry",
                  fieldbackground=[("focus", COLORS["bg_input"])],
                  bordercolor=[("focus", COLORS["border_focus"])])

        # Buttons
        style.configure("Accent.TButton", background=COLORS["accent"],
                        foreground="white", font=(FONT_FAMILY, 11, "bold"),
                        padding=(16, 8), borderwidth=0)
        style.map("Accent.TButton",
                  background=[("active", COLORS["accent_hover"]),
                              ("pressed", COLORS["accent_hover"])])

        style.configure("Secondary.TButton", background=COLORS["bg_card"],
                        foreground=COLORS["text_primary"], font=(FONT_FAMILY, 10),
                        padding=(12, 6), borderwidth=1)
        style.map("Secondary.TButton",
                  background=[("active", COLORS["bg_hover"])])

        # Notebook (tabs)
        style.configure("Dark.TNotebook", background=COLORS["bg_dark"],
                        borderwidth=0, tabmargins=[0, 0, 0, 0])
        style.configure("Dark.TNotebook.Tab", background=COLORS["bg_surface"],
                        foreground=COLORS["text_secondary"], font=(FONT_FAMILY, 11),
                        padding=(16, 8), borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", COLORS["bg_card"])],
                  foreground=[("selected", COLORS["accent_light"])])

        # PanedWindow
        style.configure("Dark.TPanedwindow", background=COLORS["bg_dark"])

        # Scrollbar
        style.configure("Dark.Vertical.TScrollbar", background=COLORS["bg_surface"],
                        troughcolor=COLORS["bg_dark"], arrowcolor=COLORS["text_muted"],
                        borderwidth=0)
        style.configure("Dark.Horizontal.TScrollbar", background=COLORS["bg_surface"],
                        troughcolor=COLORS["bg_dark"], arrowcolor=COLORS["text_muted"],
                        borderwidth=0)

    # ──────────────────────────────────────────────────────────────────────────
    #  Widget creation
    # ──────────────────────────────────────────────────────────────────────────

    def _create_widgets(self):
        # ── Title bar ────────────────────────────────────────────────────────
        title_frame = ttk.Frame(self.root, style="Dark.TFrame")
        title_frame.pack(fill=tk.X, padx=20, pady=(15, 5))
        ttk.Label(title_frame, text="⚡ Query Plan Annotator", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(title_frame, text="SC3020 Database System Principles",
                  style="Status.TLabel").pack(side=tk.RIGHT)

        # ── Connection bar ───────────────────────────────────────────────────
        conn_frame = ttk.Frame(self.root, style="Surface.TFrame")
        conn_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        conn_inner = ttk.Frame(conn_frame, style="Surface.TFrame")
        conn_inner.pack(fill=tk.X, padx=15, pady=10)

        fields = [
            ("Host:", "host_entry", "localhost", 12),
            ("Port:", "port_entry", "5432", 6),
            ("Database:", "db_entry", "TPC-H", 15),
            ("User:", "user_entry", "postgres", 10),
        ]
        for label_text, attr_name, default, width in fields:
            ttk.Label(conn_inner, text=label_text, style="Surface.TLabel").pack(side=tk.LEFT, padx=(0, 3))
            entry = ttk.Entry(conn_inner, width=width, style="Dark.TEntry")
            entry.insert(0, default)
            entry.pack(side=tk.LEFT, padx=(0, 12))
            setattr(self, attr_name, entry)

        ttk.Label(conn_inner, text="Password:", style="Surface.TLabel").pack(side=tk.LEFT, padx=(0, 3))
        self.pass_entry = ttk.Entry(conn_inner, width=12, style="Dark.TEntry", show="•")
        self.pass_entry.pack(side=tk.LEFT, padx=(0, 12))

        self.connect_btn = ttk.Button(conn_inner, text="Connect", style="Secondary.TButton",
                                      command=self._connect)
        self.connect_btn.pack(side=tk.LEFT, padx=(5, 5))

        self.conn_status_label = ttk.Label(conn_inner, text="● Disconnected", style="StatusRed.TLabel")
        self.conn_status_label.pack(side=tk.LEFT, padx=(10, 0))

        # ── Main split: left (query input) | right (output tabs) ────────────
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL, style="Dark.TPanedwindow")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 5))

        # Left panel — SQL input
        left_frame = ttk.Frame(main_pane, style="Dark.TFrame")
        main_pane.add(left_frame, weight=1)

        ttk.Label(left_frame, text="SQL Query", style="SectionTitle.TLabel").pack(anchor=tk.W, pady=(0, 5))

        # SQL text widget with dark theme
        sql_frame = tk.Frame(left_frame, bg=COLORS["border"], bd=1, relief=tk.FLAT)
        sql_frame.pack(fill=tk.BOTH, expand=True)

        self.query_input = tk.Text(
            sql_frame, wrap=tk.WORD,
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent_light"],
            selectbackground=COLORS["accent"],
            selectforeground="white",
            font=(FONT_MONO, 12),
            padx=12, pady=10,
            relief=tk.FLAT, bd=0,
            undo=True
        )
        sql_scrollbar = ttk.Scrollbar(sql_frame, orient=tk.VERTICAL,
                                      command=self.query_input.yview,
                                      style="Dark.Vertical.TScrollbar")
        self.query_input.configure(yscrollcommand=sql_scrollbar.set)
        sql_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.query_input.pack(fill=tk.BOTH, expand=True)

        # Bind syntax highlighting
        self.query_input.bind("<KeyRelease>", self._highlight_sql)

        # Buttons
        btn_frame = ttk.Frame(left_frame, style="Dark.TFrame")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.execute_btn = ttk.Button(btn_frame, text="▶  Execute & Annotate",
                                      style="Accent.TButton", command=self.run_algorithm)
        self.execute_btn.pack(side=tk.LEFT)

        self.clear_btn = ttk.Button(btn_frame, text="Clear", style="Secondary.TButton",
                                    command=lambda: self.query_input.delete("1.0", tk.END))
        self.clear_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Right panel — Tabbed output
        right_frame = ttk.Frame(main_pane, style="Dark.TFrame")
        main_pane.add(right_frame, weight=2)

        self.notebook = ttk.Notebook(right_frame, style="Dark.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Annotated SQL (Visual)
        tab1 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab1, text="  Annotated SQL  ")
        self._create_annotation_canvas(tab1)

        # Tab 2: Annotated SQL (Text)
        tab2 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab2, text="  SQL with Comments  ")
        self._create_text_tab(tab2)

        # Tab 3: QEP Tree
        tab3 = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab3, text="  QEP Tree  ")
        self._create_qep_canvas(tab3)

        # ── Status bar ───────────────────────────────────────────────────────
        status_frame = ttk.Frame(self.root, style="Surface.TFrame")
        status_frame.pack(fill=tk.X, padx=20, pady=(5, 15))

        self.status_label = ttk.Label(status_frame, text="Ready — enter a query and click Execute",
                                      style="Status.TLabel")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)

        self.annotation_count_label = ttk.Label(status_frame, text="", style="Status.TLabel")
        self.annotation_count_label.pack(side=tk.RIGHT, padx=10, pady=5)

    # ──────────────────────────────────────────────────────────────────────────
    #  Create sub-panels
    # ──────────────────────────────────────────────────────────────────────────

    def _create_annotation_canvas(self, parent):
        """Tab 1: visual annotated SQL with arrows."""
        canvas_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.annotation_canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_dark"],
                                           highlightthickness=0)
        vbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                             command=self.annotation_canvas.yview,
                             style="Dark.Vertical.TScrollbar")
        hbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL,
                             command=self.annotation_canvas.xview,
                             style="Dark.Horizontal.TScrollbar")
        self.annotation_canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        self.annotation_canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

    def _create_text_tab(self, parent):
        """Tab 2: annotated SQL as plain text with inline comments."""
        toolbar = ttk.Frame(parent, style="Dark.TFrame")
        toolbar.pack(fill=tk.X, pady=(5, 0), padx=5)

        copy_btn = ttk.Button(toolbar, text="📋 Copy to Clipboard",
                              style="Secondary.TButton", command=self._copy_annotated_sql)
        copy_btn.pack(side=tk.RIGHT, padx=5)

        text_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.annotated_text = tk.Text(
            text_frame, wrap=tk.WORD,
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            font=(FONT_MONO, 12),
            padx=12, pady=10,
            relief=tk.FLAT, bd=0,
            state=tk.DISABLED
        )
        text_scroll = ttk.Scrollbar(text_frame, orient=tk.VERTICAL,
                                    command=self.annotated_text.yview,
                                    style="Dark.Vertical.TScrollbar")
        self.annotated_text.configure(yscrollcommand=text_scroll.set)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.annotated_text.pack(fill=tk.BOTH, expand=True)

    def _create_qep_canvas(self, parent):
        """Tab 3: QEP tree visualisation."""
        canvas_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.qep_canvas = tk.Canvas(canvas_frame, bg=COLORS["bg_dark"],
                                    highlightthickness=0)
        vbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                             command=self.qep_canvas.yview,
                             style="Dark.Vertical.TScrollbar")
        hbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL,
                             command=self.qep_canvas.xview,
                             style="Dark.Horizontal.TScrollbar")
        self.qep_canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        self.qep_canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

    # ──────────────────────────────────────────────────────────────────────────
    #  Syntax highlighting
    # ──────────────────────────────────────────────────────────────────────────

    def _highlight_sql(self, event=None):
        """Apply basic keyword coloring to the SQL input."""
        self.query_input.tag_remove("keyword", "1.0", tk.END)
        self.query_input.tag_remove("function", "1.0", tk.END)
        self.query_input.tag_remove("string", "1.0", tk.END)
        self.query_input.tag_remove("number", "1.0", tk.END)

        self.query_input.tag_configure("keyword", foreground="#c084fc")
        self.query_input.tag_configure("function", foreground="#fbbf24")
        self.query_input.tag_configure("string", foreground="#86efac")
        self.query_input.tag_configure("number", foreground="#67e8f9")

        content = self.query_input.get("1.0", tk.END)

        import re

        # Highlight strings
        for match in re.finditer(r"'[^']*'", content):
            start_idx = f"1.0 + {match.start()} chars"
            end_idx = f"1.0 + {match.end()} chars"
            self.query_input.tag_add("string", start_idx, end_idx)

        # Highlight numbers
        for match in re.finditer(r'\b\d+\.?\d*\b', content):
            start_idx = f"1.0 + {match.start()} chars"
            end_idx = f"1.0 + {match.end()} chars"
            self.query_input.tag_add("number", start_idx, end_idx)

        # Highlight keywords
        for word, color in SQL_KEYWORDS.items():
            pattern = r'\b' + word + r'\b'
            tag_name = "function" if color == "#fbbf24" else "keyword"
            for match in re.finditer(pattern, content, re.IGNORECASE):
                start_idx = f"1.0 + {match.start()} chars"
                end_idx = f"1.0 + {match.end()} chars"
                self.query_input.tag_add(tag_name, start_idx, end_idx)

    # ──────────────────────────────────────────────────────────────────────────
    #  Connection handling
    # ──────────────────────────────────────────────────────────────────────────

    def _connect(self):
        """Establish a database connection."""
        try:
            if self.conn:
                try:
                    self.conn.close()
                except Exception:
                    pass

            self.conn = preprocessing.get_connection(
                host=self.host_entry.get(),
                dbname=self.db_entry.get(),
                user=self.user_entry.get(),
                password=self.pass_entry.get(),
                port=self.port_entry.get()
            )
            self.conn_status_label.configure(text="● Connected", style="StatusGreen.TLabel")
            self.status_label.configure(text=f"Connected to {self.db_entry.get()}")
        except Exception as e:
            self.conn_status_label.configure(text="● Disconnected", style="StatusRed.TLabel")
            messagebox.showerror("Connection Error", f"Failed to connect:\n{str(e)}")

    # ──────────────────────────────────────────────────────────────────────────
    #  Core algorithm execution
    # ──────────────────────────────────────────────────────────────────────────

    def run_algorithm(self):
        query_text = self.query_input.get("1.0", tk.END).strip()
        if not query_text:
            messagebox.showwarning("Input Error", "Please enter an SQL query.")
            return

        self.status_label.configure(text="Executing query...")
        self.root.update_idletasks()

        start_time = time.time()

        try:
            # Auto-connect if not connected
            if not self.conn:
                self._connect()
            if not self.conn:
                return

            # 1. Get QEP
            qep = preprocessing.get_qep(self.conn, query_text)
            self.current_qep = qep

            # 2. Get all AQPs
            aqps = preprocessing.get_all_aqps(self.conn, query_text, qep)

            # 3. Compare costs
            aqp_comparisons = annotation.compare_aqp_costs(qep, aqps)

            # 4. Generate annotations
            generated_annotations = annotation.generate_annotations(qep, aqp_comparisons, query_text)

            # 5. Generate annotated SQL text
            annotated_sql = annotation.generate_annotated_sql(query_text, generated_annotations)

            # Store results
            self.last_query = query_text
            self.last_annotations = generated_annotations
            self.last_annotated_sql = annotated_sql

            elapsed = time.time() - start_time

            # Update all three tabs
            self._draw_visual_annotations(query_text, generated_annotations)
            self._update_text_tab(annotated_sql)
            self._draw_qep_tree()

            # Update status
            self.status_label.configure(
                text=f"Done in {elapsed:.2f}s — QEP cost: {qep.get('Total Cost', 0):.2f}"
            )
            self.annotation_count_label.configure(
                text=f"{len(generated_annotations)} annotation(s) generated"
            )

        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
            messagebox.showerror("Execution Error", f"Failed to execute:\n{str(e)}")

    # ──────────────────────────────────────────────────────────────────────────
    #  Tab 1: Visual Annotated SQL
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_visual_annotations(self, query_text, generated_annotations):
        """Draw the SQL query with annotation boxes and arrows on the canvas."""
        if not query_text:
            return

        canvas = self.annotation_canvas
        canvas.delete("all")
        self.tooltips = []

        self.root.update_idletasks()
        canvas_width = canvas.winfo_width()
        if canvas_width < 100:
            canvas_width = 1200

        lines = query_text.split("\n")
        sql_start_x = 30
        sql_start_y = 50
        line_height = 32
        char_width = 9

        # ── Draw SQL lines ───────────────────────────────────────────────────
        # Background for SQL area
        max_line_len = max(len(line) for line in lines) if lines else 0
        sql_bg_width = max(sql_start_x + max_line_len * char_width + 40, 400)
        sql_bg_height = sql_start_y + len(lines) * line_height + 20

        canvas.create_rectangle(
            15, 20, sql_bg_width, sql_bg_height,
            fill=COLORS["bg_input"], outline=COLORS["border"], width=1
        )
        canvas.create_text(
            25, 30, text="SQL Query", anchor=tk.NW,
            font=(FONT_FAMILY, 9), fill=COLORS["text_muted"]
        )

        line_y_coords = {}
        for i, line in enumerate(lines):
            y_pos = sql_start_y + (i * line_height)
            # Line number
            canvas.create_text(
                sql_start_x - 10, y_pos, text=str(i + 1), anchor=tk.E,
                font=(FONT_MONO, 10), fill=COLORS["text_muted"]
            )
            # SQL text
            canvas.create_text(
                sql_start_x, y_pos, text=line, anchor=tk.W,
                font=(FONT_MONO, 11), fill=COLORS["text_primary"]
            )
            line_y_coords[i] = y_pos

        # ── Draw annotation boxes ────────────────────────────────────────────
        box_width = 380
        box_x_start = sql_bg_width + 60
        current_box_y = sql_start_y + 10

        for anno in generated_annotations:
            category = anno.get("category", "other")
            colors = annotation.CATEGORY_COLORS.get(category, annotation.CATEGORY_COLORS["other"])

            text = anno["text"]
            # Calculate box height based on text length
            estimated_lines = max(1, len(text) // 45 + text.count("\n") + 1)
            box_height = max(60, estimated_lines * 18 + 20)

            x1 = box_x_start
            y1 = current_box_y - box_height / 2
            x2 = box_x_start + box_width
            y2 = current_box_y + box_height / 2

            # Box background
            box_id = canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=colors["bg"], outline=colors["border"], width=2
            )

            # Node type label (header)
            node_label = anno["node_type"]
            if anno["relation"]:
                node_label += f"  ({anno['relation']})"
            canvas.create_text(
                x1 + 12, y1 + 14, text=node_label, anchor=tk.NW,
                font=(FONT_FAMILY, 10, "bold"), fill=colors["fg"]
            )

            # ── Separator line ───────────────────────────────────────────────
            sep_y = y1 + 28
            canvas.create_line(x1 + 8, sep_y, x2 - 8, sep_y,
                               fill=colors["border"], width=1, dash=(2, 2))

            # Annotation text (body)
            text_id = canvas.create_text(
                x1 + 12, sep_y + 6, text=text, anchor=tk.NW,
                font=(FONT_FAMILY, 9), fill=colors["fg"],
                width=box_width - 24, justify=tk.LEFT
            )

            # Tooltip with full details
            ToolTip(canvas, box_id, f"[{anno['node_type']}]\n{text}")

            # ── Arrow to SQL line ────────────────────────────────────────────
            target_line = anno.get("target_line_idx", 0)
            if target_line in line_y_coords:
                arrow_start_x = x1
                arrow_start_y = current_box_y
                arrow_end_y = line_y_coords[target_line]

                # Find target x position
                line_str = lines[target_line].lower()
                relation = anno.get("relation", "").lower()
                keyword = relation if relation else ""
                if not keyword:
                    if "join" in anno["node_type"].lower():
                        keyword = "join"
                    elif "loop" in anno["node_type"].lower():
                        keyword = "where"

                if keyword and keyword in line_str:
                    char_idx = line_str.find(keyword)
                    arrow_end_x = sql_start_x + (char_idx + len(keyword) / 2) * char_width
                else:
                    arrow_end_x = sql_start_x + len(line_str.rstrip()) * char_width + 15

                arrow_end_x = min(arrow_end_x, arrow_start_x - 15)

                # Draw curved arrow with a bezier-like path
                mid_x = (arrow_start_x + arrow_end_x) / 2
                canvas.create_line(
                    arrow_start_x, arrow_start_y,
                    mid_x, arrow_start_y,
                    mid_x, arrow_end_y,
                    arrow_end_x, arrow_end_y,
                    smooth=True, arrow=tk.LAST,
                    fill=colors["border"], width=2
                )

                # Small dot at the arrow target
                canvas.create_oval(
                    arrow_end_x - 4, arrow_end_y - 4,
                    arrow_end_x + 4, arrow_end_y + 4,
                    fill=colors["border"], outline=""
                )

            current_box_y += box_height + 20

        # Update scroll region
        bbox = canvas.bbox("all")
        if bbox:
            canvas.config(scrollregion=(bbox[0] - 20, bbox[1] - 20,
                                        bbox[2] + 40, bbox[3] + 40))

    # ──────────────────────────────────────────────────────────────────────────
    #  Tab 2: Annotated SQL text
    # ──────────────────────────────────────────────────────────────────────────

    def _update_text_tab(self, annotated_sql):
        """Display the annotated SQL text with inline comments."""
        self.annotated_text.configure(state=tk.NORMAL)
        self.annotated_text.delete("1.0", tk.END)

        # Configure tags for coloring comments
        self.annotated_text.tag_configure("comment", foreground=COLORS["green"])
        self.annotated_text.tag_configure("sql", foreground=COLORS["text_primary"])

        for line in annotated_sql.split("\n"):
            if "/*" in line and "*/" in line:
                # Split into SQL part and comment part
                parts = line.split("/*", 1)
                sql_part = parts[0]
                comment_part = "/*" + parts[1]

                self.annotated_text.insert(tk.END, sql_part, "sql")
                self.annotated_text.insert(tk.END, comment_part + "\n", "comment")
            else:
                self.annotated_text.insert(tk.END, line + "\n", "sql")

        self.annotated_text.configure(state=tk.DISABLED)

    def _copy_annotated_sql(self):
        """Copy the annotated SQL to the system clipboard."""
        if self.last_annotated_sql:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.last_annotated_sql)
            self.status_label.configure(text="Annotated SQL copied to clipboard!")
        else:
            self.status_label.configure(text="No annotated SQL to copy")

    # ──────────────────────────────────────────────────────────────────────────
    #  Tab 3: QEP Tree
    # ──────────────────────────────────────────────────────────────────────────

    def _draw_qep_tree(self):
        """Draw the QEP as a color-coded tree."""
        if not self.current_qep:
            return

        canvas = self.qep_canvas
        canvas.delete("all")
        self.tooltips = []

        self.root.update_idletasks()
        canvas_width = canvas.winfo_width()
        start_x = canvas_width / 2 if canvas_width > 100 else 500

        self._draw_qep_node(canvas, self.current_qep, start_x, 50, 200)

        bbox = canvas.bbox("all")
        if bbox:
            canvas.config(scrollregion=(bbox[0] - 60, bbox[1] - 60,
                                        bbox[2] + 60, bbox[3] + 60))

    def _draw_qep_node(self, canvas, node, x, y, x_offset):
        """Recursively draw a single QEP node and its children."""
        node_type = node.get("Node Type", "Unknown")
        relation_name = node.get("Relation Name")
        total_cost = node.get("Total Cost", 0)
        plan_rows = node.get("Plan Rows", 0)
        plan_width = node.get("Plan Width", 0)
        startup_cost = node.get("Startup Cost", 0)

        # Build display text
        if relation_name:
            display_text = f"{node_type}\n({relation_name})"
            box_height = 52
        else:
            display_text = node_type
            box_height = 36

        cost_text = f"Cost: {total_cost:.1f}"

        # Get category colors
        category = annotation.NODE_CATEGORIES.get(node_type, "other")
        colors = annotation.CATEGORY_COLORS.get(category, annotation.CATEGORY_COLORS["other"])

        # Draw children first (so lines are behind nodes)
        children = node.get("Plans", [])
        child_y = y + 85

        if len(children) == 1:
            child_positions = [x]
        elif len(children) == 2:
            child_positions = [x - x_offset, x + x_offset]
        else:
            total_width = (len(children) - 1) * x_offset
            start = x - total_width / 2
            child_positions = [start + i * x_offset for i in range(len(children))]

        for i, child in enumerate(children):
            child_x = child_positions[i]
            # Draw connection line
            canvas.create_line(
                x, y + box_height / 2, child_x, child_y - box_height / 2,
                fill=COLORS["border"], width=2
            )
            next_offset = max(100, x_offset / 1.6)
            self._draw_qep_node(canvas, child, child_x, child_y, next_offset)

        # Draw the node box
        box_width = 140
        x1, y1 = x - box_width / 2, y - box_height / 2
        x2, y2 = x + box_width / 2, y + box_height / 2

        # Shadow
        canvas.create_rectangle(
            x1 + 3, y1 + 3, x2 + 3, y2 + 3,
            fill="#0a0a16", outline=""
        )

        # Main box
        box_id = canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=colors["bg"], outline=colors["border"], width=2
        )

        # Node text
        canvas.create_text(
            x, y - 4, text=display_text,
            fill=colors["fg"], font=(FONT_FAMILY, 10, "bold"), justify=tk.CENTER
        )

        # Cost label below box
        canvas.create_text(
            x, y2 + 10, text=cost_text,
            fill=COLORS["text_muted"], font=(FONT_FAMILY, 8)
        )

        # Tooltip
        tooltip_text = (
            f"Node Type: {node_type}\n"
            f"Startup Cost: {startup_cost:.2f}\n"
            f"Total Cost: {total_cost:.2f}\n"
            f"Plan Rows: {plan_rows}\n"
            f"Plan Width: {plan_width}"
        )
        if relation_name:
            tooltip_text = f"Relation: {relation_name}\n" + tooltip_text

        tip = ToolTip(canvas, box_id, tooltip_text)
        self.tooltips.append(tip)