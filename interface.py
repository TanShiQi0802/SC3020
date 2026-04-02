import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

class QueryAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("Query Annotator")
        self.root.geometry("1000x700")

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        self.create_widgets()

    def create_widgets(self):
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top_frame, text="Select Database Schema", font=("Helvetica", 16, "bold")).pack(side=tk.LEFT, padx=(0,10))
        self.schema_var = tk.StringVar(value="TPC-H")
        schema_combo = ttk.Combobox(top_frame, textvariable=self.schema_var, state="readonly", width=15)
        schema_combo['values'] = ["TPC-H", "IMDB"]
        schema_combo.pack(side=tk.LEFT)

        main_paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Input SQL Query:", font=("Helvetica", 14, "bold")).pack(anchor=tk.W, pady=(0, 5))
        self.query_input = tk.Text(left_frame, height=10, wrap=tk.WORD, font=("Helvetica", 12))
        self.query_input.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.execute_btn = ttk.Button(btn_frame, text="Execute", command=self.run_algorithm)
        self.execute_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.visualise_btn = ttk.Button(btn_frame, text="Visualise", command=self.visualise_qep)
        self.visualise_btn.pack(side=tk.LEFT)

        ttk.Label(left_frame, text="Annotated Query Output:", font=("Helvetica", 14, "bold")).pack(anchor=tk.W, pady=(10, 5))
        self.annotation_canvas = tk.Canvas(left_frame, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.annotation_canvas.pack(fill=tk.BOTH, expand=True)
        self.annotation_canvas.create_text(20, 20, text="Run the algorithm to see visual annotations here.", fill="gray", font=("Helvetica", 12, "italic"), anchor=tk.W)

        right_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(right_frame, weight=1)

        ttk.Label(right_frame, text="QEP Visualisation:", font=("Helvetica", 14, "bold")).pack(anchor=tk.W, pady=(0, 5))

        self.qep_canvas = tk.Canvas(right_frame, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.qep_canvas.pack(fill=tk.BOTH, expand=True)
        self.qep_canvas.create_text(250, 300, text="QEP Visualisation will appear here.", fill="gray", font=("Helvetica", 12, "italic"))


    def run_algorithm(self):
        query_text = self.query_input.get("1.0", tk.END).strip()
        schema = self.schema_var.get()

        if not query_text:
            messagebox.showwarning("Input Error", "Please enter a SQL query.")
            return
        
        dummy_result = f"-- Schema used: {schema}\n--Annotations mapped to query components...\n\n{query_text}\n\n/* -> Tables are read using sequential scan because ... */"
        self.draw_visual_annotations(query_text)

    def visualise_qep(self):
        self.qep_canvas.delete("all")
        mock_qep_json = {
            "Node Type": "Hash Join",
            "Plans": [
                {
                    "Node Type": "Seq Scan", 
                    "Relation Name": "customer"
                },
                {
                    "Node Type": "Hash", 
                    "Plans": [
                        {
                            "Node Type": "Seq Scan", 
                            "Relation Name": "orders"
                        }
                    ]
                }
            ]
        }
        canvas_wdith = self.qep_canvas.winfo_width()
        if canvas_wdith <=1:
            canvas_wdith = 500
        start_x = canvas_wdith / 2
        start_y = 50
        initial_x_offset = 120
        self.draw_qep_node(self.qep_canvas, mock_qep_json, start_x, start_y, initial_x_offset)

    def draw_qep_node(self, canvas, node, x, y, x_offset):
        node_type = node.get("Node Type", "Unknown")
        relation_name = node.get("Relation Name", "")

        if relation_name:
            display_text = f"{node_type}\n{relation_name}"
            box_height = 45
        else:
            display_text = node_type
            box_height = 30

        
        children = node.get("Plans", [])
        child_y = y + 80

        if len(children) == 1:
            child_x_positions = [x]
        elif len(children) == 2:
            child_x_positions = [x - x_offset, x + x_offset]
        else:
            child_x_positions = [x - x_offset + (i * 80) for i in range(len(children))]
        
        for i, child in enumerate(children):
            child_x = child_x_positions[i]
            canvas.create_line(x, y, child_x, child_y, fill="#cccccc", width=2)
            self.draw_qep_node(canvas, child, child_x, child_y, x_offset / 1.5)
        
        box_width = 110
        canvas.create_rectangle(x - box_width / 2, y - box_height / 2, x + box_width / 2, y + box_height / 2, fill="#a0c4ff", outline="#4a4e69", width=2)
        canvas.create_text(x, y, text=display_text, fill="black", font=("Helvetica", 12, "bold"), justify=tk.CENTER)    

    def draw_visual_annotations(self, query_text):
        self.annotation_canvas.delete("all")
        lines = query_text.split("\n")
        sql_start_x = 20
        sql_start_y = 30
        line_height = 80

        line_y_coords = {}

        for i, line in enumerate(lines):
            y_pos = sql_start_y + (i * line_height)
            self.annotation_canvas.create_text(sql_start_x, y_pos, text=line, anchor=tk.W, font=("Helvetica", 12))
            line_y_coords[i] = y_pos
        
        annotations = [
            {
                "target_line_idx": 0, 
                "text": "Tables are read using sequential scan.\nThis is because no index is created on the tables."
            },
            {
                "target_line_idx": 1, 
                "text": "This join is implemented using hash join operator as NL joins and merge join increase the estimated cost by at least 10 and 7 times, respectively."
            }
        ]

        box_x_center = 500
        box_width = 340

        for i, anno in enumerate(annotations):
            target_line = anno["target_line_idx"]
            if target_line in line_y_coords:
                box_y_center = line_y_coords[target_line]
            else:
                box_y_center = sql_start_y + (i * 90)
            box_height = 65 if i == 0 else 85

            self.annotation_canvas.create_rectangle(box_x_center - box_width / 2, box_y_center - box_height / 2, box_x_center + box_width / 2, box_y_center + box_height / 2, fill="#a0c4ff", outline="#4a4e69", width=2)
            self.annotation_canvas.create_text(box_x_center, box_y_center, text=anno["text"], anchor=tk.CENTER, font=("Helvetica", 12), justify=tk.CENTER, width=box_width - 20)

            if target_line in line_y_coords:
                start_arrow_x = box_x_center - box_width / 2 - 5
                start_arrow_y = box_y_center
                end_arrow_x = sql_start_x + 200
                end_arrow_y = line_y_coords[target_line]
                self.annotation_canvas.create_line(start_arrow_x, start_arrow_y, end_arrow_x, end_arrow_y, arrow=tk.LAST, fill="#4a4e69", width=2)

if __name__ == "__main__":
    root = tk.Tk()
    app = QueryAnnotator(root)
    root.mainloop()





        



                                   
   