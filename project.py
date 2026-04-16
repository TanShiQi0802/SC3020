import tkinter as tk
from interface import QueryAnnotator

if __name__ == "__main__":
    root = tk.Tk()

    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass

    app = QueryAnnotator(root)
    root.mainloop()