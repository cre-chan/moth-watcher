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