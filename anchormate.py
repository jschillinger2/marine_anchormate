import subprocess
import pygame
import time

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
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem
from kivymd.uix.screen import MDScreen

from threading import Thread



class BaseMDNavigationItem(MDNavigationItem):
    icon = StringProperty()
    text = StringProperty()

class ConfigScreen(MDScreen):
    image_size = StringProperty()

class ManualScreen(MDScreen):
    image_size = StringProperty()

class AutoScreen(MDScreen):
    image_size = StringProperty()

KV = '''

<BaseMDNavigationItem>

    MDNavigationItemIcon:
        icon: root.icon

    MDNavigationItemLabel:
        text: root.text

<AutoScreen>

    MDBoxLayout:
        orientation: "horizontal"
        padding: 10
        spacing: 10

        MDBoxLayout:
            orientation: "horizontal"
            spacing: 10

            MDSlider:
                id: auto_slider_current

                orientation: "vertical"
                width: root.width*0.2
                height: root.height*0.9
                min: 0
                max: app.CHAIN_LENGTH
                value: app.CHAIN_LENGTH-app.current_depth
                disabled: True

            MDSlider:
                id: auto_slider_target

                orientation: "vertical"
                width: root.width*0.2
                height: root.height*0.9
                track_color_active: "red"
                track_color_inactive: "red"
                hint: True
                min: 0
                max: app.CHAIN_LENGTH
                value: app.CHAIN_LENGTH-app.target_depth

                on_value: app.auto_slider_move(self.value)


        MDBoxLayout:
            orientation: "vertical"
            spacing: 10

            MDLabel:
                text: f"Current depth: {format(app.current_depth, '.1f')}m"
                halign: "center"

            MDLabel:
                text: f"Target depth: {format(app.target_depth,'.1f')}m"
                halign: "center"

            MDLabel:
                text: f"Move by: {format(app.target_depth-app.current_depth,'+.1f')}m"
                halign: "center"

            MDButton:
                text: "Go"
                pos_hint: {"center_x": 0.5}
                width: root.width*0.2
                height: root.height*0.2

                on_press: app.auto_go()

                MDButtonIcon:
                    icon: "language-go"

                MDButtonText:
                    text: "Go!"

            MDButton:
                text: "Stop"
                pos_hint: {"center_x": 0.5}
                width: root.width*0.2
                height: root.height*0.2

                on_press: app.auto_stop()

                MDButtonIcon:
                    icon: "stop"

                MDButtonText:
                    text: "Stop!"

<ConfigScreen>

    MDButton:
        on_press: app.calib_bottom()

        pos_hint: {"center_x": .5, "center_y": .3}
        width: root.width*0.5
        height: root.height*0.2

        MDButtonIcon:
            icon: "set-split"

        MDButtonText:
            text: "Set: Anchor is down (end of chain)!"

    MDButton:
        on_press: app.calib_top()

        pos_hint: {"center_x": .5, "center_y": .8}
        width: root.width*0.5
        height: root.height*0.2

        MDButtonIcon:
            icon: "set-split"
            icon_size: "200sp"

        MDButtonText:
            text: "Set: Anchor is up!"
            font_size: "40sp"

<ManualScreen>

    MDBoxLayout:
        orientation: "horizontal"
        padding: 10
        spacing: 10

        MDBoxLayout:
            orientation: "horizontal"
            spacing: 10

            MDSlider:
                id: auto_slider_current

                orientation: "vertical"
                width: root.width*0.2
                height: root.height*0.9
                min: 0
                max: app.CHAIN_LENGTH
                value: app.CHAIN_LENGTH-app.current_depth
                disabled: True

        MDBoxLayout:
            orientation: "vertical"
            spacing: 10

            MDLabel:
                text: f"Current depth: {format(app.current_depth,'.1f')}m"
                halign: "center"

            MDButton:
                pos_hint: {"center_x": .5}
                width: root.width*0.3
                height: root.height*0.2
                style: "tonal"

                on_press: app.man_anchor_up_press()
                on_release: app.man_anchor_up_release()

                MDButtonIcon:
                    icon: "menu-up"
                    icon_size: "200sp"

                MDButtonText:
                    text: "Up"
                    font_size: "40sp"

            MDButton:
                pos_hint: {"center_x": .5}
                width: root.width*0.3
                height: root.height*0.2
                style: "tonal"

                on_press: app.man_anchor_down_press()
                on_release: app.man_anchor_down_release()

                MDButtonIcon:
                    icon: "menu-down"

                MDButtonText:
                    text: "Down"

MDBoxLayout:
    orientation: "vertical"
    md_bg_color: self.theme_cls.backgroundColor

    MDScreenManager:
        id: screen_manager

        ManualScreen:
            name: "Manual"
            image_size: "800"

        AutoScreen:
            name: "Auto"
            image_size: "1024"
            orientation: "horizontal"

        ConfigScreen:
            name: "Calibrate"
            image_size: "600"

    MDNavigationBar:
        on_switch_tabs: app.on_switch_tabs(*args)

        BaseMDNavigationItem
            icon: "car-shift-pattern"
            text: "Manual"
            active: True

        BaseMDNavigationItem
            icon: "car-child-seat"
            text: "Auto"

        BaseMDNavigationItem
            icon: "tools"
            text: "Calibrate"

        MDLabel:
            text: f"{app.debug_msg}"
            halign: "center"

'''

