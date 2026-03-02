import napari

from fibsem.ui import stylesheets
from fibsem.ui.qtdesigner_files import SenseAIControlWidget as SenseAIControlWidgetUI
from PyQt5 import QtWidgets
from fibsem.microscope import FibsemMicroscope
from fibsem.SenseAI_SG import SenseAI_ModuleControl, SenseAI_Config
from fibsem.structures import FibsemImage, FibsemImageMetadata, ImageSettings
import os
import numpy as np
import time
import logging
from fibsem.config import DEFAULT_SENSEAI_DLL, DEFAULT_SENSEAI_CONFIG




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
        self.senseAI: SenseAI_ModuleControl = None
        self.senseAI_config: SenseAI_Config = None

        self.senseAI_img: np.ndarray = None
        self.senseAI_mask: np.ndarray = None
        self.senseAI_recon: np.ndarray = None

        self.dll_path: str = None
        self.config_path: str = None

        self.setup_connections()

    
    def setup_connections(self):

        self.pushButton_init_scanGen.clicked.connect(self.initialize_scan_generator)
        self.pushButton_AcquireImage.clicked.connect(self.acquire_image)
        self.pushButton_Reconstruct.clicked.connect(self.reconstruct)

        self.toolButton_dll_load.clicked.connect(self.load_dll_path)
        self.toolButton_config_load.clicked.connect(self.load_config_path)

        # hide other controls until scan generator is initialized
        self.groupBox_ScanControl.setVisible(self.scan_gen_initialized)
        self.groupBox_Reconstruct_control.setVisible(self.scan_gen_initialized)


        ## add Scan options to scan type drop down

        scanTypes = ["Raster", "Linehop", "Random", "Raster-Random","Lane-Constrained Random","Interleaved Linehop"]
        self.comboBox_ScanPattern.addItems(scanTypes)

        ## Load Defaults

        self.lineEdit_dllPath.setText(DEFAULT_SENSEAI_DLL)
        self.lineEdit_ConfigPath.setText(DEFAULT_SENSEAI_CONFIG)



    def load_dll_path(self):
        """
        Open a file dialog to select the SenseAI DLL path and store it in self.dll_path.
        """

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select SenseAI DLL", "", "DLL Files (*.dll)")

        if file_path:
            self.dll_path = file_path
            self.lineEdit_dllPath.setText(self.dll_path)
            logging.info(f"Selected SenseAI DLL path: {self.dll_path}")
        else:
            logging.warning("No DLL path selected.")
            self.lineEdit_dllPath.setText("")


    def load_config_path(self):
        """
        Open a file dialog to select the SenseAI config path and store it in self.config_path.
        """

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select SenseAI JSON Workspace", "", "Config Files (*.json)")

        if file_path:
            self.config_path = file_path
            self.lineEdit_ConfigPath.setText(self.config_path)
            logging.info(f"Selected SenseAI config path: {self.config_path}")
        else:
            logging.warning("No config path selected.")
            self.lineEdit_ConfigPath.setText("")

    def initialize_scan_generator(self):

        ### 
        self.dll_path = self.lineEdit_dllPath.text()
        self.config_path = self.lineEdit_ConfigPath.text()


        try:
            logging.info("Loading SenseAI Module Control...")
            self.senseAI = SenseAI_ModuleControl(dll_path=self.dll_path)
            self.senseAI_config = self.senseAI.config


            logging.info("SenseAI Module Control loaded successfully")
            self.scan_gen_initialized = True
        except Exception as e:
            logging.error(f"Error loading SenseAI Module Control: {e}")
            napari.utils.notifications.show_error(f"Error loading SenseAI Module Control: {e}")
            return
        
        try:
            logging.info("Loading SenseAI config...")
            self.senseAI_config.load_config_information(self.config_path)
            logging.info("SenseAI config loaded successfully")
        except Exception as e:
            logging.error(f"Error loading SenseAI config: {e}")
            napari.utils.notifications.show_error(f"Error loading SenseAI config: {e}")
            return
        

        ## initialise the scan generator

        try:
            self.senseAI.init_scan_generator()
            logging.info("Scan Generator Initialised")
        except Exception as e:
            logging.error(f"Error initialising scan generator: {e}")
            napari.utils.notifications.show_error(f"Error initialising scan generator: {e}")
            return

        ## if module is loaded correctly, the electron beam scan needs to be set
        ## to external scan so the scan gen can control the scanning

        self.microscope._set(key="ElectronBeam_scan",value="external")

        self.update_ui()


        # show other controls
        self.groupBox_ScanControl.setVisible(self.scan_gen_initialized)
        self.groupBox_Reconstruct_control.setVisible(self.scan_gen_initialized)
        



    def update_ui(self):
        """Update the UI elements with the loaded SenseAI configuration."""

        self.spinBox_ScanSizeX.setValue(self.senseAI_config.scanGen_config["ScanSize"][0])
        self.spinBox_ScanSizeY.setValue(self.senseAI_config.scanGen_config["ScanSize"][1])

        self.doubleSpinBox_DwellTime.setValue(self.senseAI_config.scanGen_config["DwellTime"])

        self.spinBox_SamplingRate.setValue(int(self.senseAI_config.scanGen_config["Sampling"]*100))

        self.comboBox_ScanPattern.setCurrentText(self.senseAI_config.scanGen_config["Pattern"])

        self.checkBox_resetBuffer.setChecked(self.senseAI_config.scanGen_config["ResetBuffer"])



    def update_scanGen_config(self):
        """Update the SenseAI configuration with the values from the UI elements."""

        self.senseAI_config.scanGen_config["ScanSize"] = [self.spinBox_ScanSizeX.value(), self.spinBox_ScanSizeY.value()]

        self.senseAI_config.scanGen_config["DwellTime"] = self.doubleSpinBox_DwellTime.value()

        self.senseAI_config.scanGen_config["Sampling"] = self.spinBox_SamplingRate.value()/100

        self.senseAI_config.scanGen_config["Pattern"] = self.comboBox_ScanPattern.currentText()

        self.senseAI_config.scanGen_config["ResetBuffer"] = self.checkBox_resetBuffer.isChecked()



    def update_scan_generator(self):

        """Update the SenseAI scan generator with the current configuration."""

        self.update_scanGen_config()

        try:
            self.senseAI.update_ScanGenerator(self.senseAI_config.scanGen_config)
            logging.info("SenseAI scan generator updated successfully")
        except Exception as e:
            logging.error(f"Error updating SenseAI scan generator: {e}")
            napari.utils.notifications.show_error(f"Error updating SenseAI scan generator: {e}")
            return

    def acquire_image(self):

        self.update_scan_generator()

        print("Acquiring image...")

        try:
            output = self.senseAI.get_detector_image()
            

        except Exception as e:
            
            return
        self.senseAI_img = output[0]
        self.senseAI_mask = output[1]

        self._update_eb_image_viewer(self.senseAI_img)
        


    def reconstruct(self):



        try:
            recon = self.senseAI.quick_recon_single(self.senseAI_img,self.senseAI_mask)
        except Exception as e:
            logging.info(f"error performing reconstruction {e}")
            return

        self._update_eb_image_viewer(recon)



    def _update_eb_image_viewer(self,image: np.ndarray) -> None:

        # normalise and make image 8 bit

        normalised_image = np.interp(image, (image.min(), image.max()), (0, 255)).astype(np.uint8)

        fb_image = FibsemImage(normalised_image)

        self.parent.image_widget.eb_image = fb_image
        self.parent.image_widget._on_acquire_nofilter(fb_image)

    
