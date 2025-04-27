from machine import Pin, PWM, I2C, TouchPad
import time

# ========= DC MOTOR SETUP ==========

# PWM pins
MOTOR_X_PWM = PWM(Pin(5), freq=700, duty=700)
MOTOR_Y_PWM = PWM(Pin(18), freq=700, duty=700)
MOTOR_Z_PWM = PWM(Pin(19), freq=700, duty=700)

# Direction pins
MOTOR_X_IN1 = Pin(12, Pin.OUT)
MOTOR_X_IN2 = Pin(13, Pin.OUT)
MOTOR_Y_IN3 = Pin(14, Pin.OUT)
MOTOR_Y_IN4 = Pin(27, Pin.OUT)
MOTOR_Z_IN1 = Pin(26, Pin.OUT)
MOTOR_Z_IN2 = Pin(25, Pin.OUT)

# ========== Motor Direction Functions ==========


def motor_drive(pin_a, pin_b):
    pin_a.value(1)
    pin_b.value(0)


def motor_stop(pin_a, pin_b):
    pin_a.value(0)
    pin_b.value(0)


# X axis
def motor_x_cw():
    motor_drive(MOTOR_X_IN1, MOTOR_X_IN2)


def motor_x_ccw():
    motor_drive(MOTOR_X_IN2, MOTOR_X_IN1)


def motor_x_stop():
    motor_stop(MOTOR_X_IN1, MOTOR_X_IN2)


# Y axis
def motor_y_cw():
    motor_drive(MOTOR_Y_IN3, MOTOR_Y_IN4)


def motor_y_ccw():
    motor_drive(MOTOR_Y_IN4, MOTOR_Y_IN3)


def motor_y_stop():
    motor_stop(MOTOR_Y_IN3, MOTOR_Y_IN4)


# Z axis
def motor_z_down():
    motor_drive(MOTOR_Z_IN1, MOTOR_Z_IN2)


def motor_z_up():
    motor_drive(MOTOR_Z_IN2, MOTOR_Z_IN1)


def motor_z_stop():
    motor_stop(MOTOR_Z_IN1, MOTOR_Z_IN2)


# ========== Servo Setup ==========


class PCA9685:
    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.addr = address
        self.i2c.writeto_mem(self.addr, 0x00, b"\x00")
        self.set_pwm_freq(50)

    def set_pwm_freq(self, freq):
        prescale = int(25000000 / (4096 * freq) - 1)
        old = self.i2c.readfrom_mem(self.addr, 0x00, 1)[0]
        self.i2c.writeto_mem(self.addr, 0x00, bytes([(old & 0x7F) | 0x10]))
        self.i2c.writeto_mem(self.addr, 0xFE, bytes([prescale]))
        self.i2c.writeto_mem(self.addr, 0x00, bytes([old]))
        time.sleep_ms(5)
        self.i2c.writeto_mem(self.addr, 0x00, bytes([old | 0xA1]))

    def set_pwm(self, ch, on, off):
        reg = 0x06 + 4 * ch
        data = bytes([on & 0xFF, on >> 8, off & 0xFF, off >> 8])
        self.i2c.writeto_mem(self.addr, reg, data)

    def set_servo_angle(self, ch, angle):
        pulse = int(102 + (512 - 102) * angle / 180)
        self.set_pwm(ch, 0, pulse)


# init I2C + servo driver
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
pca = PCA9685(i2c)


def grab():
    print("→ Lowering Z Axis (anticlockwise)")
    motor_z_down()
    time.sleep(2.5)
    motor_z_stop()

    print("→ Closing Claw")
    pca.set_servo_angle(0, 0)
    time.sleep(0.2)

    print("→ Raising Z Axis (clockwise)")
    motor_z_up()
    time.sleep(2.5)
    motor_z_stop()

    print("→ Neutral Claw")
    pca.set_servo_angle(0, 90)
    time.sleep(0.1)


def release():
    motor_z_down()
    time.sleep(0.5)
    motor_z_stop()
    pca.set_servo_angle(0, 180)
    time.sleep(0.3)
    pca.set_servo_angle(0, 90)
    time.sleep(0.2)


# ========== Touch Setup ==========

touch_x_cw = TouchPad(Pin(4))
touch_x_ccw = TouchPad(Pin(2))
touch_y_cw = TouchPad(Pin(33))
touch_y_ccw = TouchPad(Pin(32))
touch_grab = TouchPad(Pin(15))

touches = {
    "x_cw": touch_x_cw,
    "x_ccw": touch_x_ccw,
    "y_cw": touch_y_cw,
    "y_ccw": touch_y_ccw,
    "grab": touch_grab,
}

THRESHOLD = 200
print("Touch-control Claw ready. Threshold =", THRESHOLD)

# ========== MAIN LOOP ==========

while True:
    readings = {}
    for name, pin in touches.items():
        try:
            value = pin.read()
            print("TOUCH HH: ", value)
        except Exception as e:
            print(f"TouchPad {name} error: {e}")
            value = 1000  # Treat as not touched
        readings[name] = value
        print(f"{name} = {value}")
    # Handle X axis
    if readings["x_cw"] < THRESHOLD:
        print("→ X Clockwise")
        motor_x_cw()
    elif readings["x_ccw"] < THRESHOLD:
        print("→ X AntiClockwise")
        motor_x_ccw()
    else:
        motor_x_stop()
    # Handle Y axis
    if readings["y_cw"] < THRESHOLD:
        print("→ Y Clockwise")
        motor_y_cw()
    elif readings["y_ccw"] < THRESHOLD:
        print("→ Y AntiClockwise")
        motor_y_ccw()
    else:
        motor_y_stop()
    # Handle Z axis + Claw grab
    if readings["grab"] < THRESHOLD:
        print("→ Claw Grab/Release Triggered")
        grab()
        time.sleep(0.4)
        release()
    time.sleep(0.05)  # Reduce jitter but keep responsiveness
