# Marine Anchormate Controller

This project is an experimental solution designed to interface with Signal K servers for controlling anchor windlass systems through a FireBeetle controller, enhanced with a Python-based application and React UI for extended functionalities. The hardware code is [here](https://github.com/jschillinger2/marine_anchormate_esp).

## Features

- **Signal K Integration**: Authenticate and communicate with Signal K servers to receive and send data related to the anchoring system.
- **WebSocket Communication**: Real-time data exchange with the Signal K server for up-to-date control and monitoring.
- **Rotations Count Monitoring**: Process windlass rotation count data from Signal K, enabling precise anchor tracking.
- **REST API & React UI**: A responsive web interface built with React for full manual/auto control, calibration, and real-time status.
- **Safety Features**: Heartbeat monitoring ensures auto processes are stopped if the UI disconnects.

## Disclaimer

This software is provided "as is", without warranty of any kind. It is experimental and should be used with caution.

## Installation

Refer to the [Marine Anchormate ESP](https://github.com/jschillinger2/marine_anchormate_esp?tab=readme-ov-file) for hardware setup.

### Software Requirements

- Python 3.x
- Flask + Flask-CORS
- websocket-client, requests
- Node.js & npm (for React UI)

### Setup

1. Clone this repository to your device.
2. Install Python dependencies:
   ```bash
   pip install flask flask-cors websocket-client requests
   ```
3. Update the `anchormate.properties` file with your hardware and Signal K server settings.
4. Run the backend:
   ```bash
   python anchormate.py
   ```
   The backend runs on port `5000` by default.

### React UI (Web Interface)

1. Navigate to the web UI subfolder:
   ```bash
   cd anchormate-webui
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Build the production version:
   ```bash
   npm run build
   ```
4. Ensure that the resulting `build/` folder remains in `anchormate-webui/`. This is used by the Python backend.

Once running, access the UI at: `http://<your-device-ip>:5000`

## Settings (`anchormate.properties`)

### `SIMULATED`
- Simulate regular rotation pulses for testing.
- Default: `True`

### `DEBUG`
- Show debug info in the backend.
- Default: `True`

### `CHAIN_LENGTH`
- Total chain length in meters.
- Default: e.g. `19`

### `LENGTH_PER_ROTATION`
- How many meters of chain per one rotation.
- Example: `0.25`

### `MIN_DEPTH`
- Minimum safe depth before requiring manual intervention.

### `SIGNALK_SERVER_URL`, `SIGNALK_SERVER_USER`, `SIGNALK_SERVER_PASSWORD`
- Credentials for authenticating with your Signal K server.

### `HOSTNAME`
- The IP address shown in the QR code for mobile access.
- Example: `10.10.7.16`

## QR Code and Touchscreen

- The QR code in the UI will show the hostname defined in `anchormate.properties`, allowing quick mobile access.
- Buttons support **long press** and are sized for touchscreen use.
- Context menus are disabled to avoid accidental popups on long press.
