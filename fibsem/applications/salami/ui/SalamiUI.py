import sys


try:
    sys.modules.pop("PySide6.QtCore")
except Exception:
    pass

import logging
import os
import subprocess
import threading
from copy import deepcopy
from typing import List, Optional
import napari
import napari.utils.notifications
import fibsem
from fibsem import utils
from fibsem.microscope import FibsemMicroscope
from fibsem.structures import (
    BeamType,
    FibsemImage,
    FibsemRectangle,
    FibsemStagePosition,
    MicroscopeSettings,
)
from fibsem.ui import (
    DETECTION_AVAILABLE,
    FibsemImageSettingsWidget,
    FibsemMovementWidget,
    FibsemSystemSetupWidget,
    SenseAIControlWidget,
    stylesheets,
)
from fibsem.ui import utils as fui
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QDialog, QVBoxLayout, QDialogButtonBox, QMessageBox, QAction


from fibsem.ui.widgets.milling_task_config_widget import MillingTaskConfigWidget

from fibsem.applications.salami.ui.qtdesigner_files import SalamiUI as SalamiMainUI

class SalamiUI(SalamiMainUI.Ui_MainWindow, QMainWindow):
    def __init__(self, viewer: napari.Viewer, parent_ui: Optional['QWidget'] = None):
        super().__init__()
        self.setupUi(self)
        self.viewer = viewer

        # # Initialize UI components
        self.microscope: Optional[FibsemMicroscope] = None
        self.settings: Optional[MicroscopeSettings] = None

        self.system_widget = FibsemSystemSetupWidget(parent=self)
        self.image_widget: Optional[FibsemImageSettingsWidget] = None
        self.movement_widget: Optional[FibsemMovementWidget] = None
        self.milling_task_config_widget: Optional[MillingTaskConfigWidget] = None
        self.SenseAI_widget: Optional[SenseAIControlWidget] = None

        self.tabWidget.insertTab(0, self.system_widget, "Connection")

        self.setup_connections()
    
    def setup_connections(self):
        
        self.system_widget.connected_signal.connect(self.connect_to_microscope)
        self.system_widget.disconnected_signal.connect(self.disconnect_from_microscope)

        self.update_ui()

    def connect_to_microscope(self):
        self.microscope = self.system_widget.microscope
        self.settings = self.system_widget.settings

        self.update_microscope_ui()
        self.update_ui()

    def disconnect_from_microscope(self):
        self.microscope = None
        self.settings = None
        self.update_microscope_ui()
        self.update_ui()

    def update_microscope_ui(self):
        """Update the ui based on the current state of the microscope."""

        if self.microscope is not None:
            # reusable components
            self.image_widget = FibsemImageSettingsWidget(
                microscope=self.microscope,
                image_settings=self.settings.image, # type: ignore
                parent=self,
            )
            self.movement_widget = FibsemMovementWidget(
                microscope=self.microscope,
                parent=self,
            )
            self.SenseAI_widget = SenseAIControlWidget(
                microscope=self.microscope,
                parent=self,
            )

            # add widgets to tabs
            self.tabWidget.addTab(self.image_widget, "Image")
            self.tabWidget.addTab(self.movement_widget, "Movement")
            # TODO: replace this with MillingTaskWidget to support multi-task configuration
            self.milling_task_config_widget = MillingTaskConfigWidget(microscope=self.microscope, parent=self)
            self.tabWidget.addTab(self.milling_task_config_widget, "Milling")
            self.tabWidget.addTab(self.SenseAI_widget, "SenseAI")



            # self.image_widget.acquisition_progress_signal.connect(self.handle_acquisition_update)


        else:
            if self.image_widget is None:
                return

            # remove tabs
            if self.milling_task_config_widget is not None:
                self.tabWidget.removeTab(self.tabWidget.indexOf(self.milling_task_config_widget))
                self.milling_task_config_widget.deleteLater()
                self.milling_task_config_widget = None
            if self.movement_widget is not None:
                self.tabWidget.removeTab(self.tabWidget.indexOf(self.movement_widget))
                self.movement_widget.deleteLater()
                self.movement_widget = None
            if self.image_widget is not None:
                self.tabWidget.removeTab(self.tabWidget.indexOf(self.image_widget))
                self.image_widget.clear_viewer()
                # self.image_widget.acquisition_progress_signal.disconnect(self.handle_acquisition_update)
                self.image_widget.deleteLater()
                self.image_widget = None


    def update_ui(self):
        """Update the ui based on the current state of the application."""

        # state flags

        is_microscope_connected = bool(self.microscope is not None)


        # force order: connect -> experiment -> protocol
        self.tabWidget.setTabVisible(self.tabWidget.indexOf(self.tab), is_microscope_connected)
        




def main():
    salami_ui = SalamiUI(napari.Viewer())
    salami_ui.viewer.window.add_dock_widget(
        widget=salami_ui, 
        area="right",
        add_vertical_stretch=True,
        name="SALAMI")
    napari.run()

if __name__ == "__main__":
    main()