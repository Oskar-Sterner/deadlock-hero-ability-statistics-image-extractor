from ultralytics import YOLO
from pathlib import Path

def main():
    """
    Trains a YOLOv8 model on the custom tooltip dataset.
    """
    # Load a pre-trained YOLOv8 model (yolov8n.pt is the smallest and fastest)
    model = YOLO('yolov8n.pt')

    # Get the path to the dataset configuration file
    config_path = Path(__file__).resolve().parent.parent.parent / 'tooltip_dataset.yaml'

    print(f"Starting training with dataset config: {config_path}")

    # Train the model
    # data: path to the .yaml file
    # epochs: how many times to go through the dataset (more is better, but takes longer)
    # imgsz: resize images to this size for training
    # device: 0 for GPU, 'cpu' for CPU
    results = model.train(
        data=str(config_path),
        epochs=50,
        imgsz=640,
        device='cpu'  # Use 0 for CUDA GPU, or 'cpu' if you don't have one
    )

    print("Training complete!")
    print("Model saved to the 'runs' directory.")

if __name__ == '__main__':
    main()