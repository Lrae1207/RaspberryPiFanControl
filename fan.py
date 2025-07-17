# based on https://blog.driftking.tw/en/2019/11/Using-Raspberry-Pi-to-Control-a-PWM-Fan-and-Monitor-its-Speed/#Use-PWM-to-Control-Fan-Speed
import RPi.GPIO as GPIO
import time
import signal
import sys

PWM_FREQ = 25

# LEDS
TEMP_LED_RED = 17
TEMP_LED_YELLOW = 27
TEMP_LED_GREEN = 22

RPM_LED_LOW = 16
RPM_LED_MED = 20
RPM_LED_HIGH = 21

FAN_PIN = 18
WAIT_TIME = 1

# RPM Measurement
TACH_PIN = 24
PULSE = 2
RPM_THRESH_LOW = 300
RPM_THRESH_HIGH  = 700

# Behavior
OFF_TEMP = 40   # Celcius; temperature under which to disable
MIN_TEMP = 45   # Celcius; temperature above which to start
MAX_TEMP = 70   # Celcius; temperature above which to operate at FAN_HIGH
FAN_LOW = 40    # on minimum power level
FAN_HIGH = 100  # on max power level
FAN_OFF = 25    # off fan power level
FAN_GAIN = float(FAN_HIGH - FAN_LOW) / float(MAX_TEMP - MIN_TEMP)

t0 = time.time()
rpm = 0

def getFanRPM(n):
    global t0
    global rpm

    t1 = time.time()
    dt = t1 - t0
    if dt < 0.005: 
        return

    freq = 1 / dt
    rpm = (freq / PULSE) * 60
    t0 = time.time()

def getCpuTemperature():
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        return float(f.read()) / 1000

def handleRPMLEDs():
    global rpm
    if rpm > RPM_THRESH_HIGH:
        GPIO.output(RPM_LED_HIGH, 1)
        GPIO.output(RPM_LED_MED, 0)
        GPIO.output(RPM_LED_LOW, 0)
        return
    if rpm > RPM_THRESH_LOW:
        GPIO.output(RPM_LED_HIGH, 0)
        GPIO.output(RPM_LED_MED, 1)
        GPIO.output(RPM_LED_LOW, 0)
        return
    GPIO.output(RPM_LED_HIGH, 0)
    GPIO.output(RPM_LED_MED, 0)
    GPIO.output(RPM_LED_LOW, 1)

def handleTempLEDs(temperature):
    if temperature > MAX_TEMP:
        GPIO.output(TEMP_LED_RED, 1)
        GPIO.output(TEMP_LED_YELLOW, 0)
        GPIO.output(TEMP_LED_GREEN, 0)
        return
    if temperature > MIN_TEMP:
        GPIO.output(TEMP_LED_RED, 0)
        GPIO.output(TEMP_LED_YELLOW, 1)
        GPIO.output(TEMP_LED_GREEN, 0)
        return
    GPIO.output(TEMP_LED_RED, 0)
    GPIO.output(TEMP_LED_YELLOW, 0)
    GPIO.output(TEMP_LED_GREEN, 1)


def handleFanSpeed(fan, temperature):
    if temperature > MIN_TEMP:
        delta = min(temperature, MAX_TEMP) - MIN_TEMP
        fan.start(FAN_LOW + delta * FAN_GAIN)

    elif temperature < OFF_TEMP:
        fan.start(FAN_OFF)

try:
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(FAN_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(TACH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(TACH_PIN, GPIO.FALLING, getFanRPM)
    
    GPIO.setup(TEMP_LED_RED, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(TEMP_LED_YELLOW, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(TEMP_LED_GREEN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(RPM_LED_HIGH, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(RPM_LED_MED, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(RPM_LED_LOW, GPIO.OUT, initial=GPIO.LOW)
    
    fan = GPIO.PWM(FAN_PIN, PWM_FREQ)
    while True:
        temp = getCpuTemperature()
        handleTempLEDs(temp)
        handleFanSpeed(fan, temp)
        time.sleep(WAIT_TIME)
        handleRPMLEDs()
        print("%.f rpm" % rpm)
        print("%.f c" % temp)
        rpm = 0

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
