import tkinter as tk
from interface import QueryAnnotator

if __name__ == "__main__":
    root = tk.Tk()

    # Set dark title bar on Windows (optional, no-op on macOS/Linux)
    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass

    app = QueryAnnotator(root)
    root.mainloop()