import tkinter as tk
from tkinter import ttk, messagebox
import preprocessing
import annotation

class QueryAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("Query Annotator")
        self.root.geometry("1200x800")
        self.current_qep = None

        self.last_query = ""
        self.last_annotations = []
        self.is_fullscreen = False


        try:
            self.root.state('zoomed')
        except:
            self.root.attributes('-zoomed', True)

        
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        self.create_widgets()

    def create_widgets(self):
        db_frame = ttk.Frame(self.root, padding="10")
        db_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(db_frame, text="DB Name:").pack(side=tk.LEFT)
        self.db_name = ttk.Entry(db_frame, width=15)
        self.db_name.insert(0, "SC3020 Assignment 1")
        self.db_name.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(db_frame, text="DB User:").pack(side=tk.LEFT)
        self.db_user = ttk.Entry(db_frame, width=10)
        self.db_user.insert(0, "postgres")
        self.db_user.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(db_frame, text="Password:").pack(side=tk.LEFT)
        self.db_pass = ttk.Entry(db_frame, width=15, show="*")
        self.db_pass.pack(side=tk.LEFT, padx=5)


        self.main_split = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        self.main_split.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.top_split = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_split.add(self.top_split, weight=1)

        

        left_input_frame = ttk.Frame(self.top_split)
        self.top_split.add(left_input_frame, weight=1)

        
        ttk.Label(left_input_frame, text="Input SQL Query:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.query_input = tk.Text(left_input_frame, height=10, wrap=tk.WORD, font=("Helvetica", 11))
        self.query_input.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_frame = ttk.Frame(left_input_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.execute_btn = ttk.Button(btn_frame, text="Execute & Annotate", command=self.run_algorithm)
        self.execute_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.visualise_btn = ttk.Button(btn_frame, text="Visualise QEP Tree", command=self.visualise_qep)
        self.visualise_btn.pack(side=tk.LEFT)


        right_qep_frame = ttk.Frame(self.top_split)
        self.top_split.add(right_qep_frame, weight=1)
        ttk.Label(right_qep_frame, text="QEP Visualisation:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
        qep_canvas_frame = ttk.Frame(right_qep_frame, relief=tk.SUNKEN, borderwidth=1)
        qep_canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.qep_canvas = tk.Canvas(qep_canvas_frame, bg="white")
        qep_vbar = ttk.Scrollbar(qep_canvas_frame, orient=tk.VERTICAL, command=self.qep_canvas.yview)
        qep_hbar = ttk.Scrollbar(qep_canvas_frame, orient=tk.HORIZONTAL, command=self.qep_canvas.xview)
        self.qep_canvas.configure(yscrollcommand=qep_vbar.set, xscrollcommand=qep_hbar.set)
        self.qep_canvas.grid(row=0, column=0, sticky="nsew")
        qep_vbar.grid(row=0, column=1, sticky="ns")
        qep_hbar.grid(row=1, column=0, sticky="ew")
        qep_canvas_frame.grid_rowconfigure(0, weight=1)
        qep_canvas_frame.grid_columnconfigure(0, weight=1)

        self.bottom_frame = ttk.Frame(self.main_split)
        self.main_split.add(self.bottom_frame, weight=1)
        toolbar = ttk.Frame(self.bottom_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(toolbar, text="Annotated Query Output:", font=("Helvetica", 12, "bold")).pack(side=tk.LEFT)
        self.fs_btn = ttk.Button(toolbar, text="⛶ Full Screen Annotations", command=self.toggle_fullscreen)
        self.fs_btn.pack(side=tk.RIGHT)
        anno_canvas_frame = ttk.Frame(self.bottom_frame, relief=tk.SUNKEN, borderwidth=1)
        anno_canvas_frame.pack(fill=tk.BOTH, expand=True)
        self.annotation_canvas = tk.Canvas(anno_canvas_frame, bg="white")
        anno_vbar = ttk.Scrollbar(anno_canvas_frame, orient=tk.VERTICAL, command=self.annotation_canvas.yview)
        anno_hbar = ttk.Scrollbar(anno_canvas_frame, orient=tk.HORIZONTAL, command=self.annotation_canvas.xview)
        self.annotation_canvas.configure(yscrollcommand=anno_vbar.set, xscrollcommand=anno_hbar.set)
        self.annotation_canvas.grid(row=0, column=0, sticky="nsew")
        anno_vbar.grid(row=0, column=1, sticky="ns")
        anno_hbar.grid(row=1, column=0, sticky="ew")
        anno_canvas_frame.grid_rowconfigure(0, weight=1)
        anno_canvas_frame.grid_columnconfigure(0, weight=1)

    def toggle_fullscreen(self):
        if not self.is_fullscreen:
            self.main_split.forget(self.top_split)
            self.fs_btn.config(text="⛶ Exit Full Screen Annotations")
            self.is_fullscreen = True
        else:
            self.main_split.insert(0, self.top_split, weight=1)
            self.fs_btn.config(text="⛶ Full Screen Annotations")
            self.is_fullscreen = False

        self.root.after(100, lambda: self.draw_visual_annotations(self.last_query, self.last_annotations))


    def run_algorithm(self):
        query_text = self.query_input.get("1.0", tk.END).strip()
        if not query_text:
            messagebox.showwarning("Input Error", "Please enter an SQL query.")
            return

        try:
            conn = preprocessing.get_connection(
                host="localhost", 
                dbname= self.db_name.get(), 
                user=self.db_user.get(), 
                password=self.db_pass.get(), 
                port="5432"
            )
            
            qep = preprocessing.get_qep(conn, query_text)
            self.current_qep = qep 
            
            aqps = preprocessing.get_all_aqps(conn, query_text, qep)
            aqp_comparisons = annotation.compare_aqp_costs(qep, aqps)
            
            generated_annotations = annotation.generate_annotations(qep, aqp_comparisons, query_text)

            self.last_query = query_text
            self.last_annotations = generated_annotations
            
            self.draw_visual_annotations(query_text, generated_annotations)
            self.visualise_qep() 
            
            conn.close()
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to execute: {str(e)}")

    def draw_visual_annotations(self, query_text, generated_annotations):
        if not query_text:
            return

        self.annotation_canvas.delete("all")
        lines = query_text.split("\n")
        self.root.update_idletasks()
        canvas_width = self.annotation_canvas.winfo_width()
        if canvas_width < 100: canvas_width = 1200

        sql_start_x = 20
        sql_start_y = 40
        line_height = 40
        char_width = 9
        line_y_coords = {}

        max_line_len = max([len(line) for line in lines] + [0])
        max_text_width = sql_start_x + (max_line_len * char_width)


        for i, line in enumerate(lines):
            y_pos = sql_start_y + (i * line_height)
            self.annotation_canvas.create_text(sql_start_x, y_pos, text=line, anchor=tk.W, font=("Courier", 11))
            line_y_coords[i] = y_pos
        
        box_width = 360
        desired_x_center = canvas_width - (box_width / 2) - 40
        safe_x_center = max_text_width + (box_width / 2) + 60
        box_x_center = max(desired_x_center, safe_x_center)
        current_box_y = 60

        for i, anno in enumerate(generated_annotations):
            box_height = 80
            
            self.annotation_canvas.create_rectangle(
                box_x_center - box_width / 2, current_box_y - box_height / 2, 
                box_x_center + box_width / 2, current_box_y + box_height / 2, 
                fill="#a0c4ff", outline="#4a4e69", width=2
            )
            self.annotation_canvas.create_text(
                box_x_center, current_box_y, text=anno["text"], 
                anchor=tk.CENTER, font=("Helvetica", 9), justify=tk.CENTER, width=box_width - 20
            )

            target_line = anno.get("target_line_idx", 0)
            if target_line in line_y_coords:
                start_arrow_x = box_x_center - box_width / 2
                start_arrow_y = current_box_y
                end_arrow_y = line_y_coords[target_line]
                line_str = lines[target_line].lower()
                relation = anno.get("relation", "")
                node_type = anno.get("node_type", "")

                keyword = relation.lower() if relation else ""
                if not keyword:
                    if "join" in node_type.lower(): keyword = "join"
                    elif "loop" in node_type.lower(): keyword = "where"
                
                if keyword and keyword in line_str:
                    char_idx = line_str.find(keyword)
                    end_arrow_x = sql_start_x + (char_idx * char_width) + (len(keyword) * char_width / 2)
                else: 
                    end_arrow_x = sql_start_x + (len(line_str) * char_width) + 20

                
                end_arrow_x = min(end_arrow_x, start_arrow_x - 10)
                self.annotation_canvas.create_line(start_arrow_x, start_arrow_y, end_arrow_x, end_arrow_y, arrow=tk.LAST, fill="#4a4e69", width=2)
            
            current_box_y += 100
        self.annotation_canvas.config(scrollregion=self.annotation_canvas.bbox("all"))

    def visualise_qep(self):
        if not self.current_qep:
            return
            
        self.qep_canvas.delete("all")
        self.root.update_idletasks()
        canvas_width = self.qep_canvas.winfo_width()
        start_x = canvas_width / 2 if canvas_width > 100 else 400
        self.draw_qep_node(self.qep_canvas, self.current_qep, start_x, 40, 180)

        bbox = self.qep_canvas.bbox("all")
        if bbox:
            self.qep_canvas.config(scrollregion=(bbox[0]-50, bbox[1]-50, bbox[2]+50, bbox[3]+50))


    def draw_qep_node(self, canvas, node, x, y, x_offset):
        node_type = node.get("Node Type", "Unknown")
        relation_name = node.get("Relation Name", None)

        if relation_name:
            display_text = f"{node_type}\n({relation_name})"
            box_height = 45
        else:
            display_text = node_type
            box_height = 30

        children = node.get("Plans", [])
        child_y = y + 65

        child_x_positions = [x] if len(children) == 1 else [x - x_offset, x + x_offset] if len(children) == 2 else [x - x_offset + (i * 80) for i in range(len(children))]
        
        for i, child in enumerate(children):
            child_x = child_x_positions[i]
            canvas.create_line(x, y, child_x, child_y, fill="#cccccc", width=2)
            next_offset = max(115, x_offset / 1.5)
            self.draw_qep_node(canvas, child, child_x, child_y, next_offset)
        
        box_width = 110
        canvas.create_rectangle(x - box_width / 2, y - box_height / 2, x + box_width / 2, y + box_height / 2, fill="#a0c4ff", outline="#4a4e69", width=2)
        canvas.create_text(x, y, text=display_text, fill="black", font=("Helvetica", 10), justify=tk.CENTER)