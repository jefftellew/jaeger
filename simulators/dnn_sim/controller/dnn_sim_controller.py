import socket
import threading
import json
import time

from model.dnn_sim_model import DNNSimModel
from view.dnn_sim_view import DNNSimView

from model.dnn_sim_rat_model import DNNSimRat as Rat
import random

class DNNSimController:
    def __init__(self, model: DNNSimModel, view: DNNSimView):
        self.model = model
        self.view = view

        self.config = self.read_config('./cfg/config.ini')

        self.fcp_send_ip = self.config['FCP.send.connection']['ip']
        self.fcp_send_port = self.config['FCP.send.connection'].getint('port')

        self.fcp_recv_ip = self.config['FCP.recv.connection']['ip']
        self.fcp_recv_port = self.config['FCP.recv.connection'].getint('port')

        self.health_freq = self.config['FCP.msg.freq'].getfloat('health_freq', fallback=1.0)  # default to 1 Hz if not specified
        self.pos_freq = self.config['FCP.msg.freq'].getfloat('pos_freq', fallback=0.1)  # default to 10 Hz if not specified

        # keep track of per‑RAT update threads and their stop events
        self._rat_threads: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._health_thread: tuple[threading.Thread, threading.Event] | None = None

        self._start_udp_listener()

    #===================================================================

    def read_config(self, config_file):
        import configparser
        config = configparser.ConfigParser()
        config.read(config_file)
        return config

    #===================================================================

    def _start_udp_listener(self):
        print(f"Trying to bind UDP listener on {self.fcp_recv_ip}:{self.fcp_recv_port}")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.fcp_recv_ip, self.fcp_recv_port))
            print("UDP listener successfully bound")
        except Exception as e:
            print(f"Failed to bind UDP listener on {self.fcp_recv_ip}:{self.fcp_recv_port}: {e}")
            return

        def _listen_loop(s):
            while True:
                try:
                    data, addr = s.recvfrom(65535)
                    data_dict = json.loads(data.decode('utf-8'))
                    self.view.recv_data_frame.add_alert(f"Received from {addr}: {data_dict}")

                    if data_dict.get('msg_type') == 'command':
                        self.handle_command(data_dict)
                except Exception as e:
                    import traceback
                    print(f"UDP listener error: {e}")
                    traceback.print_exc()
                    break

        t = threading.Thread(target=_listen_loop, args=(sock,), daemon=True)
        t.start()

    #===================================================================

    def handle_command(self, command_dict):
        if command_dict.get('command') == 'set_detection_mode':
            mode = command_dict.get('mode')

            if mode == 'lidar':
                self.model.set_lidar_enabled(command_dict.get('enabled'))
                self.view.mode_frame.set_lidar_enabled(command_dict.get('enabled'))
            elif mode == 'rf':
                self.model.set_rf_enabled(command_dict.get('enabled'))
                self.view.mode_frame.set_rf_enabled(command_dict.get('enabled'))
            elif mode == 'acoustic':
                self.model.set_acoustic_enabled(command_dict.get('enabled'))
                self.view.mode_frame.set_acoustic_enabled(command_dict.get('enabled'))

    #===================================================================

    def generate_random_rat_data(self, rat_id):
        zone = random.randint(1, 3)
        az_value = round(random.uniform(0, 90), 6)
        el_value = round(random.uniform(0, 90), 6)
        range_value = round(random.uniform(0, 30 * zone), 6)
        az_rate = round(random.uniform(-5, 5), 6)
        el_rate = round(random.uniform(-5, 5), 6)
        range_rate = round(random.uniform(-50, 50), 6)

        return Rat(
            rat_id=rat_id,
            zone=zone,
            az_value=az_value,
            el_value=el_value,
            range_value=range_value,
            az_rate=az_rate,
            el_rate=el_rate,
            range_rate=range_rate
        )

    #===================================================================

    def _rat_update_loop(self, rat_id: str, stop_event: threading.Event):
        """
        Background loop that continuously:
        • creates fresh RAT data,
        • updates the model,
        • refreshes the view,
        • sends the positional message over UDP.
        """
        # reuse a single UDP socket for the whole life of the thread
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while not stop_event.is_set():
            try:
                rat = self.generate_random_rat_data(rat_id)
                self.model.update_rat(rat)

                for frame in self.view.control_frame.rat_frames:
                    if frame.rat_id == rat_id:
                        frame.update_rat_data(rat)
                        break

                message = rat.to_message().encode('utf-8')
                sock.sendto(message, (self.fcp_send_ip, self.fcp_send_port))
                self.view.sent_data_frame.add_alert(f"Sent: {message.decode('utf-8')}")
                time.sleep(1.0 / self.pos_freq)
            except Exception as e:
                import traceback
                print(f"Error in RAT update thread for {rat_id}: {e}")
                traceback.print_exc()
                # Continue looping unless stop requested
        sock.close()
        print(f"RAT update thread for {rat_id} terminated")

    #===================================================================

    def start_rat_sim(self, rat_id):
        """
        Starts (or restarts) the simulation thread for a given RAT.
        If a thread already exists for this RAT, it is stopped first.
        """
        print(f"Starting simulation for RAT {rat_id}")

        # Stop existing thread if present
        if rat_id in self._rat_threads:
            self.stop_rat_sim(rat_id)

        # Initialise the thread & stop flag
        stop_event = threading.Event()
        t = threading.Thread(target=self._rat_update_loop,
                             args=(rat_id, stop_event),
                             daemon=True)
        self._rat_threads[rat_id] = (t, stop_event)
        t.start()

    #===================================================================

    def stop_rat_sim(self, rat_id):
        """
        Signals the associated update thread to stop and waits for it to finish.
        Also removes the RAT from the model.
        """
        print(f"Stopping simulation for RAT {rat_id}")

        thread_info = self._rat_threads.pop(rat_id, None)
        if thread_info:
            thread, stop_event = thread_info
            stop_event.set()
            thread.join(timeout=2.0)   # give it a moment to finish cleanly
        else:
            print(f"No active simulation thread found for RAT {rat_id}")

        self.model.remove_rat(rat_id)

    #===================================================================

    def start_health_sim(self):
        if self._health_thread:
            self.stop_health_sim()   # restart if already running

        stop_evt = threading.Event()
        t = threading.Thread(target=self._health_update_loop,
                             args=(stop_evt,),
                             daemon=True)
        self._health_thread = (t, stop_evt)
        t.start()
        print("Health simulation started")

    #===================================================================

    def stop_health_sim(self):
        if not self._health_thread:
            print("Health simulation not running")
            return
        thread, stop_evt = self._health_thread
        stop_evt.set()
        thread.join(timeout=2.0)
        self._health_thread = None
        print("Health simulation stopped")

    #===================================================================

    def _health_update_loop(self, stop_event: threading.Event):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # start with the model’s current values
        battery = self.model.battery_percentage
        temperature = self.model.temperature_c
        error_code = self.model.error_code
        status_flag = self.model.status_flag

        while not stop_event.is_set():
            try:
                battery = round(max(0.0, battery - random.uniform(0.05, 0.2)), 2)
                temperature += random.uniform(-0.2, 0.2)
                temperature = round(temperature, 2)

                # Occasionally inject an error
                if random.random() < 0.02:
                    error_code = random.randint(1, 999)
                    status_flag = random.choice(DNNSimModel.STATUS_FLAGS[1:])
                else:
                    error_code = 0
                    status_flag = DNNSimModel.STATUS_FLAGS[0]

                self.model.update_health(battery, temperature, error_code, status_flag)

                msg = json.dumps(self.model.to_health_message()).encode('utf-8')
                sock.sendto(msg, (self.fcp_send_ip, self.fcp_send_port))

                if self.view and hasattr(self.view, 'control_frame'):
                    health_frame = self.view.control_frame.health_frame
                    # schedule UI update safely
                    self.view.after(
                        0,
                        lambda: health_frame.update_health(battery, temperature, error_code, status_flag)
                    )

                time.sleep(1.0 / self.health_freq)
            except Exception as e:
                import traceback
                print(f"Error in health simulation loop: {e}")
                traceback.print_exc()
        sock.close()
        print("Health simulation thread terminated")
