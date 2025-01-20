import subprocess
import pygame
import time
import requests
import websocket
import json
import threading
import socket
import os
import sys
from kivy.clock import Clock
from enum import Enum
from gpiozero import Button
from gpiozero import OutputDevice
from time import sleep
from kivy.properties import NumericProperty
from kivy.properties import StringProperty
from kivy.properties import BooleanProperty
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from threading import Thread

class ConfigScreen(MDScreen):
    image_size = StringProperty()

class ManualScreen(MDScreen):
    image_size = StringProperty()

class AutoScreen(MDScreen):
    image_size = StringProperty()

class Direction(Enum):
    UP = 1
    DOWN = 2
    NONE = 3

class AnchorMate(MDApp):
        
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
    
    IOPINS = config.get('IOPINS') == 'True'
    
    # switch on if you want to see debug info on the screen
    DEBUG = config.get('DEBUG') == 'True'

    # path to ding sound
    SOUND_DING_PATH = "res/sounds/ding.mp3"
    
    # chain length in meter
    CHAIN_LENGTH=float(config.get('CHAIN_LENGTH', 0))

    # how many meters does the chain move for 1 rotation
    LENGTH_PER_ROTATION = float(config.get('LENGTH_PER_ROTATION', 0))

    # minimum length to pull the anchor up, allow user to do the rest manual
    MIN_DEPTH = float(config.get('MIN_DEPTH', 0))
    
    # PINS
    PIN_ANCHOR_UP = int(config.get('PIN_ANCHOR_UP', 0))
    PIN_ANCHOR_DOWN = int(config.get('PIN_ANCHOR_DOWN', 0))
    PIN_ROTATION_INDICATOR = int(config.get('PIN_ROTATION_INDICATOR', 0))

    # the direction of the anchor movement
    current_direction = Direction.NONE
    
    # current depth of anchor
    current_depth = NumericProperty(0)
    last_current_depth = -1

    # last rotation count received from Signal K
    rotations_value_last=0
    
    # target depth chosen in auto mode
    target_depth = NumericProperty(0)

    # set in automode if the cancel button is pushed
    auto_cancel=False
    auto_in_progress = BooleanProperty(False)

    debug_msg = StringProperty("debug text")
    debug_pinstate_down = BooleanProperty(False)
    debug_pinstate_up = BooleanProperty(False)
    debug_pinstate_pulse = BooleanProperty(False)

    # signalk auth token
    token = ""
    
    # ios
    print(IOPINS)
    io_anchor_up = None if not IOPINS else OutputDevice(PIN_ANCHOR_UP)
    io_anchor_down = None if not IOPINS else OutputDevice(PIN_ANCHOR_DOWN)

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
    
    def __init__(self, **kwargs):

        super(AnchorMate, self).__init__(**kwargs)
        
        # Set listeners for each BooleanProperty
        self.bind(debug_pinstate_up=self.update_debug_msg)
        self.bind(debug_pinstate_down=self.update_debug_msg)
        self.bind(debug_pinstate_pulse=self.update_debug_msg)
        self.bind(debug_pinstate_up=self.send_value_to_signal_k)
        self.bind(debug_pinstate_down=self.send_value_to_signal_k)
        
        # Set listeners to current depth to trigger TTS
        self.bind(current_depth=self.update_depth_tts)
        self.bind(current_depth=self.send_value_to_signal_k)

        # authenticate with signal K
        self.token = self.authenticate_signal_k(f"http://{self.SIGNALK_SERVER_URL}", self.SIGNALK_SERVER_USER, self.SIGNALK_SERVER_PASSWORD);
        print(f"Signal K Auth Token: {self.token}")
        
        # Initialize the debug message
        self.update_debug_msg()

        # setup heartbeat
        # self.send_heartbeat()

        # set timer to simulate anchor pulse
        if self.SIMULATED:
            Clock.schedule_interval(self.on_pulse_simulated_pressed, 2)   
        self.speak("Anchor Control is ready")
        Thread(target=self.run_signalk_websocket).start()
        
    def run_signalk_websocket(self):
        ws_address = f"ws://{self.SIGNALK_SERVER_URL}/signalk/v1/stream?token={self.token}"
        print(f"Signal K Websocket URL: {ws_address}")
        self.ws = websocket.WebSocketApp(ws_address,on_open=self.on_ws_open,
                            on_message=self.on_ws_message,
                            on_error=self.on_ws_error,
                            on_close=self.on_ws_close)
        #Window.bind(on_request_close=MyApp().on_request_close)
        self.ws.run_forever()

    def on_websocket_close(self):
        
        self.ws = websocket.WebSocketApp(ws_address, on_close=on_websocket_close)
        
    def update_depth_tts(self,a,b):
        if int(self.current_depth) != int(self.last_current_depth):
            self.speak(f"{round(self.current_depth)} meters")
        self.last_current_depth = self.current_depth
        
    def build(self):        
        self.theme_cls.primary_palette = "Blue" 
        Builder.load_file('anchormate.kv')

    def man_anchor_down_press(self):
        print("Anchor Down Start")
        self.current_direction = Direction.DOWN
        self.io_pin_down_on()

    def man_anchor_down_release(self):
        print("Anchor Stop")
        self.current_direction = Direction.NONE
        self.io_pin_all_off()        

    def man_anchor_up_press(self):
        print("Anchor Up Start")
        self.current_direction = Direction.UP
        self.io_pin_up_on()

    def man_anchor_up_release(self):
        print("Anchor Stop")
        self.current_direction = Direction.NONE
        self.io_pin_all_off()         

    def auto_slider_move(self, value):
        self.target_depth = self.CHAIN_LENGTH-value

    def auto_go(self):
        self.auto_cancel=False
        distancetomove = self.target_depth - self.current_depth
        print(f"Auto Adjust Start. Moving {distancetomove} meters")
        self.speak("Adjusting anchor height. Press Stop to cancel.")
        Thread(target=self.auto_go_process, args=(distancetomove,)).start()

    def auto_go_process(self, delta):
        self.auto_in_progress = True
        if delta > 0:
            self.man_anchor_down_press()
            while (self.current_depth<self.target_depth) and not self.auto_cancel:
                time.sleep(0.1)
            self.man_anchor_down_release()
            if not self.auto_cancel:
                self.speak("Anchor is at target depth")
            else:
                self.speak("Anchor adjustment cancelled")
        else:
            # print("xx")
            self.man_anchor_up_press()
            while self.current_depth>self.target_depth and self.current_depth>self.MIN_DEPTH and not self.auto_cancel:
                print( self.current_depth)
                print( self.target_depth)
                time.sleep(0.1)
            self.man_anchor_up_release()
            if not self.auto_cancel:
                if self.target_depth<self.MIN_DEPTH:
                    self.speak("Anchor is at minimum depth. Use manual for the rest.")
                else:    
                    self.speak("Anchor is at target depth")
            else:
                self.speak("Anchor adjustment cancelled")
        self.auto_in_progress = False
        
    def auto_stop(self):
        print("Auto Adjust Stop")
        self.auto_cancel = True
        self.speak("Anchor adjustment cancelled")
        
    def calib_top(self):
        self.speak("Anchor calibrated")
        print("Anchor-calib set at top")
        self.current_depth = 0

    def calib_bottom(self):
        print("Anchor-calib set at botton")
        self.speak("Anchor calibrated")
        self.current_depth = self.CHAIN_LENGTH

    def io_pin_down_on(self):
        self.io_pin_all_off()
        self.debug_pinstate_down = True
        if self.IOPINS:
            self.io_anchor_down.on()

    def io_pin_all_off(self):
        self.debug_pinstate_up = False
        self.debug_pinstate_down = False        
        if self.IOPINS:
            self.io_anchor_down.off()
            self.io_anchor_up.off()

    def io_pin_up_on(self):
        self.io_pin_all_off()
        self.debug_pinstate_up = True
        if self.IOPINS:
            self.io_anchor_up.on()

    # called by time in simulation mode to simulate pulse from rotation
    def on_pulse_simulated_pressed(self, a):
       self.on_pulse_on()
       Clock.schedule_once(self.on_pulse_simulated_release, 0.5)
       
    def on_pulse_simulated_release(self, a):
       self.on_pulse_off()
     
    # Define a function to be called whenever the pin goes from LOW to HIGH
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
        self.play_ding()

    def on_pulse_off(self):
        print(f"Pulse release detected!")
        self.debug_pinstate_pulse = False
        
    # Setup the pin as a 'Button', treat rising edges as button presses
    # The 'bounce_time' parameter is optional and can be adjusted based on your needs
    pulse_detector =  None if not IOPINS else Button(PIN_ROTATION_INDICATOR, pull_up=None, bounce_time=0.05)

    # Attach the event handler function to be called on rising edges
    if IOPINS: pulse_detector.when_pressed = on_pulse_on(self)
    if IOPINS: pulse_detector.when_released = on_pulse_off(self)
    
    def speak_process(self, text):
        try:
            # The command to execute Festival and send text to it
            command = f'echo "{text}" | festival --tts'
            # Execute the command
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")

    def speak(self, text):
        Thread(target=self.speak_process, args=(text,)).start()

    def play_mp3(self, path_to_mp3):
        # Initialize pygame mixer
        pygame.mixer.init()

        # Load the MP3 music file
        pygame.mixer.music.load(path_to_mp3)

        # Play the music
        pygame.mixer.music.play()

        # Wait for the music to play. Without this, the script may end and stop the music.
        while pygame.mixer.music.get_busy():
            time.sleep(1)

    # plays a ding sound
    def play_ding(self):
        Thread(target=self.play_mp3, args=(self.SOUND_DING_PATH,)).start()
        # self.play_mp3(self.SOUND_DING_PATH)
        
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
            # print(f"Message sent{json.dumps(data)}")
        else:
            print("WebSocket connection is not open")
            self.token = self.authenticate_signal_k(f"http://{self.SIGNALK_SERVER_URL}", self.SIGNALK_SERVER_USER, self.SIGNALK_SERVER_PASSWORD);
            self.run_signalk_websocket();

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
        self.io_pin_all_off() 
        self.send_value_to_signal_k();
        if self.ws:
            self.ws.close()  # Close the WebSocket connection
            print("WebSocket connection closed")

    def on_request_close(self, *args, **kwargs):
        # This is triggered for example by pressing the 'X' window button
        self.on_stop()  # Ensure on_stop is called
        return True
            
AnchorMate().run()
