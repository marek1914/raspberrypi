#!/usr/bin/python

"""
PI HAT FLOW SENSOR DEMO!!!

   Contributors:
     * Fred Kellerman
 
   Licensed under the Apache License, Version 2.0 (the "License"); 
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, 
   software distributed under the License is distributed on an 
   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
   either express or implied. See the License for the specific 
   language governing permissions and limitations under the License.
"""

import os
import time
import sys
import subprocess 
import httplib
import json
from setupflowpaths import setup_flow_paths

# Global variables that contains the cell modem device names
ETH_DEV = "none"
COM_DEV = "none"
USE_VIRTUAL_SENSE_HAT = False
USE_CELL_MODEM = True
SENSE = ""

def main():

    global ETH_DEV
    global COM_DEV
    global USE_VIRTUAL_SENSE_HAT
    global USE_CELL_MODEM
    global SENSE
    
    ######################################################
    #  A few setup items:
    ######################################################
    
    # Setup flow server paths
    flowurls, flowpaths, max_num_flow_servers = setup_flow_paths()

    # Free M2X developer accounts only officially support 10 devices/sensors,
    # no limit in Flow itself BUT you must also modify the number of devices
    # in the Flow program!    
    MAX_NUM_SENSORS = 8
    
    # 8 Max LED rows in s Pi Sense Hat, can be more if using something else
    MAX_NUM_SENSE_ROWS = 8
    # How long a constant press and hold of the middle sense hat joystick will
    # take to cause an exit of this program
    REBOOT_HOLD_TIME = 7
    # How many times to average the Pi Sense Hat positional sensors
    NUM_POSITION_READINGS_AVG = 1
    # Color of LED when showing an HTTP issue
    DISCONNECTED_LED_RGB_HTTP = [64, 0, 0]
    # Color of LED when modem cell signal becomes disconnected
    DISCONNECTED_LED_RGB = [64, 64, 64]
    # How long to wait for a response from the cellular modem serial port
    UART_READ_TIMEOUT_SECS = 2
    # How many times an HTTP connection will fail before the program
    # reboots the Raspberry Pi
    WATCHDOG_CNT_MAX = 10
    # How long to wait for an HTTP response back from the Flow server
    HTTP_CONNECTION_TIMEOUT = 10
    # When using the remote firmware upgrade feature, where to put the downloaded file
    FIRMWARE_PATH = '/home/pi/senseflowdemo1'

    # Use cmd line options to setup    
    parse_cmd_line()

    if USE_CELL_MODEM == True :
        import serial
        from bars import AtCellModem_14A2A

    ######### Action begins
    if USE_CELL_MODEM == True :
        while 1 :
            while (COM_DEV == "none" or ETH_DEV == "none") :
                COM_DEV, ETH_DEV = find_wnc_devices(ETH_DEV)
                if (COM_DEV == "none") :
                    SENSE.show_message("Unable to detect Modem COM port", scroll_speed = 0.04, text_colour = [255, 0, 0])
                    SENSE.show_message("Recheck USB...", scroll_speed = 0.04, text_colour = [255, 0, 0])
                elif (ETH_DEV == "none") :
                    SENSE.show_message("Unable to detect Modem Ethernet", scroll_speed = 0.04, text_colour = [255, 0, 0])
                    SENSE.show_message("Recheck USB...", scroll_speed = 0.04, text_colour = [255, 0, 0])
            try :
                uart = serial.Serial(COM_DEV, 115200, timeout=UART_READ_TIMEOUT_SECS)
                break
            except KeyboardInterrupt:
                my_ctrl_c_exit(ETH_DEV)
            except:
                SENSE.show_message("Serial port unable to open", scroll_speed = 0.05, text_colour = [255, 0, 0])

        # Attempt open close
        for n in range(20, 1, -1):
            uart.close()
            uart.open()
            if uart.isOpen() == True :
                SENSE.show_message(uart.name, scroll_speed = 0.03, text_colour = [255, 0, 0])         
                break
            else :
                SENSE.show_message("Wait Mdm Serial " + str(n), scroll_speed = 0.03, text_colour = [255, 0, 0])

        # Create AT modem controller object, validate serial with modem type
        at_mdm = AtCellModem_14A2A(uart, timeout=UART_READ_TIMEOUT_SECS) #, dbgFileName = '/home/pi/at.log')
        no_type = True
        while no_type == True :
            SENSE.show_message("Type: " + str(at_mdm.modem_type), scroll_speed = 0.03, text_colour = [255, 0, 0])
            at_mdm.get_version()
            no_type = (at_mdm.modem_type == 'None') or (at_mdm.modem_type == 'command')
            if (at_mdm.modem_type == 'command') :
                SENSE.show_message("FAIL: modem in serial debug mode, power cycle and reconnect modem!", scroll_speed = 0.03, text_colour = [255, 0, 0])        

        # Wait for a few AT OKs, wait until.
        wait_for_at_ok(at_mdm, SENSE)

    # Enter main loop, only reboot will exit.  Show bars, get ID start reading sensors
    while 1 :
        if USE_CELL_MODEM == True :
            # Poll mdm with AT commands to see if we're connected and measure signal strength
            idIsNotDone = 1 
            while idIsNotDone == 1 :
                # Show bars
                #print 'Update bars'
                display_mdm_bars(at_mdm, SENSE)
                for button_events in SENSE.stick.get_events() :
                    if (button_events.direction == "middle") :
                        idIsNotDone = 0
                # 14A2A cannot handle just hitting it hard with read signal strength
                # It messes up the AT command response from the modem
                time.sleep(.3)
        
        # Handle possible double push
        time.sleep(.3)
        for button_events in SENSE.stick.get_events() : dummy = 1
        
        # Gather user input for picking flow server URL
        url_index = 0
        if max_num_flow_servers > 1 :
            SENSE.show_letter(str(url_index + 1), text_colour = [255,0,0], back_colour = [0,0,0])
            notDone = 1
            while notDone == 1 :
                for button_events in SENSE.stick.get_events() :
                    if (button_events.action == "pressed") :
                        if (button_events.direction == "down" or button_events.direction == "right") :
                            url_index -= 1
                        elif (button_events.direction == "up" or button_events.direction == "left") :
                            url_index += 1
                        if (url_index + 1) > max_num_flow_servers :
                            url_index = 0
                        if (url_index < 0) :
                            url_index = max_num_flow_servers - 1
                        SENSE.show_letter(str(url_index + 1), text_colour = [255,0,0], back_colour = [0,0,0])                        
                        if (button_events.direction == "middle") :
                            notDone = 0
            
        # Gather user input for setting serial device name
        id = 1
        display_id(id, SENSE, MAX_NUM_SENSORS)
        idIsNotDone = 1 
        while idIsNotDone == 1 :
            for button_events in SENSE.stick.get_events() :
                if (button_events.action == "pressed") :
                    if (button_events.direction == "down" or button_events.direction == "right") :
                         id -= 1
                    elif (button_events.direction == "up" or button_events.direction == "left") :
                         id += 1
                    if (id > MAX_NUM_SENSORS) :
                         id = 1
                    if (id < 1) :
                         id = MAX_NUM_SENSORS 
                    display_id(id, SENSE, MAX_NUM_SENSORS)                        
                    if (button_events.direction == "middle") :
                        idIsNotDone = 0
        
        if (id > 99) :
            serialName = "SenseHat" + str(id)    
        if (id > 9) :
            serialName = "SenseHat0" + str(id)    
        else :
            serialName = "SenseHat00" + str(id)        

        SENSE.clear()
        for button_events in SENSE.stick.get_events() : tmp = 1 # Empty Event Queue
        reboot_pi_timer = time.time() # Initialize the variable, cause a push and hold causes trouble
        sig_display = False
        mdm_rsrp = mdm_rssi = 0
        bars_on = False
        blank_pos = 0
        WatchDogCnt = 0

        # Poll the sense hat and report the results to the Flow server
        # Wait for server reply and update LED Matrix with the results
        # Reset to the Pi will exit this loop and return to bars and ID setup!
        while 1 :
            if USE_CELL_MODEM == True :
                # Poll mdm with AT commands to see if we're connected to device serial port
                if at_mdm.uart.isOpen() == True :
                    mdm_connected = at_mdm.is_on_network()
                    if mdm_connected == True :
                        mdm_rsrp = at_mdm.read_rsrp()
                        mdm_rssi = at_mdm.read_rssi()
                    else :
                        mdm_rsrp = mdm_rssi = 0
                else :
                    at_mdm.uart.close()
                    try :
                        COM_DEV, ETH_DEV = find_wnc_devices(ETH_DEV)
                        if COM_DEV <> "none" :
                            at_mdm.uart = serial.Serial(COM_DEV, 115200, timeout=UART_READ_TIMEOUT_SECS)
                            SENSE.show_message("Re-connecting " + COM_DEV, scroll_speed = 0.05, text_colour = [255, 0, 0])
                            wait_for_at_ok(at_mdm, SENSE)  # This will wait forever to get an AT OK
                            mdm_connected = True
                        else :
                            mdm_connected = False
                    except KeyboardInterrupt:
                        my_ctrl_c_exit(ETH_DEV)
                    except:
                        mdm_connected = False
                        SENSE.show_message("Unable to open Serial port", scroll_speed = 0.05, text_colour = [255, 0, 0])
                    if mdm_connected == False :
                        mdm_rsrp = mdm_rssi = 0
            else :
                # If no modem, genearate data like it is...
                mdm_rsrp = mdm_rssi = 0
                mdm_connected = True  # Override since this could be because the user doesn't have a cell and ordered it to ignore.
            # Read PI HAT Sensor data to send to the Flow program via an http get request
            tempstr = str(round(SENSE.temp))
            humiditystr = str(round(SENSE.humidity))
            pressurestr = str(round(SENSE.pressure))
            accelZ = accelY = accelX = 0 
            for i in range(1, NUM_POSITION_READINGS_AVG + 1) :
                orientation = SENSE.get_gyroscope()
                accelZ += -180 + orientation["pitch"]
                accelY += -180 + orientation["roll"]
                accelX += -180 + orientation["yaw"]
            accelXstr = str(round(accelX/i))
            accelYstr = str(round(accelY/i))
            accelZstr = str(round(accelZ/i))
            #print accelXstr, accelYstr, accelZstr 

            # Button time!
            button1 = button2 = button3 = button4 = button5 = "0"
            buttons = SENSE.stick.get_events() 
            for button_events in buttons :
                #print button_events.action
                #print button_events.direction
                if button_events.action == "pressed" : 
                    button1 = "1" if button_events.direction == "up" else "0"
                    button2 = "1" if button_events.direction == "down" else "0"
                    button3 = "1" if button_events.direction == "left" else "0"
                    button4 = "1" if button_events.direction == "right" else "0"
                    button5 = "1" if button_events.direction == "middle" else "0"
                    reboot_pi_timer = time.time() 
                if button_events.action == "held" :
                    if button_events.direction == "middle" :
                        if (time.time() - reboot_pi_timer) > REBOOT_HOLD_TIME :
                            SENSE.clear()
                            SENSE.show_message("Exiting program as requested", scroll_speed = 0.07, text_colour = [255, 0, 0])
                            my_ctrl_c_exit(ETH_DEV)

            # This is the GET request body, it will be parsed by the Flow server and a response will be given in the form of a JSON string with a color
            getflow = flowpaths[url_index] + \
                      "?serial=" + serialName + \
                      "&measuredTempC=" + tempstr + \
                      "&measuredHumidity=" + humiditystr + \
                      "&measuredAccelX=" + accelXstr + \
                      "&measuredAccelY=" + accelYstr + \
                      "&measuredAccelZ=" + accelZstr + \
                      "&inBtn1=" + button1 + \
                      "&inBtn2=" + button2 + \
                      "&inBtn3=" + button3 + \
                      "&inBtn4=" + button4 + \
                      "&inBtn5=" + button5 + \
                      "&rssi=" + str(mdm_rssi)  + \
                      "&rsrp=" + str(mdm_rsrp) + \
                      "&measuredPressure=" + pressurestr 
        
            # Echo the string so you can see what is going on 
            #print "HTTP GET:"
            #print getflow

            httpSuccess = False        
            # Connect to the Flow server and send the request
            try :
                conn = httplib.HTTPSConnection(flowurls[url_index], timeout = HTTP_CONNECTION_TIMEOUT)
                try :
                    conn.request("GET", getflow)
                    # Wait and obtain the response from the server
                    reply = conn.getresponse()
                    replystr = reply.read()
                    # Close the socket
                    conn.close()
                    httpSuccess = True
                except KeyboardInterrupt :
                    my_ctrl_c_exit(ETH_DEV)
                except httplib.HTTPException:
                    SENSE.show_message("HTTP response/close Exception ", scroll_speed = 0.04, text_colour = [255, 0, 0])            
                    try :
                        conn.close()
                    except KeyboardInterrupt :
                        my_ctrl_c_exit(ETH_DEV)
                    except :
                        SENSE.show_message("HTTP close Exception ", scroll_speed = 0.04, text_colour = [255, 0, 0])                
                except :
                    SENSE.show_message("HTTP Host unreachable ", scroll_speed = 0.04, text_colour = [255, 0, 0])
            except KeyboardInterrupt:
                my_ctrl_c_exit(ETH_DEV)
            except httplib.HTTPException:
                SENSE.show_message("HTTP open Exception ", scroll_speed = 0.04, text_colour = [255, 0, 0])                
            except :
                SENSE.show_message("HTTP general ERR1 ", scroll_speed = 0.04, text_colour = [255, 0, 0])            

            if httpSuccess == False or mdm_connected == False :
                pixels = SENSE.get_pixels()
                if httpSuccess == False :
                    led_rgb = DISCONNECTED_LED_RGB_HTTP
                else :
                    led_rgb = DISCONNECTED_LED_RGB
                for r in range(0,64,MAX_NUM_SENSE_ROWS) :
                    pixels[r] = led_rgb
                SENSE.set_pixels(pixels)

            # Echo whether the server accepted the GET request
            #print "Server http reply:", reply.status, reply.reason
            # Echo the response the server gave
            #print "Server response:", replystr
        
            if httpSuccess == True :
                if reply.reason == "Accepted" :
                    WatchDogCnt = 0

                    # Parse out the LED color from the json string
                    parsedjson = json.loads(replystr)

                    # Check for cmd
                    action = parsedjson['action']
                    if action != 'none' :
                        print action
                        if action.find('update') <> -1 :
                            action = action[6:]  # remove 'update' the rest is the URL/path/
                            SENSE.show_message("Fimware update begin, parsed URL: " + action, scroll_speed = .03, text_colour = [255, 0, 0])
                            subprocess.call("mkdir " + FIRMWARE_PATH, shell=True)
                            subprocess.call("wget -P " + FIRMWARE_PATH + " " + action + "/atthatflow.py", shell=True)
                            subprocess.call("wget -P " + FIRMWARE_PATH + " " + action + "/bars.py", shell=True)
                            subprocess.call("wget -P " + FIRMWARE_PATH + " " + action + "/setupflowpaths.py", shell=True)                            
                            subprocess.call("mv " + FIRMWARE_PATH + "/bars.py.1 " + FIRMWARE_PATH + "/bars.py", shell=True)
                            subprocess.call("mv " + FIRMWARE_PATH + "/atthatflow.py.1 " + FIRMWARE_PATH + "/atthatflow.py", shell=True)
                            subprocess.call("mv " + FIRMWARE_PATH + "/setupflowpaths.py.1 " + FIRMWARE_PATH + "/setupflowpaths.py", shell=True)                            
                            subprocess.call("chmod 0700 " + FIRMWARE_PATH + "/bars.py", shell=True)
                            subprocess.call("chmod 0700 " + FIRMWARE_PATH + "/atthatflow.py", shell=True)
                            subprocess.call("chmod 0700 " + FIRMWARE_PATH + "/setupflowpaths.py", shell=True)
                            SENSE.show_message("Firmware update complete!", scroll_speed = 0.03, text_colour = [255, 0, 0])
                        elif action == 'reboot' :
                            subprocess.call("sudo shutdown -r now &", shell=True)
                            SENSE.clear()
                            while (1) : a = 1
                        elif action == 'shutdown' :
                            subprocess.call("sudo shutdown now &", shell=True)
                            SENSE.clear()              
                            while (1) : a = 1
                        elif action == 'reset' :
                            break
                        elif action == 'hi' :
                            hiMsg = 'Heat Index: ' + parsedjson['computedHeatIndexC'] + 'C'
                            SENSE.show_message(hiMsg, scroll_speed = 0.05, text_colour = [255, 255, 0])
                        elif action == 'signalon' :
                            bars_on = True
                        elif action == 'signaloff' :
                            bars_on = False
                        elif action == 'none' or action == 'msg' :
                            action = action
                        # Add your own actions here
                        else :
                            SENSE.show_message("Unknown action: " + action, scroll_speed = 0.05, text_colour = [255, 255, 0])

                    # Move a dot at the rate of the FLOW responses
                    blank_pos = (blank_pos + 1) % MAX_NUM_SENSE_ROWS

                    # Check the mailbox
                    msg = parsedjson["MSG"]
                    if msg != "" :
                        SENSE.show_message(msg, scroll_speed = 0.05, text_colour = [255, 255, 0], back_colour = [0, 0, 128])

                    # Signal bars if turned on else coloured rows
                    if (bars_on == True) and (COM_DEV <> "none") :
                        if USE_CELL_MODEM == True :
                            display_mdm_bars(at_mdm, SENSE)
                        else :
                            display_bars(-1, SENSE)
                    else:
                        rgbLEDs = []
                        if id <= MAX_NUM_SENSE_ROWS :
                            row_range = range(1, MAX_NUM_SENSE_ROWS + 1)
                        else :
                            modN = MAX_NUM_SENSORS - MAX_NUM_SENSE_ROWS + 1
                            row_range = range(1, modN)
                            row_range = [MAX_NUM_SENSE_ROWS + e for e in row_range] + [e for e in row_range]
                        for i in row_range :
                            rLedColor = int(parsedjson["R" + str(i)])
                            gLedColor = int(parsedjson["G" + str(i)])
                            bLedColor = int(parsedjson["B" + str(i)])
                            rgbLEDRow = [[rLedColor, gLedColor, bLedColor]]
                            # print "row: " + str(i) + "rgb: " + str(rLedColor) + " " + str(gLedColor) + " " + str(bLedColor)
                            rgbLEDRow *= MAX_NUM_SENSE_ROWS
                            if i == id :
                                rgbLEDRow[blank_pos] = [0,0,0]
                                rgbLEDRow[(blank_pos + 1) % MAX_NUM_SENSE_ROWS] = [0,0,0]
                                rgbLEDRow[(blank_pos + 2) % MAX_NUM_SENSE_ROWS] = [0,0,0]
                                rgbLEDRow[(blank_pos + 3) % MAX_NUM_SENSE_ROWS] = [0,0,0]
                            rgbLEDs += rgbLEDRow
                        SENSE.set_pixels(rgbLEDs)
                    try :
                        a = 1
                    except KeyboardInterrupt :
                        my_ctrl_c_exit(ETH_DEV)
                    except :
                        SENSE.show_message("JSON ERROR ", scroll_speed = 0.04, text_colour = [255, 0, 0])
                        break
                else:
                    WatchDogCnt += 1
                    SENSE.show_message("HTTP GET: rejected ", scroll_speed = 0.04, text_colour = [255, 0, 0])
            else:
                WatchDogCnt += 1
                SENSE.show_message("HTTP GET: not sent ", scroll_speed = 0.04, text_colour = [255, 0, 0])
            
            if WatchDogCnt >= WATCHDOG_CNT_MAX :
                SENSE.show_message("Watchdog Expired: Rebooting...", scroll_speed = 0.03, text_colour = [255, 0, 0])            
                SENSE.clear()
                subprocess.call("sudo shutdown -r now &", shell=True)
                exit(0)

