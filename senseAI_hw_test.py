from senseai import SenseAI
import cv2
import json
import numpy as np
import os
import matplotlib.pyplot as plt
### test using webcam
from fibsem.SenseAI_SG import SenseAI_Config
import time



def take_image_and_show(s: SenseAI):    

    name = "WCScanGen"

    print("Waiting")
    s.hw.wait_for_scan_gen_frame(name)
    print("setting state")
    s.hw.set_scan_generator_state(name,paused=False)
    print("waiting for frame")
    s.hw.wait_for_scan_gen_frame(name)
    print("Getting detector image")
    output = s.hw.get_detector_image("WCDetector")
    print("Pause scanning")
    s.hw.set_scan_generator_state(name,paused=True)

    plt.imshow(output[0])
    plt.show()

    return output


def main():
        
    ## with microscope
    SenseAI_version_path = r"C:\Program Files\SenseAI\SenseAI 2026.1.1"

    s = SenseAI(os.path.join(SenseAI_version_path,"SenseAI.dll"))

    workspace_hydra_config = SenseAI_Config(r"C:\Users\Administrator\Documents\SenseAI\Workspaces\hydra_workspace.json")

    sc_config = workspace_hydra_config.scanGen_config
    d_config = workspace_hydra_config.detector_config




    sc = s.hw.add_scan_generator("Quantum Detectors","QD",sc_config)

    time.sleep(1)

    d = s.hw.add_detector("Quantum Detectors","ScanGenerator",sc["Name"],d_config)

    time.sleep(1)

    current_dir = os.getcwd()
    os.chdir(SenseAI_version_path)

    try:
        s.hw.init_scan_generator("Quantum Detectors")
    except Exception as e:
        print(f"Error initializing scan generator: {e}")
        return

    os.chdir(current_dir)

    s.hw.update_scan_generator(sc["Name"],
                           {
                               "Pattern":"Linehop",
                               "Sampling":0.5,
                               "ResetBuffer":True,
                               "ScanSize": [640, 480]
                           })

    output = take_image_and_show(s)


if __name__ == "__main__":
    main() 