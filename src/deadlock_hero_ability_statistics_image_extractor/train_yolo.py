import argparse
from pathlib import Path

from ultralytics import YOLO

VALID_TASKS = {"abilities", "items"}


def default_dataset_yaml_for_task(task: str) -> Path:
    root = Path(__file__).resolve().parent.parent.parent
    if task == "items":
        return root / "tooltip_dataset_items.yaml"
    return root / "tooltip_dataset_abilities.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train YOLO tooltip segmentation model"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="abilities",
        choices=sorted(VALID_TASKS),
        help="Dataset/model task to train: abilities or items",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=None,
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
    parser.add_argument(
        "--run-name",
        type=str,
        default="train",
        help="YOLO run name under the selected task project directory",
    )
    return parser


def main():
    """
    Trains a YOLOv8 segmentation model on the custom tooltip dataset.
    """
    parser = build_parser()
    args = parser.parse_args()

    model = YOLO(args.model)

    config_path = args.data or default_dataset_yaml_for_task(args.task)
    project_path = Path("runs") / args.task / "segment"

    print("Starting YOLO segmentation training")
    print(f"Task: {args.task}")
    print(f"Base model: {args.model}")
    print(f"Dataset config: {config_path}")
    print(f"Run output project: {project_path}")
    print(f"Run output name: {args.run_name}")
    print(
        f"Training args: epochs={args.epochs}, imgsz={args.imgsz}, device={args.device}"
    )

    model.train(
        data=str(config_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        device=args.device,
        project=str(project_path),
        name=args.run_name,
    )

    print("Training complete!")
    print(
        f"Expected segmentation weights path: {project_path}/{args.run_name}/weights/best.pt"
    )


if __name__ == "__main__":
    main()