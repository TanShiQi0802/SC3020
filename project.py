# #ASSUMING INTERFACE IS ALR READY and the main function to launch UI is called launch_app (rename if not)
# from interface import launch_app

# if __name__ == "__main__":
#     launch_app()
    
    
import tkinter as tk
from interface import QueryAnnotator

root=tk.Tk()
app=QueryAnnotator(root)
root.mainloop()
    