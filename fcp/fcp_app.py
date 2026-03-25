import tkinter as tk

from model.fcp_model import FCPModel
from view.fcp_view import FCPView
from controller.fcp_controller import FCPController
import view.theme as theme

class FCPApp(tk.Tk):
    def __init__(self):
        super().__init__()

        theme.apply(self)
        self.title('JAEGER Forward Command Post')
        self.geometry('1280x720+50+50')
        self.iconbitmap('./assets/jaeger_logo.ico')

        self._model = FCPModel()
        self._model.analytics_db.start_mission()

        # Log the initial enabled state of all three sensors at mission start
        db = self._model.analytics_db
        for sensor in ('lidar', 'rf', 'acoustic'):
            db.log_sensor_event(sensor, 'enabled')

        self.view = FCPView()
        self.view.pack(fill='both', expand=True)

        self.controller = FCPController(self._model, self.view)
        self.view.set_controller(self.controller)
        self.view.init_gui()

        # Do an initial analytics refresh so tables populate immediately
        self.view.analytics_frame.refresh()

        # Close the mission cleanly on window close
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    #===================================================================

    def _on_close(self):
        self._model.analytics_db.end_mission()
        self._model.analytics_db.close()
        self.destroy()

if __name__ == '__main__':
    app = FCPApp()
    app.mainloop()
