from gpiozero import Servo
from time import sleep


class ExtendedServo(Servo):
    """
    - extension of Servo class to include return_ticket method
    - also adjusts min_pulse_width and max_pulse_width defaults
    """

    def __init__(self, pin, home_value, min_pw=0.0002, max_pw=0.002):
        super().__init__(pin, min_pulse_width=min_pw, max_pulse_width=max_pw)
        self.home_value = home_value
        self.value = home_value
        sleep(0.05)     # allow time for servo movement
        self.detach()

    def return_ticket(self, disp_value, stopover):
        # displace servo then return to home position
        self.value = disp_value
        sleep(stopover)
        self.value = self.home_value
        sleep(0.05)
        self.detach()

    def reset(self):
        self.value = self.home_value
        sleep(0.05)
        self.detach()
