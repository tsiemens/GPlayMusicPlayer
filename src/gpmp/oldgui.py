import tkinter as tk
from tkinter import N, S, E, W

import ttk

class Application(tk.Frame):
   def __init__(self, master=None):
      super().__init__(master)
      self.master = master
      self.master.grid_rowconfigure(0, weight=1)
      self.master.grid_columnconfigure(0, weight=1)
      self.grid(row=0, column=0, sticky=N+S+W+E)
      self.create_widgets()

   def create_widgets(self):
      self.style = ttk.Style()
      self.style.theme_use("default")

      self.master.title("GPlayMusicPlayer (Unofficial)")
      self.grid_columnconfigure(0, weight=1)
      self.grid_columnconfigure(1, weight=0)
      self.grid_columnconfigure(2, weight=1)
      self.grid_rowconfigure(0, weight=1)

      sb = ttk.Scrollbar(self)
      #  sb.pack(side=tk.RIGHT, fill=tk.Y)
      sb.grid(row=0, column=1, sticky=tk.W+tk.N+tk.S+tk.E)

      playlist_list = tk.Listbox(self, yscrollcommand=sb.set)
      for x in range(20):
         playlist_list.insert(tk.END, str(x))
         if (x % 2) != 0:
            playlist_list.itemconfig(x, {'bg':'#eeeeee'})

      #  playlist_list.pack(side=tk.LEFT, fill=tk.BOTH)
      playlist_list.grid(row=0, column=0, sticky=N+S+W+E, pady=2)
      sb.config(command=playlist_list.yview)

      tree = ttk.Treeview(self)
      tree['columns'] = ("name", "nsongs")
      tree.column("name", width=100)
      tree.column("nsongs", width=30)
      tree.heading("#0", text="Line")
      tree.heading("name", text="Playlists")
      tree.heading("nsongs", text="#")

      tree.insert("", 0, text="Line1", values=("1A", "1b"))
      tree.insert("", "end", text="Line2", values=("2A", "2b"))
      #  tree.pack(side=tk.LEFT, fill=tk.BOTH)
      tree.grid(row=0, column=2, sticky=tk.W+tk.N+tk.S+tk.E, pady=2)

def buildUI():
   root = tk.Tk()
   app = Application(master=root)
   return app

if __name__ == '__main__':
   app = buildUI()
   app.mainloop()
