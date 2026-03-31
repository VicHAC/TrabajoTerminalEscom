import os
from pathlib import Path

import cv2
import numpy as np
import tifffile as tiff
from ultralytics.models.yolo.model import YOLO


class MicrogliaProcessor:
    def __init__(self, model_path, confidence_threshold=0.5):
        # Initializes the YOLO model with the specified weights and sets the confidence threshold.
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self.model = YOLO(model_path)
        self.threshold = confidence_threshold

    def read_tiff_image(self, image_path):
        # Reads a TIFF image and standardizes its format to 8-bit BGR for YOLO processing.
        try:
            img_raw = tiff.imread(image_path)

            if img_raw.ndim == 3:
                if img_raw.dtype != np.uint8:
                    img_8bit = (
                        (img_raw - img_raw.min())
                        / (img_raw.max() - img_raw.min())
                        * 255
                    ).astype(np.uint8)
                else:
                    img_8bit = img_raw

                bgr_image = cv2.cvtColor(img_8bit, cv2.COLOR_RGB2BGR)
                return bgr_image, img_raw

            elif img_raw.ndim == 2:
                if img_raw.dtype != np.uint8:
                    img_8bit = (
                        (img_raw - img_raw.min())
                        / (img_raw.max() - img_raw.min())
                        * 255
                    ).astype(np.uint8)
                else:
                    img_8bit = img_raw

                bgr_image = cv2.cvtColor(img_8bit, cv2.COLOR_GRAY2BGR)
                return bgr_image, img_raw

            else:
                raise ValueError("Unsupported TIFF image format.")

        except Exception as e:
            raise Exception(f"Error reading TIFF: {e}")

    def process_and_crop(self, input_image_path, base_output_folder):
        # Executes object detection on the input image and saves individual crops of detected objects.
        base_name = Path(input_image_path).stem
        crops_folder = os.path.join(base_output_folder, f"crops_{base_name}")
        os.makedirs(crops_folder, exist_ok=True)

        detection_img, raw_img = self.read_tiff_image(input_image_path)
        height, width = detection_img.shape[:2]

        results = self.model.predict(
            source=detection_img, conf=self.threshold, verbose=False
        )
        result = results[0]
        boxes = result.boxes

        saved_count = 0

        if boxes is None:
            return crops_folder, saved_count

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

            crop_filename = f"microglia_{i:03d}_conf_{conf:.2f}.png"
            save_path = os.path.join(crops_folder, crop_filename)

            cv2.imwrite(save_path, crop)
            saved_count += 1

        return crops_folder, saved_count


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
