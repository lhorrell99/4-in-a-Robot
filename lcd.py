from gpiozero import DigitalOutputDevice
from time import sleep


class CharLCD:
    # lightweight Hitachi HD44780 LCD controller class

    def __init__(self, rs, en, d4, d5, d6, d7, delay=0.001):
        self.rs = DigitalOutputDevice(rs)
        self.en = DigitalOutputDevice(en)
        self.pins = [
            DigitalOutputDevice(d4),
            DigitalOutputDevice(d5),
            DigitalOutputDevice(d6),
            DigitalOutputDevice(d7)
        ]
        self.delay = delay
        self.reset()

    def en_pulse(self):
        # enable pin pulse (to send commands/data)
        sleep(self.delay)
        self.en.value = 1
        sleep(self.delay)
        self.en.value = 0
        sleep(self.delay)

    def write_data(self, data, rs_value):
        self.rs.value = rs_value
        sleep(self.delay)

        for i, pin in enumerate(self.pins):
            # set high order data bits
            pin.value = 1 if ((data >> i + 4) & 1) else 0
        self.en_pulse()

        for i, pin in enumerate(self.pins):
            # set low order data bits
            pin.value = 1 if ((data >> i) & 1) else 0
        self.en_pulse()

    def clear(self):
        # clear screen
        self.write_data(int('00000001', 2), 0)

    def reset(self):
        # initialize chip into 4-bit interface mode
        self.write_data(int('00110011', 2), 0)
        self.write_data(int('00110010', 2), 0)

        # function set
        self.write_data(int('00101000', 2), 0)

        # display controls
        self.write_data(int('00001100', 2), 0)

        # clear display
        self.clear()

        # entry mode set
        self.write_data(int('00000110', 2), 0)

    def disp_msg(self, msg):
        '''
        clear screen and write a message to the display
        msg[0]: line 1 of message to display (max 16 char string)
        msg[1]: line 2 of message to display (max 16 char string)
        '''
        self.clear()

        for char in msg[0]:
            # print first line to display
            self.write_data(ord(char), 1)

        # move cursor to line 2
        self.write_data(int('11000000', 2), 0)

        for char in msg[1]:
            # print second line to display
            self.write_data(ord(char), 1)
