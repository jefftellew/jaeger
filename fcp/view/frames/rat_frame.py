import tkinter as tk
from tkinter import ttk

class RatFrame(ttk.LabelFrame):
    def __init__(self, parent, rat_id, controller):
        self.rat_id = rat_id
        self.controller = controller
        super().__init__(parent, text=f'RAT {self.rat_id}')

        self.zone_value = tk.IntVar(value=0)
        # Track if we're in zone 3 to enable/disable the engage button
        self.zone_value.trace_add('write', self.on_zone_change)

        self.az_value = tk.DoubleVar(value=0.0)
        self.el_value = tk.DoubleVar(value=0.0)
        self.range_value = tk.DoubleVar(value=0.0)
        self.az_rate = tk.DoubleVar(value=0.0)
        self.el_rate = tk.DoubleVar(value=0.0)
        self.range_rate = tk.DoubleVar(value=0.0)

        self.create_widgets()

    #===================================================================

    def create_widgets(self):
        # Zone
        self.zone_label = ttk.Label(self, text='Zone:')
        self.zone_label.grid(row=0, column=0, padx=5, pady=5, sticky='e')

        self.zone_value_label = ttk.Label(self, textvariable=self.zone_value)
        self.zone_value_label.grid(row=0, column=1, padx=5, pady=5, sticky='w')

        # Azimuth value
        self.az_label = ttk.Label(self, text='Azimuth:')
        self.az_label.grid(row=1, column=0, padx=5, pady=5, sticky='e')

        self.az_value_label = ttk.Label(self, textvariable=self.az_value)
        self.az_value_label.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        # Elevation value
        self.el_label = ttk.Label(self, text='Elevation:')
        self.el_label.grid(row=2, column=0, padx=5, pady=5, sticky='e')

        self.el_value_label = ttk.Label(self, textvariable=self.el_value)
        self.el_value_label.grid(row=2, column=1, padx=5, pady=5, sticky='w')

        # Range value
        self.range_label = ttk.Label(self, text='Range:')
        self.range_label.grid(row=3, column=0, padx=5, pady=5, sticky='e')

        self.range_value_label = ttk.Label(self, textvariable=self.range_value)
        self.range_value_label.grid(row=3, column=1, padx=5, pady=5, sticky='w')

        # Azimuth Rate
        self.az_rate_label = ttk.Label(self, text='Azimuth Rate:')
        self.az_rate_label.grid(row=4, column=0, padx=5, pady=5, sticky='e')

        self.az_rate_value_label = ttk.Label(self, textvariable=self.az_rate)
        self.az_rate_value_label.grid(row=4, column=1, padx=5, pady=5, sticky='w')

        # Elevation Rate
        self.el_rate_label = ttk.Label(self, text='Elevation Rate:')
        self.el_rate_label.grid(row=5, column=0, padx=5, pady=5, sticky='e')

        self.el_rate_value_label = ttk.Label(self, textvariable=self.el_rate)
        self.el_rate_value_label.grid(row=5, column=1, padx=5, pady=5, sticky='w')

        # Range Rate
        self.range_rate_label = ttk.Label(self, text='Range Rate:')
        self.range_rate_label.grid(row=6, column=0, padx=5, pady=5, sticky='e')

        self.range_rate_value_label = ttk.Label(self, textvariable=self.range_rate)
        self.range_rate_value_label.grid(row=6, column=1, padx=5, pady=5, sticky='w')

        # Engage Button
        self.engage_button = ttk.Button(self, text='Engage', command=self.engage_rat, state='disabled')
        self.engage_button.grid(row=7, column=0, columnspan=2, pady=10)

    #===================================================================

    def on_zone_change(self, *args):
        """Callback that runs when the zone value changes, updates the engage button state"""
        current_zone = self.zone_value.get()
        if current_zone == 3:
            self.engage_button.config(state='normal')
        else:
            self.engage_button.config(state='disabled')

    #===================================================================

    def engage_rat(self):
        """Handle engaging the RAT"""
        # Call the controller's method to engage the RAT
        if hasattr(self.controller, 'engage_rat') and self.controller.engage_rat is not None:
            self.controller.engage_rat(self.rat_id)
        else:
            print(f"Attempting to engage RAT {self.rat_id}")

    #===================================================================

    def update_rat_data(self, rat):
        """Update the displayed data for this RAT based on a new RAT object"""
        self.zone_value.set(rat.zone)
        self.az_value.set(rat.az_value)
        self.el_value.set(rat.el_value)
        self.range_value.set(rat.range_value)
        self.az_rate.set(rat.az_rate)
        self.el_rate.set(rat.el_rate)
        self.range_rate.set(rat.range_rate)