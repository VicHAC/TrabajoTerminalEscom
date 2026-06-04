import cv2
import numpy as np

def aplicar_filtros_imagen(img, clahe_clip, gauss_k, otsu_offset, min_size=50, removal_areas=[]):
    """
    Applies CLAHE, Gaussian blur, Otsu binarization, morphological filtering, and blackouts removal areas on a BGR image.
    Returns the binary image (Grayscale).
    """
    # 1. Aplicar CLAHE si clipLimit > 0
    if clahe_clip > 0:
        clahe = cv2.createCLAHE(clipLimit=float(clahe_clip), tileGridSize=(8, 8))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h_c, s_c, v_c = cv2.split(hsv)
        v_clahe = clahe.apply(v_c)
        hsv_clahe = cv2.merge((h_c, s_c, v_clahe))
        bgr_proc = cv2.cvtColor(hsv_clahe, cv2.COLOR_HSV2BGR)
    else:
        bgr_proc = img.copy()
        
    # 2. Convertir a escala de grises
    gray = cv2.cvtColor(bgr_proc, cv2.COLOR_BGR2GRAY)
    
    # 3. Aplicar filtro gaussiano
    k = gauss_k if gauss_k % 2 != 0 else gauss_k + 1
    k = max(1, k)
    blur = cv2.GaussianBlur(gray, (k, k), 0)
    
    # 4. Umbralización de Otsu con offset
    ret, _ = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    threshold_val = max(0, min(255, ret + otsu_offset))
    _, bin_img = cv2.threshold(blur, threshold_val, 255, cv2.THRESH_BINARY)

    # 4.5. Aplicar filtros morfológicos especializados
    from .filtrado_especializado import aplicar_filtros_morfologicos
    bin_img = aplicar_filtros_morfologicos(bin_img, min_size)
    
    # 5. Aplicar eliminación de áreas manuales
    for area in removal_areas:
        ax, ay, aw, ah = area["x"], area["y"], area["w"], area["h"]
        cv2.rectangle(bin_img, (ax, ay), (ax + aw, ay + ah), 0, -1)
        
    return bin_img

def procesar_crop_individual(img, g_clahe, g_gauss, g_otsu, g_ruido, offsets, removal_areas=[]):
    """
    Calculates final parameters combining global values and individual offsets,
    then calls aplicar_filtros_imagen.
    """
    c_clip = max(0, min(10, g_clahe + offsets.get("clahe", 0)))
    k_val = max(1, min(15, g_gauss + offsets.get("gauss", 0)))
    o_offset = g_otsu + offsets.get("otsu", 0)
    r_val = max(0, min(200, g_ruido + offsets.get("ruido", 0)))
    
    return aplicar_filtros_imagen(img, c_clip, k_val, o_offset, r_val, removal_areas)




