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
        self.switch_listening_status()

    def update(self):
        if self.name != 'on':
            return

        value = self.device.is_on()
        if value != self.value:
            self.set_cached_value(value)
            self.device.notify_property_changed(self)

    def switch_listening_status(self):
        self.device.switch()

class avocetIntentProperty(avocetProperty):

    def set_value(self, value):
        if self.name != 'intent':
            return

        self.set_state(value)
        self.set_cached_value(value)
        self.device.notify_property_changed(self)
        self.intent_changed(value)

    def update(self):
        if self.name != 'intent':
            return

        value = self.device.get_intent()
        if value != self.value:
            self.set_cached_value(value)
            self.device.notify_property_changed(self)

    def intent_changed(self, value):
        self.device.action(json.loads(value))