def print_usage() :
    print
    print 'usage: atthatflow.py [emu_cell | noemu_cell | emu_nocell | noemu_nocell]'
    print
    print 'If no command lines then default is virtual sense hat and no cellular modem'
    print
    print '    emu_cell = Use Virtual Sense Emulator and Cellular WNC modem'
    print '    noemu_cell = Use real Sense Emulator and Cellular WNC modem'
    print '    emu_nocell = Use Virtual Sense Emulator and use other internet connection'
    print '    moemu_nocell = Use real Sense Emulator and use other internet connection'
    print

def my_ctrl_c_exit(eth_dev) :
    if eth_dev <> "none" :
        subprocess.call("sudo route delete default " + eth_dev, shell=True)
        print "Deleting WNC modem " + eth_dev + " from default route table"
    os._exit(-1)  #  plain exit() raises exceptions and doesn't truly exit, this one does!

def display_mdm_bars(mdm, sense_hat):
    bars = mdm.calc_rx_bars(1)  # Danger danger, leave at 1, 14A2A can't handle back to back
    display_bars(bars, sense_hat)
    #if bars == -1 :
        #sense_hat.show_message("Invalid cell signal read!", scroll_speed = 0.05, text_colour = [255, 0, 0])
    
def find_wnc_usb_device():        
    subprocess.call("lsusb -t -d 1435:3142 | grep acm > wnc_dev.lst", shell=True)
    result = os.path.getsize("wnc_dev.lst") > 0
    subprocess.call("rm wnc_dev.lst", shell=True)
    return result

