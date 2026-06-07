import cv2
import numpy as np

def aplicar_filtros_imagen(
    img, 
    clahe_clip=2, 
    gauss_k=5, 
    otsu_offset=0, 
    min_size=50, 
    removal_areas=[],
    usar_tophat=False,
    tophat_k=30,
    usar_clahe=True,
    usar_gauss=True,
    usar_bilateral=False,
    bilateral_d=9,
    usar_ruido=True
):
    """
    Applies a dynamic processing pipeline on a BGR image based on active flags and parameters.
    Returns the binary image (Grayscale).
    """
    # 1. Corrección de Iluminación: White Top-Hat
    if usar_tophat and tophat_k > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(tophat_k), int(tophat_k)))
        bgr_proc = cv2.morphologyEx(img, cv2.MORPH_TOPHAT, kernel)
    else:
        bgr_proc = img.copy()

    # 2. Aplicar CLAHE
    if usar_clahe and clahe_clip > 0:
        clahe = cv2.createCLAHE(clipLimit=float(clahe_clip), tileGridSize=(8, 8))
        hsv = cv2.cvtColor(bgr_proc, cv2.COLOR_BGR2HSV)
        h_c, s_c, v_c = cv2.split(hsv)
        v_clahe = clahe.apply(v_c)
        hsv_clahe = cv2.merge((h_c, s_c, v_clahe))
        bgr_proc = cv2.cvtColor(hsv_clahe, cv2.COLOR_HSV2BGR)
        
    # 3. Convertir a escala de grises
    gray = cv2.cvtColor(bgr_proc, cv2.COLOR_BGR2GRAY)
    
    # 4. Suavizado / Reducción de Ruido (Bilateral o Gaussiano)
    if usar_bilateral:
        d = int(bilateral_d)
        d = max(1, d)
        gray = cv2.bilateralFilter(gray, d, 75, 75)
    elif usar_gauss:
        k = int(gauss_k) if int(gauss_k) % 2 != 0 else int(gauss_k) + 1
        k = max(1, k)
        gray = cv2.GaussianBlur(gray, (k, k), 0)

    # 5. Umbralización de Otsu con offset
    ret, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    threshold_val = max(0, min(255, ret + otsu_offset))
    _, bin_img = cv2.threshold(gray, threshold_val, 255, cv2.THRESH_BINARY)

    # 6. Aplicar filtros morfológicos especializados (remoción de ruido)
    if usar_ruido and min_size > 0:
        from .filtrado_especializado import aplicar_filtros_morfologicos
        bin_img = aplicar_filtros_morfologicos(bin_img, min_size)
    
    # 7. Aplicar eliminación de áreas manuales
    for area in removal_areas:
        ax, ay, aw, ah = area["x"], area["y"], area["w"], area["h"]
        cv2.rectangle(bin_img, (ax, ay), (ax + aw, ay + ah), 0, -1)
        
    return bin_img

def procesar_crop_individual(
    img, 
    g_clahe, 
    g_gauss, 
    g_otsu, 
    g_ruido, 
    offsets, 
    removal_areas=[],
    usar_tophat=False,
    g_tophat=30,
    usar_clahe=True,
    usar_gauss=True,
    usar_bilateral=False,
    g_bilateral=9,
    usar_ruido=True
):
    """
    Calculates final parameters combining global values and individual offsets,
    then calls aplicar_filtros_imagen.
    """
    c_clip = max(0, min(10, g_clahe + offsets.get("clahe", 0))) if usar_clahe else g_clahe
    k_val = max(1, min(15, g_gauss + offsets.get("gauss", 0))) if usar_gauss else g_gauss
    b_val = max(1, min(15, g_bilateral + offsets.get("gauss", 0))) if usar_bilateral else g_bilateral
    o_offset = g_otsu + offsets.get("otsu", 0)
    r_val = max(0, min(200, g_ruido + offsets.get("ruido", 0))) if usar_ruido else g_ruido
    
    return aplicar_filtros_imagen(
        img, 
        clahe_clip=c_clip, 
        gauss_k=k_val, 
        otsu_offset=o_offset, 
        min_size=r_val, 
        removal_areas=removal_areas,
        usar_tophat=usar_tophat,
        tophat_k=g_tophat,
        usar_clahe=usar_clahe,
        usar_gauss=usar_gauss,
        usar_bilateral=usar_bilateral,
        bilateral_d=b_val,
        usar_ruido=usar_ruido
    )





