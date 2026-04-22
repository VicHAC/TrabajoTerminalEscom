import os
from pathlib import Path
import cv2
import numpy as np
import tifffile as tiff
import torch
from ultralytics.models.yolo.model import YOLO

# Fix for loading YOLO models in some environments
_original_load = torch.load

def _trusted_torch_load(*args, **kwargs):
    kwargs["weights_only"] = False
    return _original_load(*args, **kwargs)

torch.load = _trusted_torch_load

def get_optimal_device():
    """Evaluates available hardware and returns the optimal computation device."""
    if not torch.cuda.is_available():
        return "cpu"
    capability = torch.cuda.get_device_capability()
    if capability[0] > 9:
        return "cpu"
    return "cuda"

class MicrogliaProcessor:
    def __init__(self, model_path, confidence_threshold=0.20):
        """Initializes the YOLO model and sets the device."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.device = get_optimal_device()

    def read_image(self, image_path):
        """Reads images (including high-bit TIFFs) and converts them to 8-bit BGR."""
        try:
            ext = Path(image_path).suffix.lower()

            if ext in [".tif", ".tiff"]:
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

    def _filter_inner_boxes(self, raw_boxes, ioa_threshold=0.40):
        """
        Filtra de manera agresiva cuadros interiores o falsas detecciones superpuestas.
        Utiliza el cálculo de 'Intersection over Area' (IoA) de la caja más pequeña.
        """
        # Ordenamos de la más grande a la más pequeña por área
        raw_boxes.sort(key=lambda b: b['area'], reverse=True)
        filtered_boxes = []

        for current_box in raw_boxes:
            keep = True
            for larger_box in filtered_boxes:
                # Calcular coordenadas de intersección
                ix1 = max(current_box['x1'], larger_box['x1'])
                iy1 = max(current_box['y1'], larger_box['y1'])
                ix2 = min(current_box['x2'], larger_box['x2'])
                iy2 = min(current_box['y2'], larger_box['y2'])

                iw = max(0, ix2 - ix1)
                ih = max(0, iy2 - iy1)
                inter_area = iw * ih

                # Si el choque es del 40% o más del área de la caja chica, la descartamos
                if inter_area > 0:
                    ioa = inter_area / current_box['area']
                    if ioa >= ioa_threshold:
                        keep = False
                        break
            
            if keep:
                filtered_boxes.append(current_box)

        return filtered_boxes

    def process_and_crop(self, input_image_path, base_output_folder):
        """
        Executes YOLO inference, filters overlapping nested boxes, crops detected objects, 
        and returns the bounding box coordinates for interactive UI rendering.
        """
        base_name = Path(input_image_path).stem
        crops_folder = os.path.join(base_output_folder, base_name, "crops")
        os.makedirs(crops_folder, exist_ok=True)

        bgr_image, img_raw = self.read_image(input_image_path)
        if bgr_image is None:
            raise ValueError(f"Could not read the image: {input_image_path}")

        results = self.model.predict(
            source=bgr_image,
            conf=self.confidence_threshold,
            device=self.device,
            save=False
        )

        raw_boxes = []
        if len(results) > 0 and results[0].boxes is not None:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                area = (x2 - x1) * (y2 - y1)
                raw_boxes.append({
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'area': area
                })

        final_boxes = self._filter_inner_boxes(raw_boxes, ioa_threshold=0.40)
        detected_boxes_data = []

        for i, b in enumerate(final_boxes):
            x1, y1, x2, y2 = b['x1'], b['y1'], b['x2'], b['y2']

            crop_img = bgr_image[y1:y2, x1:x2]
            crop_filename = f"microglia_{i+1}.png"
            crop_path = os.path.join(crops_folder, crop_filename)
            cv2.imwrite(crop_path, crop_img)

            detected_boxes_data.append({
                "x": x1,
                "y": y1,
                "w": x2 - x1,
                "h": y2 - y1,
                "crop_path": crop_path
            })

        return crops_folder, len(detected_boxes_data), detected_boxes_data


if __name__ == "__main__":
    # Test execution block
    model_path = "ia/entrenamiento_resultados/modelo_microglias5/weights/best.pt"
    test_image = "imagenes_microscopio_raw/x5/Sin título-22.tif"
    results_folder = "./resultados_seleccion"
    
    try:
        if os.path.exists(test_image):
            processor = MicrogliaProcessor(model_path)
            processor.process_and_crop(test_image, results_folder)
            print("Model loaded and processed successfully.")
        else:
            print(f"Error: Image not found at {test_image}")
    except Exception as e:
        print(f"Critical error: {e}")