def find_wnc_comport():
    if find_wnc_usb_device() == True :
        # Find the last 3 entries in dmesg and pick off the 1st one, that will be the AT port
        subprocess.call("dmesg | grep ttyACM | tail -3 | head -1 > wnc_dev.lst", shell=True)
        if os.path.getsize("wnc_dev.lst") > 0 :
            for i in range(0,10) :
                subprocess.call("dmesg | grep ttyACM | tail -3 | head -1 | grep ttyACM" + str(i) + " > wnc_dev.lst", shell=True)
                if os.path.getsize("wnc_dev.lst") > 0 :
                    subprocess.call("rm wnc_dev.lst", shell=True)
                    print "Found WNC ttyACM" + str(i) + " device"
                    return "/dev/ttyACM" + str(i)
        subprocess.call("rm wnc_dev.lst", shell=True)
    print "WNC serial port not found!"
    return "none"

# This assumes that the WNC is the only cdc_ether attached to the Pi!
def find_wnc_eth(eth_dev):
    if eth_dev <> "none" :
        print "Remove " + eth_dev + " from global route table"    
        subprocess.call("sudo route delete default " + eth_dev, shell=True)    
    if find_wnc_usb_device() == True :
        # Try to find which eth it's at:
        for i in range(0,10):
            subprocess.call("dmesg | grep cdc_ether | grep eth" + str(i) + " | tail -1 > wnc_dev.lst", shell=True)
            if os.path.getsize("wnc_dev.lst") > 0 :
                subprocess.call("rm wnc_dev.lst", shell=True)
                eth_dev = "eth" + str(i)
                print "Found WNC " + eth_dev
                # Try to make the IP traffic use the cellular modem which should which show up as ethX
                print "Making " + eth_dev + " be default in global route table"
                subprocess.call("sudo route add default " + eth_dev, shell=True)
                return "eth" + str(i)
        subprocess.call("rm wnc_dev.lst", shell=True)
    print "WNC eth not found! (maybe told not to use it via cmd line)"
    return "none"

