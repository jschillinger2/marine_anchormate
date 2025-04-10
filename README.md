# Marine Anchormate Controller

This project is an experimental solution designed to interface with Signal K servers for controlling anchor windlass systems through a FireBeetle controller, enhanced with a Python-based application for extended functionalities. The hardware code is <a href="https://github.com/jschillinger2/marine_anchormate_esp">here</a>

## Features

- **Signal K Integration**: Authenticate and communicate with Signal K servers to receive and send data related to the anchoring system.
- **WebSocket Communication**: Real-time data exchange with the Signal K server for up-to-date control and monitoring.
- **Rotations Count Monitoring**: Listen for and process windlass rotation count data from Signal K, enabling precise control over the anchoring process.
- **REST API & React UI**: A responsive browser interface built with React for full manual/auto control, calibration, and real-time status monitoring.
- **Directional Control**: Manage anchoring operations with defined UP, DOWN, and NONE directions for movement control.

## Disclaimer

This software is provided "as is", without warranty of any kind, express or implied. I take no responsibility for its use or the outcomes of its operation. It is considered experimental and should be used with caution.

## Installation

Refer to [Marine Anchormate ESP](https://github.com/jschillinger2/marine_anchormate_esp?tab=readme-ov-file) for initial setup instructions and hardware requirements.

### Software Requirements

- Python 3.x
- Requests and Websocket-client libraries
- Flask & Flask-CORS (for REST API)
- Node.js & npm (for React UI)

### Setup

1. Clone this repository to your local machine.
2. Install required Python packages:
   ```bash
   pip install flask flask-cors requests websocket-client
   ```
3. Adjust `anchormate.properties` configuration as per your Signal K server and hardware setup.
4. Run the Python backend with:
   ```bash
   python anchormate.py
   ```

### React UI (Web Interface)

To build and deploy the web UI:

1. Go into the React subfolder:
   ```bash
   cd anchormate-webui
   ```
2. Install the frontend dependencies:
   ```bash
   npm install
   ```
3. Build the frontend:
   ```bash
   npm run build
   ```
4. The output will go into `anchormate-webui/build`, which is automatically served by the Flask app.

Once the backend is running, open a browser at `http://<your-device-ip>:5000` to access the UI.

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

These settings allow for a high degree of customization and should be adjusted according to the specifics of your hardware setup and operational preferences.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, features, or improvements.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
