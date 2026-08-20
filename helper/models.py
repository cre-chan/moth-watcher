from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

# ultralytics is available for Python < 3.13
from ultralytics import YOLO

def convert_label_file(src: Path, dst: Path) -> None:
        converted_lines: list[str] = []
        with src.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) != 5:
                    raise ValueError(f"Unexpected YOLO label format in {src}: {line}")
                # class id を1クラス検出として 0 に統一
                converted_lines.append(f"0 {' '.join(parts[1:])}")
        dst.write_text("\n".join(converted_lines), encoding="utf-8")

def train_YOLOv8_model(
    dataset_root: str = "data/ami_dataset/ami_traps/camera_trap_images",
    output_root: str = "models/ami_yolov8",
    run_name: str = "moth_one_class",
    val_ratio: float = 0.2,
    random_seed: int = 42,
    epochs: int = 20,
    imgsz: int = 640,
    batch: int = 16,
    max_samples: int | None = None,
) -> str:
    """
    AMI datasetの既存YOLOラベルを1クラス(moth)に統合してYOLOv8を学習する。

    returns:
        best.pt の絶対パス
    """
    if not (0.0 < val_ratio < 1.0):
        raise ValueError(f"val_ratio must be between 0 and 1. got: {val_ratio}")

    dataset_path = Path(dataset_root).resolve()
    images_dir = dataset_path / "images"
    labels_dir = dataset_path / "labels"
    if not images_dir.is_dir():
        raise FileNotFoundError(f"AMI image directory not found: {images_dir}")
    if not labels_dir.is_dir():
        raise FileNotFoundError(f"AMI label directory not found: {labels_dir}")

    image_paths = sorted(
        p for p in images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not image_paths:
        raise RuntimeError(f"No images found under {images_dir}")

    paired_samples: list[tuple[Path, Path]] = []
    for image_path in image_paths:
        label_path = labels_dir / f"{image_path.stem}.txt"
        if label_path.is_file():
            paired_samples.append((image_path, label_path))

    if len(paired_samples) < 2:
        raise RuntimeError("Need at least 2 image/label pairs to train and validate.")

    # サンプルをランダムにシャッフルしてmax_samplesまで件数を制限する
    random.Random(random_seed).shuffle(paired_samples)
    if max_samples is not None:
        paired_samples = paired_samples[:max_samples]

    # サンプルを学習用と検証用に分割する
    split_index = int(len(paired_samples) * (1.0 - val_ratio))
    if split_index <= 0:
        split_index = 1
    if split_index >= len(paired_samples):
        split_index = len(paired_samples) - 1

    train_samples = paired_samples[:split_index]
    val_samples = paired_samples[split_index:]
    if not train_samples or not val_samples:
        raise RuntimeError("train/val split failed. Adjust val_ratio or sample size.")

    prepared_root = Path(output_root).resolve() / "prepared_dataset"
    if prepared_root.exists():
        shutil.rmtree(prepared_root)

    train_img_dir = prepared_root / "images" / "train"
    val_img_dir = prepared_root / "images" / "val"
    train_lbl_dir = prepared_root / "labels" / "train"
    val_lbl_dir = prepared_root / "labels" / "val"
    for d in (train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir):
        d.mkdir(parents=True, exist_ok=True)

    for image_path, label_path in train_samples:
        shutil.copy2(image_path, train_img_dir / image_path.name)
        convert_label_file(label_path, train_lbl_dir / label_path.name)
    for image_path, label_path in val_samples:
        shutil.copy2(image_path, val_img_dir / image_path.name)
        convert_label_file(label_path, val_lbl_dir / label_path.name)

    data_yaml_path = prepared_root / "ami_moth_one_class.yaml"
    data_yaml_path.write_text(
        "\n".join(
            [
                f"path: {prepared_root.as_posix()}",
                "train: images/train",
                "val: images/val",
                "names:",
                "  0: moth",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    project_dir = Path(output_root).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    model = YOLO("yolov8n.pt")
    train_results = model.train(
        data=str(data_yaml_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project=str(project_dir),
        name=run_name,
        exist_ok=True,
        seed=random_seed,
    )

    best_model_path = Path(train_results.save_dir) / "weights" / "best.pt"
    if not best_model_path.is_file():
        raise RuntimeError(f"Training finished but best.pt was not found: {best_model_path}")
    return str(best_model_path.resolve())

if __name__ == "__main__":
    best_model = train_YOLOv8_model(
        output_root='models/ami_yolov8', 
        run_name='full_train', 
        epochs=100, 
        imgsz=640, 
        batch=16, 
        val_ratio=0.2, 
        random_seed=42)
    print(f"Best model saved at: {best_model}")