import os
from pathlib import Path

import cv2
import numpy as np
from skimage.morphology import skeletonize


class MorphologyAnalyzer:
    def __init__(self, base_folder: str):
        """
        Initializes the morphology analyzer targeting a specific image's result folder.
        """
        self.base_folder = Path(base_folder)
        self.crops_dir = self.base_folder / "crops"
        self.filtered_dir = self.base_folder / "filtradas"
        self.skeleton_dir = self.base_folder / "esqueletos"

    def _apply_otsu_blur(self, img_path: Path, out_path: Path):
        """Helper method: Applies Gaussian Blur and Otsu Binarization."""
        img_raw = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img_raw is None:
            return False

        img_blurred = cv2.GaussianBlur(img_raw, (5, 5), 0)
        _, img_binary = cv2.threshold(
            img_blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        cv2.imwrite(str(out_path), img_binary)
        return True

    def _apply_skeleton(self, img_path: Path, out_path: Path):
        """Helper method: Reduces binary image to a topological skeleton."""
        img_raw = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img_raw is None:
            return False

        img_bool = img_raw > 0
        skeleton = skeletonize(img_bool)
        skeleton_img = (skeleton * 255).astype(np.uint8)

        cv2.imwrite(str(out_path), skeleton_img)
        return True

    def execute_filtering(self, global_img_path: str):
        """Step 1: Applies filtering to all individual crops and the global image."""
        self.filtered_dir.mkdir(parents=True, exist_ok=True)
        count = 0

        # 1. Process individual crops
        if self.crops_dir.exists():
            for file in self.crops_dir.glob("*.png"):
                out_path = self.filtered_dir / file.name
                if self._apply_otsu_blur(file, out_path):
                    count += 1

        # 2. Process the global large image for the UI Viewer
        global_out = self.base_folder / "global_filtrada.png"
        self._apply_otsu_blur(Path(global_img_path), global_out)

        return count, str(global_out)

    def execute_skeletonization(self):
        """Step 2: Applies skeletonization to the filtered images."""
        self.skeleton_dir.mkdir(parents=True, exist_ok=True)
        count = 0

        # 1. Process individual filtered crops
        if self.filtered_dir.exists():
            for file in self.filtered_dir.glob("*.png"):
                out_path = self.skeleton_dir / file.name
                if self._apply_skeleton(file, out_path):
                    count += 1

        # 2. Process the global filtered image for the UI Viewer
        global_filtered = self.base_folder / "global_filtrada.png"
        global_out = self.base_folder / "global_esqueleto.png"

        if global_filtered.exists():
            self._apply_skeleton(global_filtered, global_out)

        return count, str(global_out)
