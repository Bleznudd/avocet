"""
The code is based on https://github.com/respeaker/mic_hat/blob/master/interfaces

This code is not in use at the moment due to it's license

License: GPL V2
"""


import threading
import queue
import time

from .apa102 import APA102

class Led:

    PIXELS_N = 3

    def __init__(self):
        self.basis = [0] * 3 * self.PIXELS_N

        self.basis[0] = 1

        self.dev = APA102(num_led=self.PIXELS_N)
        self.next = threading.Event()
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def wake(self, direction=0):
        self.next.set()
        self.queue.put(lambda: self.dev.set_pixel_rgb(0, 0xFFFFFF))
        self.queue.put(lambda: self.dev.set_pixel_rgb(1, 0xFFFFFF))
        self.queue.put(lambda: self.dev.set_pixel_rgb(2, 0xFFFFFF))

    def cycle(self):
        self.next.set()
        self.queue.put(lambda: self.dev.rotate(1))

    def sleep(self, direction=0):
        self.next.set()
        self.queue.put(lambda: self.dev.set_pixel_rgb(0, 0x000000))
        self.queue.put(lambda: self.dev.set_pixel_rgb(1, 0x000000))
        self.queue.put(lambda: self.dev.set_pixel_rgb(2, 0x000000))

    def stop(self):
        self.queue.put(lambda: self.dev.cleanup())

    def _run(self):
        while True:
            func = self.queue.get()
            func()
            self.dev.show()
            time.sleep(0.35)
        
