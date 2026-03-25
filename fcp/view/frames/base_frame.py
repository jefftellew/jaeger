import tkinter as tk
from tkinter import ttk

class BaseFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.create_widgets()

    def create_widgets(self):
        # This method should be overridden by subclasses to create specific widgets
        pass