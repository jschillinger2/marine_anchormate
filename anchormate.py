from enum import Enum
from gpiozero import Button
from gpiozero import OutputDevice
from time import sleep

from kivy.properties import NumericProperty

from kivy.lang import Builder
from kivy.properties import StringProperty

from kivymd.app import MDApp
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem
from kivymd.uix.screen import MDScreen


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
                max: 20
                value: 20-app.current_depth
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
                max: 20
                value: 20-app.target_depth

                on_value: app.auto_slider_move(self.value)


        MDBoxLayout:
            orientation: "vertical"
            spacing: 10

            MDLabel:
                text: f"Current depth: {20-int(auto_slider_current.value)}m"
                halign: "center"

            MDLabel:
                text: f"Target depth: {20-int(auto_slider_target.value)}m"
                halign: "center"

            MDLabel:
                text: f"Move by: {int(auto_slider_current.value)-int(auto_slider_target.value)}m"
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

    MDButton:
        pos_hint: {"center_x": .5, "center_y": .3}
        width: root.width*0.3
        height: root.height*0.2
        style: "tonal"

        on_press: app.man_anchor_down_press()
        on_release: app.man_anchor_down_release()

        MDButtonIcon:
            icon: "menu-down"

        MDButtonText:
            text: "Down"

    MDButton:
        pos_hint: {"center_x": .5, "center_y": .8}
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

'''

class Direction(Enum):
    UP = 1
    DOWN = 2
    NONE = 3

class AnchorBro(MDApp):

    # switch to TRUE if you dont want to call the IO ports (for testing)
    SIMULATED = True
    
    # chain length in meter
    CHAIN_LENGTH=20

    # how many meters does the chain move for 1 rotation
    LENGTH_PER_ROTATION = 0.25

    # PINS
    PIN_ANCHOR_UP = 17
    PIN_ANCHOR_DOWN = 18
    PIN_ROTATION_INDICATOR = 19

    # the direction of the anchor movement
    current_direction = Direction.NONE
    
    # current depth of anchor
    current_depth = NumericProperty(5)

    # target depth chosen in auto mode
    target_depth = NumericProperty(0)

    # ios
    io_anchor_up = None if SIMULATED else OutputDevice(PIN_ANCHOR_UP)
    io_anchor_down = None if SIMULATED else OutputDevice(PIN_ANCHOR_DOWN)
    
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

    def man_anchor_down_press(a):
        print("Anchor Down Start")

    def man_anchor_down_release(a):
        print("Anchor Stop")

    def man_anchor_up_press(a):
        print("Anchor Up Start")

    def man_anchor_up_release(a):
        print("Anchor Stop")

    def auto_slider_move(a, value):
        # print(f"Current slider value: {value}")
        target_depth = 20-value

    def auto_go(a):
        print("Adjust Start")

    def auto_stop(a):
        print("Adjust Stop")
        
    def calib_top(self):
        print("Anchor-calib set at top")
        self.current_depth = 0

    def calib_bottom(self):
        print("Anchor-calib set at botton")
        self.current_depth = 20

    def io_pin_down_on():
        io_anchor_down.on()

    def io_pin_down_off():
        io_anchor_down.off()

    def io_pin_up_on():
        io_anchor_up.on()

    def io_pin_up_off():
        io_anchor_up.off()

    # Define the GPIO pin number you want to listen on
    PIN_NUMBER = 17  # Replace 17 with your specific GPIO pin number

    # Define a function to be called whenever the pin goes from LOW to HIGH
    def on_pulse():
        global current_depth
        print(f"Pulse detected! Current Depth: {current_depth}")
        if current_direction == Direction.UP:
            current_depth -= LENGTH_PER_ROTATION
        elif current_direction == Direction.DOWN:
            current_depth += LENGTH_PER_ROTATION
        else:
            print("Anchor moving despite no engine")

    # Setup the pin as a 'Button', treat rising edges as button presses
    # The 'bounce_time' parameter is optional and can be adjusted based on your needs
    pulse_detector =  None if SIMULATED else Button(PIN_ROTATION_INDICATOR, pull_up=None, bounce_time=0.05)

    # Attach the event handler function to be called on rising edges
    if not SIMULATED: pulse_detector.when_pressed = on_pulse    
        
AnchorBro().run()
