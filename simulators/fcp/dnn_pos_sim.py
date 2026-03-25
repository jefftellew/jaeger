"""
dnn_pos_sim.py
Author: Seamus Daniello
Created: 2025-12-13
Description: Simulates the DNN's state vector output stream
Dependencies: Python3.x, dotenv, numpy, tkinter
Usage: python3 dnn_pos_sim.py
"""

import socket
import os
import json
from datetime import datetime, timezone
import time
import threading
import uuid

from dotenv import load_dotenv
import numpy as np
import tkinter as tk
from tkinter import messagebox

# Load root/.env variables (sim IP and Port numbers)
load_dotenv()

# Define the destination IP address and port number 
dnn_pos_sim_ip = os.getenv("DNN_POS_SIM_DESTINATION_IP")
dnn_pos_sim_port = int(os.getenv("DNN_POS_SIM_DESTINATION_PORT"))

# Creates an individual instance of a DNN data stream
def send_data(
    current_sending, 
    current_interval,
    current_dnn_pos_sim_port,
    current_precision_level,
    imposed_visibility_limit=100
    ):
    visibility_cycle = 0
    visibility_limit = imposed_visibility_limit



    # Define a json object to hold the state vector and send to the desired ip/port
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Define initial characteristics of the DNN output data stream
        rat_id = str(uuid.uuid4())
        az_value = np.random.uniform(0.0, 360.0)
        el_value = np.random.uniform(-90.0, 90.0)
        range_value = np.random.uniform(100.0, 10000.0)
        az_rate = np.random.uniform(-50.0, 50.0)
        el_rate = np.random.uniform(-50.0, 50.0)
        range_rate = np.random.uniform(-500.0, 500.0)

        # Send json object until manual interrupt (Control + C)
        while current_sending and visibility_cycle < visibility_limit:
            data = {
                'rat_id': rat_id,
                'current_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
                'values': {
                    'az_value': az_value,
                    'el_value': el_value,
                    'range_value': range_value
                },
                'rates': {
                    'az_rate': az_rate,
                    'el_rate': el_rate,
                    'range_rate': range_rate
                }
            }

            # Convert positioning values to 64-bit floating points if Precision type is 'double'
            if current_precision_level == 'double':
                data['values']['az_value'] = np.float64(data['values']['az_value'])
                data['values']['el_value'] = np.float64(data['values']['el_value'])
                data['values']['range_value'] = np.float64(data['values']['range_value'])

            # Create a json object for DNN positioning and rate fields
            json_data = json.dumps(data)

            # Send JSON object to the defined FCP serial port
            sock.sendto(json_data.encode(), (dnn_pos_sim_ip, int(current_dnn_pos_sim_port)))
            print(f"Sending to {dnn_pos_sim_ip}:{current_dnn_pos_sim_port}")
            print(f"Sent: {json_data}")

            # Increment the positioning values by a max of 1 digit
            az_value += np.random.uniform(-1.0, 1.0)
            az_value = az_value % 360
            if az_value < 0:
                az_value += 360
            el_value += np.random.uniform(-1.0, 1.0)
            range_value += np.random.uniform(-1.0, 1.0)

            # Increment the range values by a max of 1 digit
            az_rate += np.random.uniform(-1.0, 1.0)
            el_rate += np.random.uniform(-1.0, 1.0)
            range_rate += np.random.uniform(-1.0, 1.0)

            # Increment visibility cycle counter and sleep for defined interval
            visibility_cycle += 1
            time.sleep(current_interval)

# Launches DNN data stream to the defined FCP serial port
def start_sending(
    dnn_instance_is_sending,
    dnn_instance_interval_entry,
    dnn_instance_vl_entry,
    dnn_instance_port_entry,
    dnn_instance_precision_var,
    defined_visibility_limit=100
    ):
    global dnn_pos_sim_port
    sending = dnn_instance_is_sending
    if sending:
        messagebox.showinfo("Info", "Already sending data.")
        return
    try:
        interval = float(dnn_instance_interval_entry)
        vl_limit = float(dnn_instance_vl_entry)
        if dnn_instance_port_entry:
            dnn_pos_sim_port = float(dnn_instance_port_entry)
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid number for the interval.")
        return

    precision = dnn_instance_precision_var

    sending = True
    threading.Thread(target=send_data, args=(
        sending, 
        interval, 
        dnn_pos_sim_port, 
        precision,
        defined_visibility_limit,), daemon=True).start()

