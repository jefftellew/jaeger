import tkinter as tk
from tkinter import ttk
from view.frames import base_frame
from view.frames.rat_frame import RatFrame

class ControlFrame(base_frame.BaseFrame):
    def __init__(self, parent, controller):
        # Initialize variables prior to calling the parent constructor because create_widgets() is called in the parent constructor
        self.lidar_enabled = True
        self.rf_enabled = True
        self.acoustic_enabled = True

        self.rat_frames = {}  # Dictionary to hold RATFrame instances keyed by rat_id

        super().__init__(parent)

        self.controller = controller
        self.create_widgets()

        self.columnconfigure(0, weight=1)

    #===================================================================

    def create_widgets(self):
        dnn_mode_label_frame = ttk.LabelFrame(self, text='Detection Modes')
        dnn_mode_label_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        dnn_mode_label_frame.columnconfigure(0, weight=1)
        dnn_mode_label_frame.columnconfigure(1, weight=1)
        dnn_mode_label_frame.columnconfigure(2, weight=1)
        dnn_mode_label_frame.rowconfigure(0, weight=1)

        self.lidar_label = ttk.Label(dnn_mode_label_frame, text='LiDAR Enabled', background='lightgreen', anchor=tk.CENTER, cursor='hand2')
        self.lidar_label.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        self.lidar_label.bind('<Button-1>', lambda _: self.update_lidar_checkbutton())

        self.rf_label = ttk.Label(dnn_mode_label_frame, text='RF Enabled', background='lightgreen', anchor=tk.CENTER, cursor='hand2')
        self.rf_label.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        self.rf_label.bind('<Button-1>', lambda _: self.update_rf_checkbutton())

        self.acoustic_label = ttk.Label(dnn_mode_label_frame, text='Acoustic Enabled', background='lightgreen', anchor=tk.CENTER, cursor='hand2')
        self.acoustic_label.grid(row=0, column=2, padx=5, pady=5, sticky='nsew')
        self.acoustic_label.bind('<Button-1>', lambda _: self.update_acoustic_checkbutton())

        self.rat_list_labelframe = ttk.LabelFrame(self, text='Rogue Aerial Targets')
        self.rat_list_labelframe.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')

    #===================================================================

    def update_lidar_checkbutton(self):
        self.lidar_enabled = not self.lidar_enabled
        self.lidar_label.configure(
            background='lightgreen' if self.lidar_enabled else 'red',
            text='LiDAR Enabled' if self.lidar_enabled else 'LiDAR Disabled'
        )
        self.controller.set_lidar_enabled(self.lidar_enabled)

    #===================================================================

    def update_rf_checkbutton(self):
        self.rf_enabled = not self.rf_enabled
        self.rf_label.configure(
            background='lightgreen' if self.rf_enabled else 'red',
            text='RF Enabled' if self.rf_enabled else 'RF Disabled'
        )
        self.controller.set_rf_enabled(self.rf_enabled)

    #===================================================================

    def update_acoustic_checkbutton(self):
        self.acoustic_enabled = not self.acoustic_enabled
        self.acoustic_label.configure(
            background='lightgreen' if self.acoustic_enabled else 'red',
            text='Acoustic Enabled' if self.acoustic_enabled else 'Acoustic Disabled'
        )
        self.controller.set_acoustic_enabled(self.acoustic_enabled)

    #===================================================================

    def update_rat(self, rat):
        print(f"Received update for RAT {rat.rat_id}: {rat}")
        if rat.rat_id not in self.rat_frames.keys():
            # Create a new RATFrame for this RAT
            rat_frame = RatFrame(self.rat_list_labelframe, rat.rat_id, self.controller)
            rat_frame.pack(side=tk.LEFT , padx=5, pady=5, fill=tk.X, expand=True)
            self.rat_frames[rat.rat_id] = rat_frame
        else:
            # Update the existing RATFrame with new data
            rat_frame = self.rat_frames[rat.rat_id]

        # Update the RATFrame's displayed values
        rat_frame.zone_value.set(rat.zone)
        rat_frame.az_value.set(rat.az_value)
        rat_frame.el_value.set(rat.el_value)
        rat_frame.range_value.set(rat.range_value)
        rat_frame.az_rate.set(rat.az_rate)
        rat_frame.el_rate.set(rat.el_rate)
        rat_frame.range_rate.set(rat.range_rate)
