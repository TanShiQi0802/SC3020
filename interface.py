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
        self.annotation_output = tk.Text(left_frame, height=12, wrap=tk.WORD, state=tk.DISABLED, font=("Helvetica", 12))
        self.annotation_output.pack(fill=tk.BOTH, expand=True)

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
        self.annotation_output.config(state=tk.NORMAL)
        self.annotation_output.delete("1.0", tk.END)
        self.annotation_output.insert(tk.END, dummy_result)
        self.annotation_output.config(state=tk.DISABLED)

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


if __name__ == "__main__":
    root = tk.Tk()
    app = QueryAnnotator(root)
    root.mainloop()





        



                                   
   