import logging
import os
from pathlib import Path

import cv2
import numpy as np
from skimage.morphology import skeletonize

# Configuración del log para ver detalles en la terminal
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s"
)


class MorphologyAnalyzer:
    def __init__(self, input_directory: str, output_directory: str):
        self.input_dir = Path(input_directory)
        self.output_dir = Path(output_directory)

        logging.info(f"Analizador iniciado.")
        logging.info(
            f"Carpeta de entrada (Buscando imágenes aquí): {self.input_dir.absolute()}"
        )
        logging.info(
            f"Carpeta de salida (Guardando esqueletos aquí): {self.output_dir.absolute()}"
        )

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_image(self, image_path: Path) -> bool:
        img_raw = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if img_raw is None:
            logging.error(f"No se pudo leer la imagen: {image_path}")
            return False

        # Suavizado y Binarización
        img_blurred = cv2.GaussianBlur(img_raw, (5, 5), 0)
        _, img_binary = cv2.threshold(
            img_blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        # Skeletonize
        img_bool = img_binary > 0
        skeleton = skeletonize(img_bool)
        skeleton_img = (skeleton * 255).astype(np.uint8)

        output_filename = f"{image_path.name}"
        save_path = self.output_dir / output_filename

        cv2.imwrite(str(save_path), skeleton_img)
        return True

    def execute_batch_processing(self) -> int:
        count = 0
        extensions = ("*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff")

        found_any = False
        for ext in extensions:
            files = list(self.input_dir.glob(ext))
            if files:
                found_any = True
                logging.info(
                    f"Se encontraron {len(files)} archivos con extensión {ext}"
                )

            for file in files:
                if self.process_image(file):
                    count += 1

        if not found_any:
            logging.warning(
                f"¡Atención! No se encontró ningún archivo de imagen en {self.input_dir}"
            )

        return count


if __name__ == "__main__":
    # Ruta base del proyecto
    base_path = Path("./analisis_resultados")
    logging.info(f"--- Iniciando escaneo global en: {base_path.absolute()} ---")

    if not base_path.exists():
        logging.error(f"La carpeta raíz '{base_path}' NO EXISTE. Revisa la ruta.")
    else:
        total_global = 0
        # Recorre cada carpeta dentro de analisis_resultados (ej. Sin título-22)
        for folder in base_path.iterdir():
            if folder.is_dir():
                logging.info(f"Explorando subcarpeta encontrada: {folder.name}")

                # Buscamos específicamente la carpeta 'filtradas'
                filtradas_path = folder / "filtradas"

                if filtradas_path.exists():
                    logging.info(
                        f"  [OK] Carpeta 'filtradas' localizada en: {filtradas_path}"
                    )
                    output_path = base_path / f"esqueletos_{folder.name}"

                    analyzer = MorphologyAnalyzer(
                        input_directory=str(filtradas_path),
                        output_directory=str(output_path),
                    )

                    total = analyzer.execute_batch_processing()
                    total_global += total
                    logging.info(
                        f"  [FIN] {total} esqueletos generados para esta carpeta."
                    )
                else:
                    logging.warning(
                        f"  [OMITIDO] No existe la carpeta 'filtradas' dentro de {folder.name}"
                    )

        logging.info(f"--- Proceso finalizado. Total global: {total_global} ---")