def find_wnc_devices(eth_dev):
    com_dev = find_wnc_comport()
    eth_dev = find_wnc_eth(eth_dev)
    return com_dev, eth_dev

def wait_for_at_ok(mdm, sense_hat, debug=False) :
    sense_hat.show_message("Wait for AT OK", scroll_speed = 0.03, text_colour = [255, 0, 0])
    cnt = 0
    while 1:
        result, resp = mdm.send_mdm_cmd('AT', timeout=1)
        sense_hat.show_message(".", scroll_speed = 0.01, text_colour = [255, 0, 0])
        if result == True :
           cnt += 1
        else :
           cnt = 0
        if cnt >= 4 :
            sense_hat.show_message("AT OK", scroll_speed = 0.03, text_colour = [255, 0, 0])
            break

def make_rainbow(sense_hat, num_display_secs, twinkle_time = 0) :
    from colorsys import hsv_to_rgb
    from time import sleep
    from time import time

    # Hues represent the spectrum of colors as values between 0 and 1. The range
    # is circular so 0 represents red, ~0.2 is yellow, ~0.33 is green, 0.5 is cyan,
    # ~0.66 is blue, ~0.84 is purple, and 1.0 is back to red. These are the initial
    # hues for each pixel in the display.
    hues = [
        0.00, 0.00, 0.06, 0.13, 0.20, 0.27, 0.34, 0.41,
        0.00, 0.06, 0.13, 0.21, 0.28, 0.35, 0.42, 0.49,
        0.07, 0.14, 0.21, 0.28, 0.35, 0.42, 0.50, 0.57,
        0.15, 0.22, 0.29, 0.36, 0.43, 0.50, 0.57, 0.64,
        0.22, 0.29, 0.36, 0.44, 0.51, 0.58, 0.65, 0.72,
        0.30, 0.37, 0.44, 0.51, 0.58, 0.66, 0.73, 0.80,
        0.38, 0.45, 0.52, 0.59, 0.66, 0.73, 0.80, 0.87,
        0.45, 0.52, 0.60, 0.67, 0.74, 0.81, 0.88, 0.95,
    ]
    def scale(v):
        return int(v*255)

    num_display_secs = abs(num_display_secs) + 1  # +1 to make sure at least 1 sec!
    startTime = time()
    l = 0.0
    while (time() - startTime) < num_display_secs :
        # Rotate the hues
        hues = [(h + 0.04) % 1.0 for h in hues]
        l = (l + .01) % .8
        ll = .2 + l
        # Convert the hues to RGB values
        pixels = [hsv_to_rgb(h, 1.0, ll) for h in hues]
        # hsv_to_rgb returns 0..1 floats; convert to ints in the range 0..255
        pixels = [(scale(r), scale(g), scale(b)) for r, g, b in pixels]
        # Update the display
        sense_hat.set_pixels(pixels)
        sleep(twinkle_time)

