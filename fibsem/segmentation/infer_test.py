from unetpp_model import SegmentationModelUNetPP
import tifffile as tiff
import numpy as np
import matplotlib.pyplot as plt


checkpoint = r"C:\Users\rohit\Documents\fibsem_model_training\models\lamella_and_trench_1\unetpp_model-20260320-31.pt"

model = SegmentationModelUNetPP(checkpoint=checkpoint, encoder="resnet34", num_classes=3, _fix_numeric_scaling=True)

print("Model loaded successfully")

#import image

image_path = r"C:\Users\rohit\Documents\fibsem_model_training\cryoxflo_thin_lamella_2_images\010.tif"


image = tiff.imread(image_path)


#run inference

masks = model.inference(image)

print("Inference completed successfully")

print("Masks shape:", masks.shape)

#visualize
mask1 = masks[:,:,0]  # assuming masks is (H, W, 3) and we want the first channel

plt.imshow(mask1)
plt.title("Predicted Mask")
plt.axis("off")
plt.show()



