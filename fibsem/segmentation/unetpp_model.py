from segmentation_models_pytorch import UnetPlusPlus
import os
import logging
import numpy as np
import torch
import torch.nn.functional as F
from fibsem.segmentation.utils import decode_segmap, download_checkpoint

class SegmentationModelUNetPP:
    def __init__(self, 
            checkpoint: str = None, 
            encoder: str = "resnet34", 
            num_classes: int = 3, 
            _fix_numeric_scaling: bool = False) -> None:
    

        super().__init__()


        self.checkpoint: str = checkpoint
        self.mode = "eval"
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.num_classes = num_classes
        self._fix_numeric_scaling = _fix_numeric_scaling

        self.load_model(checkpoint=checkpoint,encoder=encoder,classes=self.num_classes)

        
        
    def load_model(self, checkpoint: str = None, encoder: str = "resnet34", classes: int = 3) -> None:
        
        checkpoint = download_checkpoint(checkpoint)

        checkpoint_dict = torch.load(checkpoint, map_location=self.device)

        self.model = UnetPlusPlus(
            encoder_name=checkpoint_dict.get("encoder", encoder),
            encoder_weights="imagenet",
            in_channels=1,
            classes=checkpoint_dict.get("nc", classes),
        )
        self.model.to(self.device)

        self.model.load_state_dict(checkpoint_dict["checkpoint"])




    def pre_process(self, img: np.ndarray) -> torch.Tensor:
        """Pre-process the image for inference"""
        img_t = torch.Tensor(img).float().to(self.device)

        if self._fix_numeric_scaling:
            img_t /=  255.0 # scale float to 0 - 1
        if img_t.ndim == 2:
            img_t = img_t.unsqueeze(0).unsqueeze(0)  # add batch dim and channel dim
        elif img_t.ndim == 3:
            if img_t.shape[0] > 1:  # means the first dim is batch dim
                img_t = img_t.unsqueeze(1)  # add channel dim
            else:
                img_t = img_t.unsqueeze(0)  # add batch dim

        assert img_t.ndim == 4, f"Expected 4 dims, got {img_t.ndim}"

        logging.debug({"msg": "pre_process", "shape": img_t.shape, "dtype": img_t.dtype, "min": img_t.min(), "max": img_t.max()})

        return img_t

    def inference(self, img: np.ndarray, rgb: bool = True) -> np.ndarray:
        """Run model inference on the input image"""
        with torch.no_grad():
            img_t = self.pre_process(img)

            outputs = self.model(img_t)
            outputs = F.softmax(outputs, dim=1)
            masks = torch.argmax(outputs, dim=1).detach().cpu().numpy()
        
        # decode to rgb
        if rgb:
            masks = self.postprocess(masks, nc=self.num_classes)

        # TODO: return masks, scores, logits
        return masks

    def inference_v2(self, img: np.ndarray, rgb: bool = True) -> np.ndarray:
        """Run model inference on the input image"""
        with torch.no_grad():
            img_t = self.pre_process(img)

            outputs = self.model(img_t)
            outputs = F.softmax(outputs, dim=1)
            masks = torch.argmax(outputs, dim=1).detach().cpu().numpy()
        
        # decode to rgb
        if rgb:
            masks = self.postprocess(masks, nc=self.num_classes)

        # TODO: return masks, scores, logits
        return masks, outputs
        
    def postprocess(self, masks, nc):
        # TODO: vectorise this properly
        # TODO: use decode_segmap_v2
        output_masks = []
        for i in range(len(masks)):
            output_masks.append(decode_segmap(masks[i], nc=nc))

        if len(output_masks) == 1:
            output_masks = output_masks[0]
        return np.array(output_masks)





