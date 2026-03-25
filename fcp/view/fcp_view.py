from tkinter import ttk
from view.frames import video_frame, map_frame, alert_frame, control_frame
from view.frames.analytics_frame import AnalyticsFrame

class FCPView(ttk.Frame):
    def __init__(self):
        super().__init__()

    #===================================================================

    def init_gui(self):
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)

        self.video_frame = video_frame.VideoFrame(self)
        self.video_frame.grid(row=0, column=0, sticky='nsew')
        video_path = self.video_frame._get_assets_path() + "\\drone.mp4"
        self.video_frame.play_video(video_path)

        self.map_frame = map_frame.MapFrame(self)
        self.map_frame.grid(row=0, column=1, sticky='nsew')

        self.alert_frame = alert_frame.AlertFrame(self)
        self.alert_frame.grid(row=1, column=0, sticky='nsew', columnspan=2)

        self.control_frame = control_frame.ControlFrame(self, controller=self.controller)
        self.control_frame.grid(row=0, column=2, sticky='nsew')

        # Analytics frame — placed in col=3 for now so it lives on the main page.
        # To move it into a notebook tab later, replace these two lines with:
        #   notebook = ttk.Notebook(self)
        #   notebook.add(self.control_frame, text='Targets')
        #   notebook.add(self.analytics_frame, text='Analytics')
        #   notebook.grid(row=0, column=2, sticky='nsew', rowspan=2)
        self.columnconfigure(3, weight=1)
        self.analytics_frame = AnalyticsFrame(self, db=self.controller.model.analytics_db)
        self.analytics_frame.grid(row=1, column=2, sticky='nsew')

    #===================================================================

    def set_controller(self, controller):
        self.controller = controller
