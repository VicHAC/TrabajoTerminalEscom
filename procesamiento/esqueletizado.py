import cv2
import numpy as np
from skimage.morphology import skeletonize

def generar_esqueleto_topologico(bin_img):
    """
    Reduces a binary image (Grayscale) to a topological skeleton.
    Returns the skeleton image (uint8, 0 or 255).
    """
    img_bool = bin_img > 0
    skeleton = skeletonize(img_bool)
    skeleton_img = (skeleton * 255).astype(np.uint8)
    return skeleton_img

def generar_esqueleto_de_archivo(fil_path):
    """
    Loads a filtered image from path, runs skeletonization, and returns the skeleton image.
    """
    with open(fil_path, "rb") as f:
        file_bytes = bytearray(f.read())
    img_array = np.asarray(file_bytes, dtype=np.uint8)
    img_raw = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
    if img_raw is None:
        return None
    _, bin_img = cv2.threshold(img_raw, 127, 255, cv2.THRESH_BINARY)
    
    return generar_esqueleto_topologico(bin_img)
