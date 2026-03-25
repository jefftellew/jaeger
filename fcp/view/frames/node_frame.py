import tkinter as tk
from tkinter import ttk

class NodeFrame(ttk.LabelFrame):
    def __init__(self, parent, node_title):
        self.node_title = node_title
        super().__init__(parent, text=self.node_title)

        self.battery_percent = tk.DoubleVar(value=0.0)
        self.temperature_c = tk.DoubleVar(value=0.0)
        self.error_code = tk.IntVar(value=0)
        self.status_flag = tk.StringVar(value='')

        self.create_widgets()

    def create_widgets(self):
        self.battery_percent_label = ttk.Label(self, text='Battery Percentage:')
        self.battery_percent_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')

        self.battery_percent_value_label = ttk.Label(self, textvariable=self.battery_percent)
        self.battery_percent_value_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        self.temperature_c_label = ttk.Label(self, text='Temperature (°C):')
        self.temperature_c_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')

        self.temperature_c_value_label = ttk.Label(self, textvariable=self.temperature_c)
        self.temperature_c_value_label.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        self.error_code_label = ttk.Label(self, text='Error Code:')
        self.error_code_label.grid(row=2, column=0, padx=5, pady=5, sticky='e')

        self.error_code_value_label = ttk.Label(self, textvariable=self.error_code)
        self.error_code_value_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        self.status_flag_label = ttk.Label(self, text='Status Flag:')
        self.status_flag_label.grid(row=3, column=0, padx=5, pady=5, sticky='e')

        self.status_flag_value_label = ttk.Label(self, textvariable=self.status_flag)
        self.status_flag_value_label.grid(row=3, column=1, padx=5, pady=5, sticky='w')

    def update_node_data(self, rat):
        self.battery_percent.set(rat.battery_percent)
        self.temperature_c.set(rat.temperature_c)
        self.error_code.set(rat.error_code)
        self.status_flag.set(rat.status_flag)