def display_bars(bars, sense_hat):    
    if bars < 1 :
        bars = 0
        f = [255,0,0]
    else :
        f = [0,0,255]
        
    b = [0,0,0]

    if bars == 0 :
        rgb_pixels = \
        [b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         f,b,b,b,b,b,b,b]
    elif bars == 1 :
        rgb_pixels = \
        [b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,f,b,b,b,b,b,b,
         b,f,b,b,b,b,b,b]
    elif bars == 2 :
        rgb_pixels = \
        [b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,f,b,b,b,b,
         b,b,b,f,b,b,b,b,
         b,f,b,f,b,b,b,b,
         b,f,b,f,b,b,b,b]
    elif bars == 3 :
        rgb_pixels = \
        [b,b,b,b,b,b,b,b,
         b,b,b,b,b,b,b,b,
         b,b,b,b,b,f,b,b,
         b,b,b,b,b,f,b,b,
         b,b,b,f,b,f,b,b,
         b,b,b,f,b,f,b,b,
         b,f,b,f,b,f,b,b,
         b,f,b,f,b,f,b,b]
    else :
        rgb_pixels = \
        [b,b,b,b,b,b,b,f,
         b,b,b,b,b,b,b,f,
         b,b,b,b,b,f,b,f,
         b,b,b,b,b,f,b,f,
         b,b,b,f,b,f,b,f,
         b,b,b,f,b,f,b,f,
         b,f,b,f,b,f,b,f,
         b,f,b,f,b,f,b,f]

