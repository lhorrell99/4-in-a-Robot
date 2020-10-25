from gpiozero import DigitalOutputDevice
from time import sleep


class Stepper:
    def __init__(self, d, s, r):
        """
        param d: GPIO direction pin
        param s: GPIO step pin
        param r: stepper resolution (steps per revolution)
        current_position: stepper location (relative to initialize location)
        """
        self.d = DigitalOutputDevice(d)
        self.s = DigitalOutputDevice(s)
        self.r = r
        self.current_position = 0

    def turn(self, revs, speed=1):
        """
        param revs: number of revolutions to turn (+ve CW or -ve CCW)
        param speed: (approx) speed (rps)
        """
        pulses = self.__get_pulses(revs)
        delay = self.__get_delay(speed)
        self.d.value = 0 if revs > 0 else 1
        for pulse in range(pulses):
            self.s.on()
            sleep(delay)
            self.s.off()
            sleep(delay)
        self.current_position += revs

    def return_home(self):
        # return stepper to initialize location
        if self.current_position:   # if not already at zero position
            self.turn(-self.current_position)

    def __get_delay(self, speed):
        # convert speed (rps) to time dela
        return 1 / (2 * self.r * speed)

    def __get_pulses(self, revs):
        # converts revolutions to pulse count
        return int(abs(self.r * revs))
