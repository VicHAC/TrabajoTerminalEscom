import logging
import numpy as np
import tifffile as tiff
from PIL import Image
from pathlib import Path

# Configures the logging system to output information to the console and a file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("conversion_log.txt", mode='w')
    ]
)

class ImageFormatConverter:
    def __init__(self, input_directory: str, output_directory: str):
        # Initializes directories and creates the output structure
        self.input_dir = Path(input_directory)
        self.output_dir = Path(output_directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Initialized converter. Input directory: {self.input_dir} | Output directory: {self.output_dir}")

    def normalize_intensity(self, image_array: np.ndarray) -> np.ndarray:
        # Maps pixel values to a standard 8-bit range
        if image_array.dtype != np.uint8:
            min_val = image_array.min()
            max_val = image_array.max()
            if max_val > min_val:
                return ((image_array - min_val) / (max_val - min_val) * 255).astype(np.uint8)
            else:
                return np.zeros_like(image_array, dtype=np.uint8)
        return image_array

    def process_image(self, file_path: Path) -> bool:
        # Reads a single TIFF file, converts its color space, and saves it as PNG
        logging.debug(f"Starting processing for file: {file_path}")
        try:
            img_raw = tiff.imread(str(file_path))
            logging.debug(f"Successfully read {file_path.name}. Shape: {img_raw.shape}, Dtype: {img_raw.dtype}")
            
            img_8bit = self.normalize_intensity(img_raw)

            if img_8bit.ndim == 2:
                # Generates a grayscale image object
                pil_image = Image.fromarray(img_8bit, mode='L')
            elif img_8bit.ndim == 3:
                # Generates an RGB image object
                pil_image = Image.fromarray(img_8bit, mode='RGB')
            else:
                logging.warning(f"Unsupported number of dimensions ({img_8bit.ndim}) for file {file_path}")
                return False

            relative_path = file_path.relative_to(self.input_dir)
            output_file = self.output_dir / relative_path.with_suffix('.png')
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            pil_image.save(str(output_file), format="PNG")
            logging.info(f"Successfully converted and saved: {output_file}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to process {file_path}. Error: {str(e)}", exc_info=True)
            return False

    def execute_batch_conversion(self) -> int:
        # Collects all files recursively and processes those with TIFF extensions case-insensitively
        success_count = 0
        all_files = list(self.input_dir.rglob("*"))
        tiff_files = [f for f in all_files if f.is_file() and f.suffix.lower() in ('.tif', '.tiff')]
        
        logging.info(f"Found {len(tiff_files)} TIFF files to process.")
        
        for tiff_file in tiff_files:
            if self.process_image(tiff_file):
                success_count += 1
        return success_count

if __name__ == "__main__":
    # Defines directories and starts the conversion process
    input_folder = "./imagenes_microscopio_raw"
    output_folder = "./imagenes_roboflow_png"
    
    converter = ImageFormatConverter(input_folder, output_folder)
    processed_total = converter.execute_batch_conversion()
    logging.info(f"Batch conversion finished. Total successfully processed files: {processed_total}")