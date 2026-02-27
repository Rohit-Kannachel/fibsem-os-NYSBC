import napari

from fibsem.ui import stylesheets
from fibsem.ui.qtdesigner_files import SenseAIControlWidget as SenseAIControlWidgetUI
from PyQt5 import QtWidgets
from fibsem.microscope import FibsemMicroscope
import os
import numpy as np
import time
from senseai import SenseAI

class SenseAIControlWidget(SenseAIControlWidgetUI.Ui_Form, QtWidgets.QWidget):

    def __init__(
        self,
        microscope: FibsemMicroscope,
        parent: QtWidgets.QWidget,
    ):
        
        
        super().__init__(parent=parent)

        self.setupUi(self)

        if not hasattr(parent, "viewer") and not isinstance(parent.viewer, napari.Viewer):
            raise ValueError("Parent must have a 'viewer' attribute of type napari.Viewer")

        self.parent = parent
        self.microscope = microscope
        self.viewer = parent.viewer
        self.scan_gen_initialized = False
        self.senseAI: SenseAI = None

        self.setup_connections()

    
    def setup_connections(self):

        self.pushButton_init_scanGen.clicked.connect(self.initialize_scan_generator)
        self.pushButton_AcquireImage.clicked.connect(self.acquire_image)
        self.pushButton_Reconstruct.clicked.connect(self.reconstruct)

        # hide other controls until scan generator is initialized
        self.groupBox_ScanControl.setVisible(self.scan_gen_initialized)
        self.groupBox_Reconstruct_control.setVisible(self.scan_gen_initialized)



    def initialize_scan_generator(self):

        print("Initializing scan generator...")

        init = self.init_webcam()

        if not init:
            print(f"error initialising")
            return 

        self.scan_gen_initialized = True

        # show other controls
        self.groupBox_ScanControl.setVisible(self.scan_gen_initialized)
        self.groupBox_Reconstruct_control.setVisible(self.scan_gen_initialized)


    def init_webcam(self):

        SenseAI_version_path = r"C:\Program Files\SenseAI\SenseAI 2026.1.1"
        self.senseAI = SenseAI(os.path.join(SenseAI_version_path,"SenseAI.dll"))

        sg = self.senseAI.hw.add_scan_generator("WCScanGen", "QDMock", {
            "ScanSize": [
                1536,
                1024
            ],
            "DwellTime": 0.010,
            "Pattern": "Raster",
            "Sampling": 1.0,
            "ResetBuffer": True,
        })


        self.senseAI.hw.add_detector("WCDetector", "ScanGenerator", sg["Name"], {
            "Input": 0,
            "QDType": "qd_analogue"
        })


        try:
            self.senseAI.hw.init_scan_generator("WCScanGen")
        except Exception as e:
            print(f"Error Initialising: {e}")
            return False
        
        self.senseAI.hw.update_scan_generator("WCScanGen",
                           {
                               "Pattern":"Linehop",\
                               "Sampling":0.25,
                               "ResetBuffer":True
                           })
        
        time.sleep(3)

        return True




    
    def acquire_image(self):

        print("Acquiring image...")

        try:
            output3 = self.senseAI.hw.get_detector_image("WCDetector")
        except Exception as e:
            print(f"Capture failed: {e}")
            return
        img = output3[0]
        # mask1 = output3[1]

        # img = np.random.randint(0, 256, (1024, 1536), dtype=np.uint8)

        self.parent.image_widget.eb_layer.data = img


    def reconstruct(self):

        print("Reconstructing...")

    
