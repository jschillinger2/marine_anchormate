# marine_anchormate

Anchor control to run on Raspberry Pi. 

# Install

## Install Linux packages

```
apt install python3
apt install xclip
apt install festival
```

## Setup Python

Suggest to set up virtual environment in your target folder.

```
python3 -m venv path/to/venv
```

## Install Python libaries

```
pip3 install gpiozero
pip3 install pigame
pip3 install https://github.com/kivymd/KivyMD/archive/master.zip
```

# Run

You can just execute anchormate.py.

```
python3 anchormate.py
```


# AnchorMate Configuration

AnchorMate is designed with customization in mind, allowing users to tailor the application to their specific needs through various settings. Below are the available configuration options:

## Settings

### `SIMULATED`
- **Description**: Switch to `TRUE` if you don't want to call the IO ports (for testing purposes). This is useful for running the application in an environment where the actual hardware is not available or when you wish to simulate hardware interactions.
- **Default Value**: `True`

### `DEBUG`
- **Description**: Turn this on if you want to see debug information on the screen. It helps in troubleshooting and understanding the flow of operations within the application.
- **Default Value**: `True`

### `CHAIN_LENGTH`
- **Description**: Defines the total chain length in meters. This setting is crucial for calculating how much of the chain has been deployed or needs to be retracted.
- **Default Value**: `20`

### `LENGTH_PER_ROTATION`
- **Description**: Indicates how many meters the chain moves for 1 rotation of the mechanism. This ratio is essential for accurately tracking the chain's movement.
- **Default Value**: `0.25`

### `MIN_DEPTH`
- **Description**: Sets the minimum length to pull the anchor up, allowing the user to do the rest manually. This feature ensures that the system does not need to fully retract the anchor, saving time and effort in shallow waters.
- **Default Value**: `2`

### `PIN_ANCHOR_UP`
- **Description**: GPIO pin number used to trigger the anchor's upward movement. This pin interfaces with the hardware responsible for retracting the anchor.
- **Default Value**: `17`

### `PIN_ANCHOR_DOWN`
- **Description**: GPIO pin number used to initiate the anchor's downward deployment. It signals the hardware mechanism to release the anchor for setting.
- **Default Value**: `18`

### `PIN_ROTATION_INDICATOR`
- **Description**: GPIO pin number connected to the device that indicates the rotation of the anchor mechanism. This pin is used to monitor the movement and calculate the chain's deployed length.
- **Default Value**: `19`

These settings allow for a high degree of customization and should be adjusted according to the specifics of your hardware setup and operational preferences.
