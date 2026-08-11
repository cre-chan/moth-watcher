# Watchmose

Watchmose is a Dev Container based prototype that monitors moth larvae from a GoPro video stream and estimates three probabilities:

- molting probability
- pupation probability
- hunger probability

When the estimated probability exceeds the configured threshold, the system sends an email alert.

## Prerequisites

- Docker Desktop with Dev Containers support
- A GoPro stream that is reachable from the container

## Development environment

1. Open this folder in VS Code.
2. Run "Dev Containers: Reopen in Container".
3. The container will install Python dependencies from `requirements.txt`.

## Configuration

The program loads settings from environment variables:

- `GOPRO_STREAM_URL`: RTSP/HTTP stream URL for the GoPro
- `FRAME_WIDTH`, `FRAME_HEIGHT`: frame resolution
- `SAMPLE_INTERVAL_SECONDS`: how often to sample frames
- `MOLTING_THRESHOLD`, `PUPATION_THRESHOLD`, `HUNGER_THRESHOLD`: alert thresholds
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TO`: SMTP settings for email alerts

## Run

```bash
python app/main.py
```

## Notes

- This is a prototype and uses a simple rule-based detector rather than a trained machine learning model.
- For a real deployment, replace the heuristic detector and estimator with a calibrated model trained on your own video data.

# How to run the unit tests
To run the unit tests, be sure you are at watchmose directory and run the following commands
```bash
python -m unittest discover -s tests
```
The command above runs all the tests.
```bash
python -m unittest discover -s tests [test1] [test2]
```
The command above runs the specified tests.