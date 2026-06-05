import cv2
import numpy as np
import warnings
from skimage.morphology import remove_small_objects

# Ignorar advertencias de obsolescencia de skimage en la consola
warnings.filterwarnings("ignore", category=FutureWarning)

def aplicar_filtros_morfologicos(bin_img, min_size):
    """
    Aplica filtros morfológicos especializados a una imagen binaria de microglía:
    1. Filtro por área (remove_small_objects) para eliminar ruido de fondo
       sin alterar la forma de las microglías principales.
    """
    if bin_img is None:
        return None

    # Eliminación de objetos pequeños (ruido) por área en píxeles
    if min_size > 0:
        img_bool = bin_img > 0
        img_clean = remove_small_objects(img_bool, min_size=int(min_size))
        return (img_clean * 255).astype(np.uint8)

    return bin_img.copy()
