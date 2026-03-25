from dataclasses import dataclass, field
from model.rat_model import Rat
from model.analytics_db import FCPAnalyticsDB

@dataclass
class FCPModel:
    lidar_enabled: bool = True
    rf_enabled: bool = True
    acoustic_enabled: bool = True
    rats: dict[str, Rat] = field(default_factory=dict)
    analytics_db: FCPAnalyticsDB = field(default_factory=FCPAnalyticsDB)

    def set_lidar_enabled(self, enabled: bool):
        self.lidar_enabled = bool(enabled)

    def set_rf_enabled(self, enabled: bool):
        self.rf_enabled = bool(enabled)

    def set_acoustic_enabled(self, enabled: bool):
        self.acoustic_enabled = bool(enabled)

    def update_rat(self, rat: Rat):
        self.rats[rat.rat_id] = rat

    def remove_rat(self, rat_id: str):
        if rat_id in self.rats:
            del self.rats[rat_id]