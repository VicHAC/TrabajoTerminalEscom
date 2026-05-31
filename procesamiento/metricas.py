from ia.extract_microglia_metrics import extract_microglia_metrics

def extraer_metricas_esqueleto(skeleton_image_path):
    """
    Extracts microglia morphological metrics from a skeletonized image file path.
    """
    return extract_microglia_metrics(skeleton_image_path)
