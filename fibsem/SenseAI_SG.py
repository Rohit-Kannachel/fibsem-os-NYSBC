import json
import os
import numpy as np
import time
import logging


# from senseai import SenseAI


### scan generator and external detector imaging code here
### also code for senseAI processing and reconstruction here


class SenseAI_Config():
    def __init__(self,
        senseAI_WorkspaceJSON_path:str = None):

        self.senseAI_WorkspaceJSON_path = senseAI_WorkspaceJSON_path
        self.scanGen_config: dict = None
        self.detector_config: dict = None
        self.scanGen_initialised: bool = False

        self.load_config_information(self.senseAI_WorkspaceJSON_path)


    def load_config_information(self, json_path: str = None):

        ## load the config from the json into python dicts
        if json_path is None:

            logging.info("No config path provided, using default values")
            
            self.scanGen_config = {
                "ScanSize": [
                    640,
                    480
                ],
                "DwellTime": 0.010,
                "Pattern": "Linehop",
                "Sampling": 0.3,
                "ResetBuffer": True,
            }

            self.detector_config =  {
            "Input": 0,
            "QDType": "qd_analogue"
            }
        
            return
        
        try:
            workspace_config = self._load_json(json_path)
        except Exception as e:
            logging.error(f"Error loading Workspace JSON file: {e}")
            return

        
        self.scanGen_config = workspace_config["ScanGenerators"][0]
        self.detector_config = workspace_config["Detectors"][0]

        return

    
    def _load_json(self,json_path:str):

        with open(json_path, "r",encoding="utf-8-sig") as f:
            data = json.load(f)
        
        return data
    

    def update_config(self):

        ## update necessary parameters here

        pass

class SenseAI_ModuleControl():
    """
    This class provides control over the SenseAI module, 
    including loading the dll, adding and updating scan generators and detectors, 
    initializing scan generators, and getting images from detectors.

    """


    def __init__(self,
        dll_path:str = None,
        config: SenseAI_Config = None):
    

        self.dll_path = dll_path
        self.config = config

        self.dll_loaded: bool = False
        self.scanGen_added: bool = False
        self.detector_added: bool = False

        self.scanGen_name = "Quantum Detectors"
        self.detector_name = "Quantum Detectors"

        self.load_dll()

        if self.config is None:
            logging.info("No config provided, using default values")
            self.config = SenseAI_Config()

        self.add_ScanGenerator(self.config.scanGen_config)
        self.add_Detector(self.config.detector_config)

    
    def load_dll(self):
        """Load the SenseAI dll and initialize the SenseAI module."""
        if self.dll_path is None:
            logging.info("No dll path provided, cannot load SenseAI module. Loading Sim")
            self.senseAI = SIM_SenseAI_Module()
            self.dll_loaded = False
            return


        try:
            from senseai import SenseAI, quick_recon, quick_recon_single
            self.senseAI = SenseAI(self.dll_path)
            self.dll_loaded = True
            self.quick_recon_func = quick_recon
            self.quick_recon_single_func = quick_recon_single
            logging.info(f"SenseAI module loaded successfully from {self.dll_path}")
            
        except Exception as e:
            logging.error(f"Error loading SenseAI module: {e}")

    def add_ScanGenerator(self, scanGen_config: dict) -> None:
        """Add a scan generator with the given name and configuration."""
        try:
            self.senseAI.hw.add_scan_generator(self.scanGen_name, "QD", scanGen_config)
            self.scanGen_added = True
            logging.info(f"Scan generator {self.scanGen_name} added successfully")
        except Exception as e:
            logging.error(f"Error adding scan generator: {e}")

    def add_Detector(self, detector_config: dict) -> None:
        """Add a detector with the given name and configuration."""
        try:
            self.senseAI.hw.add_detector(self.detector_name, "ScanGenerator", self.scanGen_name, detector_config)
            self.detector_added = True
            logging.info(f"Detector {self.detector_name} added successfully")
        except Exception as e:
            logging.error(f"Error adding detector: {e}")

    def update_ScanGenerator(self, scanGen_config: dict) -> None:
        """Update the scan generator with the given name and configuration."""
        try:
            current_dir = os.getcwd()
            os.chdir(r"C:\Program Files\SenseAI\SenseAI 2026.1.1")

            self.senseAI.hw.update_scan_generator(self.scanGen_name, scanGen_config)
            logging.info(f"Scan generator {self.scanGen_name} updated successfully")

            os.chdir(current_dir)
           


        except Exception as e:
            logging.error(f"Error updating scan generator: {e}")


    def init_scan_generator(self) -> None:
        """Initialize the scan generator with the given name."""

        if not self.scanGen_added:
            logging.error(f"Scan generator {self.scanGen_name} has not been added yet, cannot initialize")
            return

        if not self.detector_added:
            logging.error(f"Detector {self.detector_name} has not been added yet, cannot initialize")
            return
        

        try:
            
             ## try work-around
            current_dir = os.getcwd()
            os.chdir(r"C:\Program Files\SenseAI\SenseAI 2026.1.1")

            self.senseAI.hw.init_scan_generator(self.scanGen_name)
            logging.info(f"Scan generator {self.scanGen_name} initialized successfully")
            self.scanGen_added = True

            os.chdir(current_dir)
        except Exception as e:
            logging.error(f"Error initializing scan generator: {e}")

    def get_detector_image(self):
        """
            Get an image from the detector with the given name.
            Returns the image as a numpy array, or None if there was an error.

            Args:
                name: Name of the detector to get the image from.
            Returns:
                Image as a numpy array, or None if there was an error.

            """
        
        if not self.scanGen_added:
            logging.error("Scan Gen not initialised")
            return None

        try:

            image = self.senseAI.hw.get_detector_image(self.detector_name)
            img = image[0]

            logging.info(f"Image acquired from detector {self.detector_name} successfully")
            return image
        except Exception as e:
            logging.error(f"Error getting image from detector: {e}")
            return None
        
    def quick_recon_single(self,image:np.ndarray, mask:np.ndarray):

        ## add image if not already done so

        self.senseAI.add_image("img01",image=image,mask=mask)

        dict_name, train, recon = self.quick_recon_func(self.senseAI, image="img01", patch_shape=[10, 10, 1, 1], dict_size=36, dict_kwargs={"OnesElement": True})


        for i in range(10):


            recon1 = self.senseAI.get_image_buffer("img01", "Reconstruction")
            time.sleep(0.5)

        
        
        return recon1



