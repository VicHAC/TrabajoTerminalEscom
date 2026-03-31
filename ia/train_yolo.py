import os

from ultralytics import settings
from ultralytics.models.yolo.model import YOLO


class ModelTrainer:
    def __init__(self, base_model="yolov8n.pt"):
        # Initializes the YOLO model with a pre-trained base weight file.
        self.model = YOLO(base_model)

    def execute_training(self, data_config_path, epochs_count=50, image_size=640):
        # Starts the training process using the provided YAML configuration on the CPU.
        if not os.path.exists(data_config_path):
            raise FileNotFoundError(f"Configuration file not found: {data_config_path}")

        results = self.model.train(
            data=data_config_path,
            epochs=epochs_count,
            imgsz=image_size,
            project="ia/entrenamiento_resultados",
            name="modelo_microglias",
            device="cpu",
        )
        return results


if __name__ == "__main__":
    # Sets the global dataset directory to the current working directory.
    settings.update({"datasets_dir": os.getcwd()})

    # Specifies the relative path to the configuration file.
    yaml_config = "ia/dataset/data.yaml"

    trainer = ModelTrainer(base_model="yolov8n.pt")

    try:
        print("Initializing training sequence...")
        trainer.execute_training(data_config_path=yaml_config, epochs_count=100)
        print("Training sequence completed.")
    except Exception as e:
        print(f"A critical error occurred during training: {e}")
