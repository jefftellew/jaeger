import socket
import threading
import json

from model.fcp_model import FCPModel
from model.rat_model import Rat
from model.node_model import Node
from view.fcp_view import FCPView

class FCPController:
    def __init__(self, model: FCPModel, view: FCPView):
        self.model = model
        self.view = view

        self.config = self.read_config('./cfg/config.ini')

        self.dnn_recv_ip = self.config['DNN.recv.connection']['ip']
        self.dnn_recv_port = self.config['DNN.recv.connection'].getint('port')

        self.dnn_send_ip = self.config['DNN.send.connection']['ip']
        self.dnn_send_port = self.config['DNN.send.connection'].getint('port')

        # Track which RATs have already received a 'detected' log so we only
        # emit it once per mission, and track last-known zone per RAT so we
        # only log zone_change when the zone actually changes.
        self._known_rats: set[str] = set()
        self._rat_zones: dict[str, int] = {}

        self._start_udp_listener()

    #===================================================================

    def read_config(self, config_file):
        import configparser
        config = configparser.ConfigParser()
        config.read(config_file)
        return config

    #===================================================================

    # Right now this only deals with the DNN side, not DNE
    def _start_udp_listener(self):
        print(f"Trying to bind UDP listener on {self.dnn_recv_ip}:{self.dnn_recv_port}")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.dnn_recv_ip, self.dnn_recv_port))
            print("UDP listener successfully bound")
        except Exception as e:
            print(f"Failed to bind UDP listener on {self.dnn_recv_ip}:{self.dnn_recv_port}: {e}")
            return

        def _listen_loop(s):
            while True:
                try:
                    data, addr = s.recvfrom(65535)
                    data_dict = json.loads(data.decode('utf-8'))

                    # Process the data and update the model
                    if data_dict.get('msg_type') == 'positional':
                        rat = Rat(data_dict)
                        self._handle_rat_analytics(rat, data_dict.get('current_time'))
                        self.model.update_rat(rat)
                        self.view.control_frame.update_rat(rat)

                    if data_dict.get('msg_type') == 'health':
                        node = Node(data_dict)
                        self.view.map_frame.update_dnn_node(node)

                except Exception as e:
                    import traceback
                    print(f"UDP listener error: {e}")
                    traceback.print_exc()
                    break

        t = threading.Thread(target=_listen_loop, args=(sock,), daemon=True)
        t.start()

    #===================================================================

    def _handle_rat_analytics(self, rat: Rat, msg_timestamp: str | None):
        """Log first-detection and zone-change events to the analytics DB."""
        db = self.model.analytics_db

        if rat.rat_id not in self._known_rats:
            self._known_rats.add(rat.rat_id)
            db.log_rat_event(
                rat.rat_id, 'detected',
                zone=rat.zone,
                az=rat.az_value, el=rat.el_value, range_m=rat.range_value,
                timestamp=msg_timestamp,
            )
            self._rat_zones[rat.rat_id] = rat.zone
        elif rat.zone != self._rat_zones.get(rat.rat_id):
            self._rat_zones[rat.rat_id] = rat.zone
            db.log_rat_event(
                rat.rat_id, 'zone_change',
                zone=rat.zone,
                az=rat.az_value, el=rat.el_value, range_m=rat.range_value,
                timestamp=msg_timestamp,
            )

    #===================================================================

    def set_lidar_enabled(self, enabled: bool):
        self.model.set_lidar_enabled(enabled)
        self.view.alert_frame.add_alert(f'LiDAR detection {"enabled" if enabled else "disabled"}')
        self.model.analytics_db.log_sensor_event('lidar', 'enabled' if enabled else 'disabled')
        # Send a command to DNN about the change
        self._send_detection_command('lidar', bool(enabled))

    #===================================================================

    def set_rf_enabled(self, enabled: bool):
        self.model.set_rf_enabled(enabled)
        self.view.alert_frame.add_alert(f'RF detection {"enabled" if enabled else "disabled"}')
        self.model.analytics_db.log_sensor_event('rf', 'enabled' if enabled else 'disabled')
        # Send a command to DNN about the change
        self._send_detection_command('rf', bool(enabled))

    #===================================================================

    def set_acoustic_enabled(self, enabled: bool):
        self.model.set_acoustic_enabled(enabled)
        self.view.alert_frame.add_alert(f'Acoustic detection {"enabled" if enabled else "disabled"}')
        self.model.analytics_db.log_sensor_event('acoustic', 'enabled' if enabled else 'disabled')
        # Send a command to DNN about the change
        self._send_detection_command('acoustic', bool(enabled))

    #===================================================================

    def _send_detection_command(self, mode: str, enabled: bool):
        """
        Send a UDP JSON command to the DNN command endpoint indicating a detection-mode change.
        """
        msg = {
            "msg_type": "command",
            "command": "set_detection_mode",
            "mode": mode,
            "enabled": enabled
        }
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = json.dumps(msg).encode('utf-8')
            sock.sendto(payload, (self.dnn_send_ip, self.dnn_send_port))
            sock.close()
        except Exception as e:
            print(f"Failed to send detection command for {mode}: {e}")

    #===================================================================

    def engage_rat(self, rat_id: str):
        """Engage a specific RAT"""
        print(f"Engaged RAT: {rat_id}")
        self.model.analytics_db.log_rat_event(rat_id, 'engage_commanded')
        # Add real engagement logic here