#    sense_hat.clear()
    sense_hat.set_pixels(rgb_pixels)

def parse_cmd_line() :
    global USE_VIRTUAL_SENSE_HAT
    global USE_CELL_MODEM
    global SENSE
    global ETH_DEV
    global COM_DEV
    
    # Parse command line inputs to setup emu or SENSE hat or cell or no cell:
    if len(sys.argv) == 1 :
        # Try to autodetect SENSE hat and cellular modem
        try :
            from sense_hat import SenseHat
            SENSE = SenseHat()
            USE_VIRTUAL_SENSE_HAT = False
            print "Real Sense Hat Detected"
        except KeyboardInterrupt :
            my_ctrl_c_exit(ETH_DEV)
        except :
            from sense_emu import SenseHat
            SENSE = SenseHat()
            SENSE.clear()     
            USE_VIRTUAL_SENSE_HAT = True 
            print "Using Sense Hat Emulator"
        COM_DEV, ETH_DEV = find_wnc_devices(ETH_DEV)
        USE_CELL_MODEM = COM_DEV <> "none"    
    elif len(sys.argv) == 2 :
        if sys.argv[1] == 'emu_cell' :
            USE_VIRTUAL_SENSE_HAT = True
            USE_CELL_MODEM = True    
        elif sys.argv[1] == 'noemu_cell' :
            USE_VIRTUAL_SENSE_HAT = False
            USE_CELL_MODEM = True    
        elif sys.argv[1] == 'emu_nocell' :
            USE_VIRTUAL_SENSE_HAT = True
            USE_CELL_MODEM = False
        elif sys.argv[1] == 'noemu_nocell' :
            USE_VIRTUAL_SENSE_HAT = False
            USE_CELL_MODEM = False
        else :
            print_usage()
            exit(0)
            
        if USE_VIRTUAL_SENSE_HAT == True :
            from sense_emu import SenseHat
            print "Using Sense Hat Emulator"
        else :
            from sense_hat import SenseHat
            print "Real Sense Hat Detected"
        SENSE = SenseHat()
        SENSE.clear()
    else:
        print_usage()
        exit(0)

