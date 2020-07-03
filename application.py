import time
import requests
import config
import yeecontrol as yeelight
from threading import Thread
from time import sleep

# Variables to hold the current and last states
currentstate = 0
previousstate = 0
# start the bulb detection thread
detection_thread = Thread(target=yeelight.bulbs_detection_loop)
detection_thread.start()
# give detection thread some time to collect bulb info
sleep(1.00)

try:
    print("Ready")
    # Loop until user quits with CTRL-C
    while True:
        # Read state
        currentstate = 1 if yeelight.any_bulbs_detected() else 0
        # If the light is toggled
        if currentstate != previousstate:

            stateString = "On" if currentstate == 1 else "Off"
            print("Light turned" + stateString)

            r = requests.post('https://maker.ifttt.com/trigger/light_toggled/with/key/' + config.ifttt_api_key, params={"value1":stateString,"value2":"none","value3":"none"})

            previousstate = currentstate

        # Wait for 3 seconds
        time.sleep(3.00)

except KeyboardInterrupt:
    yeelight.close()
    detection_thread.join()