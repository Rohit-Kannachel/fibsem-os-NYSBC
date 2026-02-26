import napari

from fibsem.ui import stylesheets
from fibsem.ui.qtdesigner_files import SenseAIControlWidget as SenseAIControlWidgetUI
from PyQt5 import QtWidgets
from fibsem.microscope import FibsemMicroscope

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
        self.scan_gen_initialized = True

        # show other controls
        self.groupBox_ScanControl.setVisible(self.scan_gen_initialized)
        self.groupBox_Reconstruct_control.setVisible(self.scan_gen_initialized)

    
    def acquire_image(self):

        print("Acquiring image...")

    def reconstruct(self):

        print("Reconstructing...")

    