class SIM_SenseAI_Module():

    def __init__(self):
        logging.info("Initializing SIM SenseAI Module")

        self.hw = SIM_HW_Interface()

    ### Implement other methods as needed / discovered

    
class SIM_HW_Interface():
    """
    Simulated hardware interface for SenseAI, used for testing purposes.
    This class simulates the hardware interface for SenseAI, allowing for testing without actual hardware.
    It provides methods to add scan generators and detectors, update scan generators, and initialize scan generators.
    It also provides a method to get an image from the detector.
    """

    def __init__(self):
        logging.info("Initializing SIM HW Interface")
        self.scanGenerator: dict = None
        self.detector: dict = None


    def add_scan_generator(self, name, type, config):

        logging.info(f"Adding scan generator {name} of type {type} with config {config}")
        self.scanGenerator = {
            "Name": name,
            "Type": type,
            "Config": config
        }

    def add_detector(self, name, type, source, config):
        logging.info(f"Adding detector {name} of type {type} with source {source} and config {config}")
        self.detector = {
            "Name": name,
            "Type": type,
            "Source": source,
            "Config": config
        }

    def update_scan_generator(self, name, config):
        logging.info(f"Updating scan generator {name} with config {config}")
        if self.scanGenerator is not None and self.scanGenerator["Name"] == name:
            self.scanGenerator["Config"] = config
        else:
            logging.error(f"Scan generator {name} not found, cannot update")


    def init_scan_generator(self, name: str) -> None:
        """
        Initialize the scan generator with the given name.
        If the scan generator is not found, log an error.
        Args:
            name: Name of the scan generator to initialize.
        
        Returns:
            None
            
        """


        logging.info(f"Initializing scan generator {name}")
        if self.scanGenerator is not None and self.scanGenerator["Name"] == name:
            logging.info(f"Scan generator {name} initialized with config {self.scanGenerator['Config']}")
        else:
            logging.error(f"Scan generator {name} not found, cannot initialize")

    def get_detector_image(self, name: str) -> tuple[np.ndarray, np.ndarray] | None:
        """
        Get an image from the detector with the given name.
        If the detector is not found, return None.
        If the detector is found, return a simulated image based on the scan generator configuration.

        Args:
            name: Name of the detector to get the image from.
        Returns:
            List containing the simulated image and mask as 2D numpy arrays, or None if the detector is not found.

        """
        logging.info(f"Getting image from detector {name} SIMULATED ")
        if self.detector is not None and self.detector["Name"] == name:
            logging.info(f"Getting image from detector {name} with config {self.detector['Config']} SIMULATED")
            # return a simulated image based on the config
            scan_size = self.scanGenerator["Config"]["ScanSize"]

            ## SCAN SIZE IS REVERSED in config for SenseAI, FLIP HERE

            image = np.random.randint(0, 256, (scan_size[1], scan_size[0]), dtype=np.uint8)


            sampling = self.scanGenerator["Config"]["Sampling"]

            image, mask = self._zero_random_pixels(image, sampling)

            return [image, mask]
        else:
            logging.error(f"Detector {name} not found, cannot get image")
            return None
    


    def _zero_random_pixels(self, image: np.ndarray, sample_pct: float) -> tuple[np.ndarray, np.ndarray]:
        """
        Randomly set a percentage of pixels to 0 in a 2D numpy array.
        
        Args:
            image:      2D numpy array
            sample_pct: float between 0 and 1 (e.g. 0.25 for 25%)
        
        Returns:
            Tuple containing the modified copy of the image and a mask indicating which pixels were zeroed
        """
        result = image.copy()
        
        total_pixels = image.size                          # total number of pixels
        n_zero = int(total_pixels * (1-sample_pct))            # how many to zero out
        
        # Pick random flat indices, then set them to 0
        indices = np.random.choice(total_pixels, size=n_zero, replace=False)
        result.flat[indices] = 0

        mask = np.zeros(image.size, dtype=np.uint8)
        mask.flat[indices] = 1
        mask = mask.reshape(image.shape)

        return result, mask
    
    

        


def main():
    pass

if __name__ == "__main__":
    main()
        