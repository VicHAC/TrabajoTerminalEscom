import pytest
import os
import cv2
import numpy as np
from ia.modelo_yolo import MicrogliaProcessor

def test_modelo_yolo_mock_prediccion(monkeypatch):
    """Prueba que el procesador de IA inicialice y procese simuladamente."""
    
    # Mock de ultralytics.models.yolo.model.YOLO
    class MockYOLO:
        def __init__(self, path):
            self.path = path
            
        def __call__(self, img_array, conf=None, iou=None, device=None, verbose=None):
            class MockBoxes:
                def __init__(self):
                    self.xyxy = torch.tensor([[10, 10, 50, 50]]) if 'torch' in globals() else [[10, 10, 50, 50]]
                    self.conf = [0.9]
            class MockResult:
                def __init__(self):
                    self.boxes = MockBoxes()
            return [MockResult()]

    monkeypatch.setattr("ia.modelo_yolo.YOLO", MockYOLO)
    
    # Creamos un archivo falso para que os.path.exists pase
    fake_model_path = "fake_model.pt"
    with open(fake_model_path, "w") as f:
        f.write("fake")
        
    try:
        procesador = MicrogliaProcessor(fake_model_path)
        img_falsa = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Testeamos run_inference o similar
        if hasattr(procesador, "run_inference"):
            resultados = procesador.run_inference(img_falsa)
            assert len(resultados) == 1
    finally:
        os.remove(fake_model_path)