# Stops DNN data stream to the defined FCP serial port
def stop_sending():
    global sending
    sending = False

def create_dnn_instance_frame(
    title, 
    dnn_sim_instance_root, 
    instance_is_sending=False, 
    instance_interval=5, 
    instance_precision='double'
):
    # Create a frame with a white border
    border_frame = tk.Frame(dnn_sim_instance_root, bd=2, relief='solid', bg='white')
    border_frame.pack(side=tk.LEFT, padx=10, pady=10)

    # Add title label
    title_label = tk.Label(border_frame, text=title, font=('Impact', 14, 'bold'), bg='white', fg='black')
    title_label.pack(pady=5)

    # Defines a frame to hold the Interval, Visibility Limit, and Precision Input objects
    input_frame_1 = tk.Frame(border_frame, bg='#101820')
    input_frame_1.pack(pady=10)

    # Users to select the rate at which entries are sent to the FCP
    tk.Label(input_frame_1, text="Interval (seconds):", bg='#101820', fg='white', font=('Courier New', 12)).pack(pady=5)
    interval_entry = tk.Entry(input_frame_1, font=('Helvetica', 12), bd=2, relief='groove')
    interval_entry.pack(pady=5)
    interval_entry.insert(0, str(instance_interval))

    # Users can select the visibility limit
    tk.Label(input_frame_1, text="Visibility Limit", bg='#101820', fg='white', font=('Courier New', 12)).pack(pady=5)
    vl_entry = tk.Entry(input_frame_1, font=('Helvetica', 12), bd=2, relief='groove')
    vl_entry.pack(pady=5)
    vl_entry.insert(0, "100")

    # Enables users to select the output port on the FCP
    tk.Label(input_frame_1, text="Port", bg='#101820', fg='white', font=('Courier New', 12)).pack(pady=5)
    port_entry = tk.Entry(input_frame_1, font=('Helvetica', 12), bd=2, relief='groove')
    port_entry.pack(pady=5)
    port_entry.insert(0, "100")

    # Users can select the output variable type
    precision_var = tk.StringVar(value='float')
    tk.Label(input_frame_1, text="Choose Precision:", bg='#101820', fg='white', font=('Comic Sans MS', 12)).pack(pady=5)

    tk.Radiobutton(input_frame_1, text='Float', variable=precision_var, value='float').pack(anchor=tk.W)
    tk.Radiobutton(input_frame_1, text='Double', variable=precision_var, value='double').pack(anchor=tk.W)

    # Start and Stop buttons
    tk.Button(input_frame_1, text="Start Sending", command=lambda: start_sending(
        instance_is_sending,
        interval_entry.get(), 
        vl_entry.get(), 
        port_entry.get(), 
        precision_var.get(),
        int(vl_entry.get()))).pack(pady=10)
    tk.Button(input_frame_1, text="Stop Sending", command=stop_sending).pack(pady=10)

def launch_dnn_sim_loop():
    root = tk.Tk()
    root.title("DNN Positioning Sim")

    # Default sim dimensions
    root.geometry("650x600")
    root.configure(bg='#101820')

    # Defines a frame to hold the sim title
    title_frame = tk.Frame(root, bg='#101820')
    title_frame.pack(pady=20)
    title_label = tk.Label(title_frame, text="DNN SIM", font=('Impact', 24, 'bold'), bg='#101820', fg='white')
    title_label.pack()

    # Configure as many dnn instance frames as necessary with titles
    create_dnn_instance_frame("Rat 1", root)
    create_dnn_instance_frame("Rat 2", root)
    create_dnn_instance_frame("Rat 3", root)

    root.mainloop()

launch_dnn_sim_loop()