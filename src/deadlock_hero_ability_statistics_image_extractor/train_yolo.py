import argparse
from pathlib import Path

from ultralytics import YOLO


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train YOLO tooltip segmentation model"
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "tooltip_dataset.yaml",
        help="Path to YOLO dataset yaml file",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="yolov8n-seg.pt",
        help="Base YOLO model weights",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Training image size",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Training device (e.g. cpu, 0)",
    )
    return parser


def main():
    """
    Trains a YOLOv8 segmentation model on the custom tooltip dataset.
    """
    parser = build_parser()
    args = parser.parse_args()

    model = YOLO(args.model)

    config_path = args.data

    print("Starting YOLO segmentation training")
    print(f"Base model: {args.model}")
    print(f"Dataset config: {config_path}")
    print(
        f"Training args: epochs={args.epochs}, imgsz={args.imgsz}, device={args.device}"
    )

    model.train(
        data=str(config_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        device=args.device,
    )

    print("Training complete!")
    print("Expected segmentation weights path: runs/segment/train/weights/best.pt")


if __name__ == "__main__":
    main()