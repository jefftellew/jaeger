from view.frames import base_frame
import tkinter as tk
from tkinter import ttk
from view.frames.node_frame import NodeFrame

class MapFrame(base_frame.BaseFrame):
    def create_widgets(self):
        self.dnn_frame = NodeFrame(self, node_title='DNN')
        self.dnn_frame.pack(expand=True, fill='both', padx=10, pady=10)

    def update_dnn_node(self, node):
        self.dnn_frame.update_node_data(node)