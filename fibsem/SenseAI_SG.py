


### scan generator and external detector imaging code here
### also code for senseAI processing and reconstruction here


class SenseAI_Config():
    def __init__(self,
        ScanGen_config_path: str = None,
        Detector_config_path: str = None):

        self.ScanGen_ConfigPath = ScanGen_config_path
        self.Detector_ConfigPath = Detector_config_path

        self.load_config_information()

    def load_config_information(self):

        ## load the config from the json into python dicts

        pass
    

    def update_config(self):

        ## update necessary parameters here

        pass

class SenseAI_ModuleControl():
    def __init__(self,
        dll_path:str = None,
        config: SenseAI_Config = None):
    

        self.dll_path = dll_path
        self.config = config
    





def main():
    pass

if __name__ == "__main__":
    main()
        