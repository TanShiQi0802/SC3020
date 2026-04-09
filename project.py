import tkinter as tk
from interface import QueryAnnotator

if __name__ == "__main__":
    root = tk.Tk()
    app = QueryAnnotator(root)
    root.mainloop()