class Direction(Enum):
    UP = 1
    DOWN = 2
    NONE = 3

class AnchorMate(MDApp):

    # switch to TRUE if you dont want to call the IO ports (for testing)
    SIMULATED = True

    # switch on if you want to see debug info on the screen
    DEBUG = True

    # path to ding sound
    SOUND_DING_PATH = "res/sounds/ding.mp3"
    
    # chain length in meter
    CHAIN_LENGTH=20

    # how many meters does the chain move for 1 rotation
    LENGTH_PER_ROTATION = 0.25

    # minimum length to pull the anchor up, allow user to do the rest manual
    MIN_DEPTH = 2
    
    # PINS
    PIN_ANCHOR_UP = 17
    PIN_ANCHOR_DOWN = 18
    PIN_ROTATION_INDICATOR = 19

    # the direction of the anchor movement
    current_direction = Direction.NONE
    
    # current depth of anchor
    current_depth = NumericProperty(5)
    last_current_depth = -1
    
    # target depth chosen in auto mode
    target_depth = NumericProperty(0)

    # set in automode if the cancel button is pushed
    auto_cancel=False

    debug_msg = StringProperty("debug text")
    debug_pinstate_down = BooleanProperty(False)
    debug_pinstate_up = BooleanProperty(False)
    debug_pinstate_pulse = BooleanProperty(False)
    
    # ios
    io_anchor_up = None if SIMULATED else OutputDevice(PIN_ANCHOR_UP)
    io_anchor_down = None if SIMULATED else OutputDevice(PIN_ANCHOR_DOWN)

    def __init__(self, **kwargs):
        super(AnchorMate, self).__init__(**kwargs)
        
        # Set listeners for each BooleanProperty
        self.bind(debug_pinstate_up=self.update_debug_msg)
        self.bind(debug_pinstate_down=self.update_debug_msg)
        self.bind(debug_pinstate_pulse=self.update_debug_msg)

        # Set listeners to current depth to trigger TTS
        self.bind(current_depth=self.update_depth_tts)

        # Initialize the debug message
        self.update_debug_msg()

        # set timer to simulate anchor pulse
        if self.SIMULATED:
            Clock.schedule_interval(self.on_pulse_simulated_pressed, 2)   
        self.speak("Anchor Control is ready")    

    def update_depth_tts(self,a,b):
        if int(self.current_depth) != int(self.last_current_depth):
            self.speak(f"{round(self.current_depth)} meters")
        self.last_current_depth = self.current_depth
        
    def on_switch_tabs(
        self,
        bar: MDNavigationBar,
        item: MDNavigationItem,
        item_icon: str,
        item_text: str,
    ):
        self.root.ids.screen_manager.current = item_text

    def build(self):        
        return Builder.load_string(KV)

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
        self.speak_process("Adjusting anchor height. Press Stop to cancel.")
        Thread(target=self.auto_go_process, args=(distancetomove,)).start()

    def auto_go_process(self, delta):
        if delta > 1:
            self.man_anchor_down_press()
            while (self.current_depth<self.target_depth) and not self.auto_cancel:
                time.sleep(0.1)
            self.man_anchor_down_release()
            if not self.auto_cancel:
                self.speak("Anchor is at target depth")
            else:
                self.speak("Anchor adjustment cancelled")
        else:
            print("xx")
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
        if not self.SIMULATED:
            self.io_anchor_down.on()

    def io_pin_all_off(self):
        self.debug_pinstate_up = False
        self.debug_pinstate_down = False        
        if not self.SIMULATED:
            self.io_anchor_down.off()
            self.io_anchor_up.off()

    def io_pin_up_on(self):
        self.io_pin_all_off()
        self.debug_pinstate_up = True
        if not self.SIMULATED:
            self.io_anchor_up.on()

    # called by time in simulation mode to simulate pulse from rotation
    def on_pulse_simulated_pressed(self, a):
       self.on_pulse_on()
       Clock.schedule_once(self.on_pulse_simulated_release, 0.5)
       
    def on_pulse_simulated_release(self, a):
       # time.sleep(1) 
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
    pulse_detector =  None if SIMULATED else Button(PIN_ROTATION_INDICATOR, pull_up=None, bounce_time=0.05)

    # Attach the event handler function to be called on rising edges
    if not SIMULATED: pulse_detector.when_pressed = on_pulse_on(self)
    if not SIMULATED: pulse_detector.when_released = on_pulse_off(self)
    
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
        self.debug_msg = f"U:{self.debug_pinstate_up}, D:{self.debug_pinstate_down}, P:{self.debug_pinstate_pulse}"

        
AnchorMate().run()
