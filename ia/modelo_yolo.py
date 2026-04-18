import os
from pathlib import Path

import cv2
import numpy as np
import tifffile as tiff
from ultralytics.models.yolo.model import YOLO
import torch

_original_load = torch.load
def _trusted_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _trusted_torch_load

def get_optimal_device():
    # Evaluates available hardware and returns the optimal supported computation device
    if not torch.cuda.is_available():
        return 'cpu'
    
    capability = torch.cuda.get_device_capability()
    if capability[0] > 9:
        return 'cpu'
        
    return 'cuda'

class MicrogliaProcessor:
    def __init__(self, model_path, confidence_threshold=0.20):
        # Initializes the YOLO model with the specified weights and sets the confidence threshold.
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.device = get_optimal_device()

    def read_image(self, image_path):
        # Determines the file extension and delegates the image reading to the appropriate library.
        try:
            ext = Path(image_path).suffix.lower()
            
            if ext in ['.tif', '.tiff']:
                img_raw = tiff.imread(image_path)
                
                if img_raw.ndim == 3:
                    if img_raw.dtype != np.uint8:
                        img_8bit = ((img_raw - img_raw.min()) / (img_raw.max() - img_raw.min()) * 255).astype(np.uint8)
                    else:
                        img_8bit = img_raw
                    bgr_image = cv2.cvtColor(img_8bit, cv2.COLOR_RGB2BGR)
                    return bgr_image, img_raw
                    
                elif img_raw.ndim == 2:
                    if img_raw.dtype != np.uint8:
                        img_8bit = ((img_raw - img_raw.min()) / (img_raw.max() - img_raw.min()) * 255).astype(np.uint8)
                    else:
                        img_8bit = img_raw
                    bgr_image = cv2.cvtColor(img_8bit, cv2.COLOR_GRAY2BGR)
                    return bgr_image, img_raw
                else:
                    raise ValueError("Unsupported TIFF image format.")
            
            else:
                # Uses OpenCV to load standard formats like PNG or JPG
                img_raw = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
                if img_raw is None:
                    raise ValueError(f"OpenCV could not decode the image file: {image_path}")
                
                if len(img_raw.shape) == 3:
                    bgr_image = img_raw
                elif len(img_raw.shape) == 2:
                    bgr_image = cv2.cvtColor(img_raw, cv2.COLOR_GRAY2BGR)
                else:
                    raise ValueError("Unsupported standard image format.")
                    
                return bgr_image, img_raw

        except Exception as e:
            raise Exception(f"Error reading image: {e}")

    def process_and_crop(self, input_image_path, base_output_folder):
        # Executes object detection on the input image and saves individual crops of detected objects.
        base_name = Path(input_image_path).stem
        image_base_folder = os.path.join(base_output_folder, base_name)
        
        crops_folder = os.path.join(image_base_folder, "originales")
        os.makedirs(crops_folder, exist_ok=True)
        
        filtered_crops_folder = os.path.join(image_base_folder, "filtradas")
        os.makedirs(filtered_crops_folder, exist_ok=True)

        detection_img, raw_img = self.read_image(input_image_path)
        height, width = detection_img.shape[:2]

        results = self.model.predict(
            source=detection_img,
            conf=self.confidence_threshold,
            device=self.device,
            save=True,
            name=base_name,
            exist_ok=True
        )
        result = results[0]
        boxes = result.boxes

        saved_count = 0

        if boxes is None:
            return image_base_folder, saved_count

        for i in range(len(boxes)):
            box = boxes[i]
            coords = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = coords

            conf = box.conf[0].cpu().numpy()

            margin = 5
            x1_m = max(0, x1 - margin)
            y1_m = max(0, y1 - margin)
            x2_m = min(width, x2 + margin)
            y2_m = min(height, y2 + margin)

            crop = detection_img[y1_m:y2_m, x1_m:x2_m]

            if crop.size == 0:
                continue

            crop_filename = f"celula_{i:03d}.png"
            save_path = os.path.join(crops_folder, crop_filename)

            # Usar imencode y tofile evita bugs silenciosos de cv2.imwrite en Windows
            # cuando la ruta tiene caracteres especiales o el array no es contiguo
            crop_contiguo = np.ascontiguousarray(crop)
            is_success, im_buf_arr = cv2.imencode(".png", crop_contiguo)
            if is_success:
                im_buf_arr.tofile(save_path)
                saved_count += 1
                
                # --- Aplicar filtros para preparar esqueletización ---
                # 1. Convertir a escala de grises
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                # 2. Aplicar filtro gaussiano para suavizar y reducir ruido (previene falsas ramas)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                # 3. Binarizar con Otsu para detectar automáticamente el umbral
                # Deja la microglía (si es más clara) en blanco y el fondo en negro.
                _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Guardar el recorte filtrado en la nueva carpeta
                filtered_save_path = os.path.join(filtered_crops_folder, crop_filename)
                binary_contiguo = np.ascontiguousarray(binary)
                is_success_filt, im_buf_arr_filt = cv2.imencode(".png", binary_contiguo)
                if is_success_filt:
                    im_buf_arr_filt.tofile(filtered_save_path)
                else:
                    print(f"Error al codificar el recorte filtrado: {filtered_save_path}")
            else:
                print(f"Error al codificar el recorte: {save_path}")

        return image_base_folder, saved_count


if __name__ == "__main__":
    # Entry point for testing the detection pipeline.
    model_path = "modelo_microglias_best.pt"
    test_image_path = "./imagenes_microscopio_raw/x5/Sin título-22.tif"
    results_folder = "./resultados_seleccion"

    try:
        processor = MicrogliaProcessor(model_path, confidence_threshold=0.30)

        if os.path.exists(test_image_path):
            processor.process_and_crop(test_image_path, results_folder)
        else:
            print(f"Image not found: {test_image_path}")

    except Exception as e:
        print(f"Critical error: {e}")
