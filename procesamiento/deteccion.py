import os
import uuid
from ia.modelo_yolo import MicrogliaProcessor

def ejecutar_conteo_ia(ruta_imagen, base_output_folder, confidence_threshold=0.20):
    """
    Executes YOLO model detection on the image and returns crops folder, microglia count, and bounding boxes.
    """
    model_path = os.path.join(os.getcwd(), "ia", "entrenamiento_resultados", "modelo_microglias5", "weights", "best.pt")
    processor = MicrogliaProcessor(model_path=model_path, confidence_threshold=confidence_threshold)
    resultado = processor.process_and_crop(ruta_imagen, base_output_folder=base_output_folder)
    
    if len(resultado) == 3:
        crops_folder, count, boxes_data = resultado
        # Initialize offsets and removal areas
        for box in boxes_data:
            box["offsets"] = {"clahe": 0, "gauss": 0, "otsu": 0, "ruido": 0}
            box["removal_areas"] = []
        return crops_folder, count, boxes_data
    else:
        crops_folder, count = resultado
        return crops_folder, count, []

def recortar_y_guardar_manual(orig_pixmap_or_cv_img, x, y, w, h, crops_folder):
    """
    Crops the original image (QPixmap or numpy array) and saves it as a manual crop in the crops folder.
    Returns the saved crop file path and the generated filename.
    """
    nombre_archivo = f"manual_{uuid.uuid4().hex[:6]}.png"
    ruta_guardado = os.path.join(crops_folder, nombre_archivo)
    
    # Check if it's a QPixmap (PyQt6 object)
    try:
        from PyQt6.QtCore import QRect
        from PyQt6.QtGui import QPixmap
        if isinstance(orig_pixmap_or_cv_img, QPixmap):
            rect_recorte = QRect(x, y, w, h)
            pixmap_recorte = orig_pixmap_or_cv_img.copy(rect_recorte)
            pixmap_recorte.save(ruta_guardado, "PNG")
            return ruta_guardado, nombre_archivo
    except ImportError:
        pass
        
    # fallback to numpy / OpenCV
    import cv2
    crop_img = orig_pixmap_or_cv_img[y:y+h, x:x+w]
    is_success, im_buf_arr = cv2.imencode(".png", crop_img)
    if is_success:
        im_buf_arr.tofile(ruta_guardado)
    else:
        cv2.imwrite(ruta_guardado, crop_img)
    return ruta_guardado, nombre_archivo
