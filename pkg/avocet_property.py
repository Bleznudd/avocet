"""avocet properties"""

from gateway_addon import Property
import json

class avocetProperty(Property):

    def __init__(self, device, name, description, value):
        Property.__init__(self, device, name, description)
        self.set_cached_value(value)

    def set_state(self, value):
        self.device.status = value

class avocetSwitchProperty(avocetProperty):

    def set_value(self, value):
        if self.name != 'on':
            return

        self.set_state(value)
        self.set_cached_value(value)
        self.device.notify_property_changed(self)
        self.switch_changed()

    def update(self):
        if self.name != 'on':
            return

        value = self.device.is_on()
        if value != self.value:
            self.set_cached_value(value)
            self.device.notify_property_changed(self)

    def switch_changed(self):
        self.device.switch()

class avocetVolumeProperty(avocetProperty):

    def set_value(self, value):
        if self.name != 'volume':
            return

        self.set_state(value)
        self.set_cached_value(value)
        self.device.notify_property_changed(self)
        self.volume_changed(value)

    def update(self):
        if self.name != 'volume':
            return

        value = self.device.get_volume()
        if value != self.value:
            self.set_cached_value(value)
            self.device.notify_property_changed(self)

    def volume_changed(self, value):
        self.device.adjust(value)