def display_id(id, sense_hat, max_num_sensors) :
    if id < 1 or id > max_num_sensors :
        sense_hat.show_message("Invalid ID: " + str(id), scroll_speed = 0.05, text_colour = [255, 0, 0], back_colour = [0,0,0])
        return

    f = [255,0,0]
    b = [0,0,255]

    rgb_pixels_10 = \
        [b,b,b,b,b,b,b,b,
         b,f,b,b,f,f,b,b,
         b,f,b,f,b,b,f,b,
         b,f,b,f,b,b,f,b,
         b,f,b,f,b,b,f,b,
         b,f,b,f,b,b,f,b,
         b,f,b,b,f,f,b,b,
         b,b,b,b,b,b,b,b]

    rgb_pixels_11 = \
        [b,b,b,b,b,b,b,b,
         b,f,b,b,b,f,b,b,
         b,f,b,b,b,f,b,b,
         b,f,b,b,b,f,b,b,
         b,f,b,b,b,f,b,b,
         b,f,b,b,b,f,b,b,
         b,f,b,b,b,f,b,b,
         b,b,b,b,b,b,b,b]
         
    rgb_pixels_12 = \
        [b,b,b,b,b,b,b,b,
         b,f,b,b,f,f,b,b,
         b,f,b,f,b,b,f,b,
         b,f,b,b,b,f,b,b,
         b,f,b,b,f,b,b,b,
         b,f,b,f,b,b,b,b,
         b,f,b,f,f,f,f,b,
         b,b,b,b,b,b,b,b]

    if id < 10 :
        sense_hat.show_letter(str(id), text_colour = [255,0,0], back_colour = [0,0,255])
    elif id == 10 :
        sense_hat.set_pixels(rgb_pixels_10)
    elif id == 11 :
        sense_hat.set_pixels(rgb_pixels_11)
    elif id == 12 :
        sense_hat.set_pixels(rgb_pixels_12)

try :
    main()
except :
    #except Exception as ex:
    import traceback
    print traceback.format_exc()    
    #import pdb
    #pdb.post_mortem()
    my_ctrl_c_exit(ETH_DEV)