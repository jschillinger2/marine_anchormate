import subprocess
import time
import requests
import websocket
import json
import threading
from enum import Enum
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import subprocess
import time
import requests
import websocket
import json
import threading
import socket
import os
import sys
from threading import Event
from enum import Enum
from time import sleep
from threading import Thread


# Absolute path to React build folder
REACT_BUILD_DIR = os.path.join(os.path.dirname(__file__), "anchormate-webui", "build")

# Raise error immediately if build folder is missing
if not os.path.exists(REACT_BUILD_DIR):
    raise FileNotFoundError(f"React build folder not found: {REACT_BUILD_DIR}")

# Initialize Flask app
app = Flask(__name__, static_folder=REACT_BUILD_DIR, static_url_path="")
CORS(app)

class Direction(Enum):
    UP = 1
    DOWN = 2
    NONE = 3

class AnchorMate:

    # Function to get local IP address for UI access

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"

    def read_properties_file(filepath):
        properties = {}
        with open(filepath, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):  # ignore comments and empty lines
                    key, value = line.split('=', 1)
                    properties[key.strip()] = value.strip()
        return properties


    PROPERTIES_FILE_PATH = 'anchormate.properties'  # Adjust the path as needed
    config = read_properties_file(PROPERTIES_FILE_PATH)
    
    SIMULATED = config.get('SIMULATED') == 'True'

    SIGNALK_SERVER_URL = config.get('SIGNALK_SERVER_URL')
    SIGNALK_SERVER_USER = config.get('SIGNALK_SERVER_USER')
    SIGNALK_SERVER_PASSWORD = config.get('SIGNALK_SERVER_PASSWORD')
    
    # switch on if you want to see debug info on the screen
    DEBUG = config.get('DEBUG') == 'True'
    
    # chain length in meter
    CHAIN_LENGTH=float(config.get('CHAIN_LENGTH', 0))

    # how many meters does the chain move for 1 rotation
    LENGTH_PER_ROTATION = float(config.get('LENGTH_PER_ROTATION', 0))

    # minimum length to pull the anchor up, allow user to do the rest manual
    MIN_DEPTH = float(config.get('MIN_DEPTH', 0))
    
    # the direction of the anchor movement
    current_direction = Direction.NONE
    
    # current depth of anchor
    current_depth = 0

    # last rotation count received from Signal K
    rotations_value_last=0
    
    # target depth chosen in auto mode
    target_depth = 0
    
    # set in automode if the cancel button is pushed
    auto_cancel=False
    auto_in_progress = False

    debug_msg = "debug text"
    debug_pinstate_down = False
    debug_pinstate_up = False
    debug_pinstate_pulse = False

    # signalk auth token
    token = ""
    
    ws = 0

    def authenticate_signal_k(self, server_url, username, password, version='v1'):
        """
        Authenticate with a Signal K server and extract the authentication token.

        :param server_url: Base URL of the Signal K server (e.g., 'http://localhost:3000').
        :param username: Username for authentication.
        :param password: Password for authentication.
        :param version: Version of the Signal K API to use (default is 'v1').
        :return: The authentication token if successful, None otherwise.
        """

        login_url = f"{server_url}/signalk/{version}/auth/login"
        print (f"Auth Login URL {login_url}; User: {username}; Password: {password}")
        payload = {
            "username": username,
            "password": password
        }
        headers = {
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(login_url, json=payload, headers=headers)
            response.raise_for_status()  # Raises stored HTTPError, if one occurred.

            # Extract token from response
            token_info = response.json()
            return token_info.get('token', None)
        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")  # HTTP error
        except Exception as err:
            print(f"An error occurred: {err}")  # Other errors

        return None

    last_ui_heartbeat_time = time.time()
    
    def __init__(self, **kwargs):

        super(AnchorMate, self).__init__(**kwargs)
        
        if self.SIMULATED:
            print("Starting simulated rotation pulses")
            self.schedule_simulated_pulses()

        # show local ip
        print(f"IP for QR code: {self.get_local_ip()}");
            
        # authenticate with signal K
        self.token = self.authenticate_signal_k(f"http://{self.SIGNALK_SERVER_URL}", self.SIGNALK_SERVER_USER, self.SIGNALK_SERVER_PASSWORD);
        print(f"Signal K Auth Token: {self.token}")
        
        # Initialize the debug message
        self.update_debug_msg()

        Thread(target=self.run_signalk_websocket).start()
        Thread(target=self.monitor_ui_heartbeat_timeout, daemon=True).start()

    def monitor_ui_heartbeat_timeout(self):
        while True:
            time.sleep(0.5)
            if self.auto_in_progress:
                if time.time() - self.last_ui_heartbeat_time > 1.0:
                    print("No UI heartbeat received in >1s, stopping auto.")
                    self.auto_stop()
        
    def run_signalk_websocket(self):
        ws_address = f"ws://{self.SIGNALK_SERVER_URL}/signalk/v1/stream?token={self.token}"
        print(f"Signal K Websocket URL: {ws_address}")
        self.ws = websocket.WebSocketApp(ws_address,on_open=self.on_ws_open,
                        on_message=self.on_ws_message,
                        on_error=self.on_ws_error,
                        on_close=self.on_ws_close)
        self.ws.run_forever()

    def on_websocket_close(self):        
        self.ws = websocket.WebSocketApp(ws_address, on_close=on_websocket_close)
     
    def man_anchor_down_press(self):
        print("Anchor Down Start")
        self.current_direction = Direction.DOWN
        self.command_down_on()

    def man_anchor_down_release(self):
        print("Anchor Stop")
        self.current_direction = Direction.NONE
        self.command_all_off()        

    def man_anchor_up_press(self):
        print("Anchor Up Start")
        self.current_direction = Direction.UP
        self.command_up_on()

    def man_anchor_up_release(self):
        print("Anchor Stop")
        self.current_direction = Direction.NONE
        self.command_all_off()         

    def auto_go(self):
        self.auto_cancel=False
        distancetomove = self.target_depth - self.current_depth
        print(f"Auto Adjust Start. Moving {distancetomove} meters")
        Thread(target=self.auto_go_process, args=(distancetomove,)).start()

    def auto_go_process(self, delta):
        self.auto_in_progress = True
        if delta > 0:
            self.man_anchor_down_press()
            while (self.current_depth<self.target_depth) and not self.auto_cancel:
                time.sleep(0.1)
            self.man_anchor_down_release()
        else:
            self.man_anchor_up_press()
            while self.current_depth>self.target_depth and self.current_depth>self.MIN_DEPTH and not self.auto_cancel:
                print( self.current_depth)
                print( self.target_depth)
                time.sleep(0.1)
            self.man_anchor_up_release()
        self.auto_in_progress = False
        
    def auto_stop(self):
        print("Auto Adjust Stop")
        self.auto_cancel = True
        self.command_all_off();
        
    def calib(self, depth):
        print(f"Anchor-calib set at {depth}")
        self.current_depth = depth

    def command_down_on(self):
        self.command_all_off();
        self.debug_pinstate_down = True;
        self.send_value_to_signal_k();

    def command_all_off(self):
        self.debug_pinstate_up = False;
        self.debug_pinstate_down = False;
        self.send_value_to_signal_k();
        
    def command_up_on(self):
        self.command_all_off();
        self.debug_pinstate_up = True
        self.send_value_to_signal_k();
        
    # called by time in simulation mode to simulate pulse from rotation
    def on_pulse_simulated_pressed(self, a):
       self.on_pulse_on()
       print("Simulated Rotation")
       time.sleep(0.1)
       self.on_pulse_off()

    def schedule_simulated_pulses(self):
        def loop():
            while True:
                self.on_pulse_simulated_pressed(self)
                time.sleep(2)
        threading.Thread(target=loop, daemon=True).start()
     
    # Define a function to be called whenever the rotation pulse is triggered
    def on_pulse_on(self):
        #global current_depth
        print(f"Pulse detected! Current Depth: {self.current_depth}")
        self.debug_pinstate_pulse = True
        if self.current_direction == Direction.UP:
            self.current_depth -= self.LENGTH_PER_ROTATION
        elif self.current_direction == Direction.DOWN:
            self.current_depth += self.LENGTH_PER_ROTATION
        else:
            print("Anchor moving despite no engine")

    def on_pulse_off(self):
        print(f"Pulse release detected!")
        self.debug_pinstate_pulse = False

  
    def update_debug_msg(self, *args):
        # Update debug_msg to reflect the current state of the BooleanProperties
        if self.DEBUG:
            self.debug_msg = f"U:{self.debug_pinstate_up}, D:{self.debug_pinstate_down}, P:{self.debug_pinstate_pulse}"
        else:
            self.debug_msg = ""

    def send_value_to_signal_k(self, *args):
        path_control = 'vessels.self.anchor.control'
        path_current_depth = 'vessels.self.anchor.state.current_depth'
        
        value = 'OFF'
        if self.debug_pinstate_up:
            value = 'UP'
        if self.debug_pinstate_down:
            value = 'DOWN'
       
        data = {
            "context": "vessels.self",  
            "updates": [
                {
                    "source": {
                        "label": "anchormate" 
                    },
                    "values": [
                        {
                            "path": path_control,
                            "value": value
                        },
                        {
                            "path": path_current_depth,
                            "value": self.current_depth
                        }
                    ]
                }
            ]
        }

        if hasattr(self.ws, 'open') and self.ws.open:
            self.ws.send(json.dumps(data))
            print(f"Message sent{json.dumps(data)}")
        else:
            print("WebSocket connection is not open")

    def on_ws_open(self,ws):
        print("Connection opened")
        self.ws.open = True  # Set a custom attribute to track the connection state
        self.start_heartbeat()

    def start_heartbeat(self):
        self.send_heartbeat()  # Initial call to start the heartbeat process

    def send_heartbeat(self):

        path_control = 'vessels.self.anchor.control.heartbeat'
        value = time.time()

        data = {
            "context": "vessels.self",  
            "updates": [
                {
                    "source": {
                        "label": "anchormate" 
                    },
                    "values": [
                        {
                            "path": path_control,
                            "value": value
                        }
                    ]
                }
            ]
        }            

        if hasattr(self.ws, 'open') and self.ws.open:
            self.ws.send(json.dumps(data))
        else:
            print("WebSocket connection is not open")
            self.token = self.authenticate_signal_k(f"http://{self.SIGNALK_SERVER_URL}", self.SIGNALK_SERVER_USER, self.SIGNALK_SERVER_PASSWORD);
            self.run_signalk_websocket();
                   
        # Schedule the next heartbeat
        self.heartbeat_timer = threading.Timer(0.25, self.send_heartbeat)  # Send heartbeat
        self.heartbeat_timer.start()    

    def on_ws_message(self,ws, message):
        # print("Received message:", message)
        data = json.loads(message)
        
        # Initialize a variable to hold the rotations value
        rotations_value = None

        # Extract the rotations value
        for update in data.get("updates", []):
            for value in update.get("values", []):
                if value.get("path") == "sensors.windlass.rotations":
                    rotations_value = value.get("value")
                    break  # Stop searching once we find the rotations value

        # Check if we found a rotations value and print it
        if rotations_value is not None:
            print(f"Rotations value: {rotations_value}")
            if rotations_value > self.rotations_value_last:
                self.on_pulse_on()
            self.rotations_value_last = rotations_value
        # else:
            # print("Rotations value not found.")

    def on_ws_error(self,ws, error):
        print("Error:", error)

    def on_ws_close(self,ws,a,b):
        print("Connection closed. Trying to reconnect. ")
        self.ws.open = False  # Update the connection state
        self.token = self.authenticate_signal_k(f"http://{self.SIGNALK_SERVER_URL}", self.SIGNALK_SERVER_USER, self.SIGNALK_SERVER_PASSWORD);
        self.run_signalk_websocket();
        
    def on_stop(self):
        # This method is called when the application is about to stop
        self.current_direction = Direction.NONE
        self.command_all_off() 
        self.send_value_to_signal_k();
        if self.ws:
            self.ws.close()  # Close the WebSocket connection
            print("WebSocket connection closed")
            


    

anchor = AnchorMate()

# REST API endpoints
@app.route("/api/manual", methods=["POST"])
def manual():
    direction = request.json.get("direction")
    if direction in ["DOWN"]:
        anchor.man_anchor_down_press()
    if direction in ["UP"]:
        anchor.man_anchor_up_press()
    elif direction == "STOP":
        anchor.man_anchor_down_release()
    return jsonify({"status": "ok"})

@app.route("/api/auto", methods=["POST"])
def auto():
    action = request.json.get("action")
    if action == "START":
        target = request.json.get("targetDepth")
        anchor.target_depth = target
        anchor.auto_go()
    elif action == "STOP":
        anchor.auto_stop()
    return jsonify({"status": "ok"})

@app.route("/api/calibrate", methods=["POST"])
def calibrate():
    depth = request.json.get("depth")
    anchor.calib(depth)
    return jsonify({"status": "ok"})

@app.route("/api/depth", methods=["GET"])
def get_depth():
    return jsonify({"depth": anchor.current_depth})

@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    anchor.last_ui_heartbeat_time = time.time()
    return jsonify({"status": "alive"})

@app.route("/api/status", methods=["GET"])
def get_status():
    return jsonify({"autoRunning": anchor.auto_in_progress})

@app.route("/api/info", methods=["GET"])
def get_info():
    return jsonify({
        "host": anchor.get_local_ip(),
        "chainLength": anchor.CHAIN_LENGTH
    })

# Serve React frontend
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    file_path = os.path.join(REACT_BUILD_DIR, path)
    if path != "" and os.path.exists(file_path):
        return send_from_directory(REACT_BUILD_DIR, path)
    else:
        index_path = os.path.join(REACT_BUILD_DIR, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(REACT_BUILD_DIR, "index.html")
        else:
            abort(500, description="index.html not found in React build folder")


    
# Start server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
