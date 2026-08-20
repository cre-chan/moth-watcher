# Watchmose

Watchmose is a Dev Container based prototype that monitors moth larvae from a GoPro video stream and estimates three probabilities:

- molting probability
- pupation probability
- hunger probability

When the estimated probability exceeds the configured threshold, the system sends an email alert.

# Quickstart
In this section, we will show how to run the watchmoth program.
## Prerequisites

- Docker 
    - you can download Docker from [here](https://www.docker.com/products/docker-desktop)
- A GoPro stream that is reachable from the container
    - Currently, we assume the GoPro is connected to the computer with HDMI
- Internet access for sending email alerts
- Python 3.13.5 final
    - you can download Python from [here](https://www.python.org/downloads/)
- Google account for sending email alerts
    - Currently, we use gmail to send alert emails only

## Preparation
First, you need to install the dependencies. We recommend installing in a virtual environment. You can create a virtual environment by running the following command:
```bash
python -m venv .venv
```

Then, activate the virtual environment by running the following command:    
```bash
source .venv/bin/activate
```

Finally, install the dependencies by running the following command:
```bash
pip install -r requirements.txt
```


Befor you run the program, you need to grant the application access to your Google account. You can do this by running the following command in your terminal:

```bash
python helpers/get_creds.py <path_to_client_secret.json>
```

Then, add the following environment variables to your system:

```bash
export GMAIL_TOKEN_PATH=<path_to_token.json>
export GMAIL_RECIPIENT=<recipient_email_address>
```

## Run

```bash
python app/main.py
```

# Development (For humans)
For development, we recommend using a virtual environment. You can create a virtual environment by running the following command:
First, you need to install the dependencies. We recommend installing in a virtual environment. You can create a virtual environment by running the following command:
```bash
python -m venv .venv
```

Then, activate the virtual environment by running the following command:    
```bash
source .venv/bin/activate
```

Finally, install the dependencies by running the following command:
```bash
pip install -r requirements.txt
```
## How to get ami dataset
The AMI dataset is available at [https://zenodo.org/records/12554005](https://zenodo.org/records/12554005). You can download the dataset and unzip it to `data/ami_dataset/`.

## How to run the unit tests
To run the unit tests, be sure you are at watchmose directory and run the following commands
```bash
python -m unittest discover -s tests
```
The command above runs all the tests.
```bash
python -m unittest discover -s tests [test1] [test2]
```
The command above runs the specified tests.

## How to run full YOLOv8 training on AMI dataset
`train_YOLOv8_model()` is implemented in [helper/models.py](/Users/duoxu/Desktop/watchmose/helper/models.py) and trains a 1-class detector (`moth`) from `data/ami_dataset/ami_traps/camera_trap_images`.

> Note: Use Python 3.11 virtual environment for training (ultralytics/torch dependency).

1. Run full training:
```bash
python helper/models.py
```
The command runs the training with the following parameters:
```
train_YOLOv8_model(output_root='models/ami_yolov8', run_name='full_train', epochs=100, imgsz=640, batch=16, val_ratio=0.2, random_seed=42);
```

2. Run only `test_models.py` using the trained model:
```bash
export YOLOV8_MODEL_PATH=/absolute/path/to/models/ami_yolov8/full_train/weights/best.pt 
python -m unittest discover -v tests -p test_models.py
```

> Note: Currently, the warning is expected on Macbook Air
> [W NNPACK.cpp:64] Could not initialize NNPACK! Reason: Unsupported hardware.
>..

# Instructions for AI
For AI developers, you must run all your commands in a virtual environment. You can create a virtual environment by running the following command:
```bash
python -m venv .venv
```

Then, activate the virtual environment by running the following command:    
```bash
source .venv/bin/activate
```

If necessary, install the dependencies by running the following command:
```bash
pip install -r requirements.txt
```

When you introduce new dependencies, please add them to requirements.txt and run the following command to update the virtual environment:
```bash
pip install -r requirements.txt
```