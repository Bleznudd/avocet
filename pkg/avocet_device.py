"""avocet device"""

from gateway_addon import Device
# from webthing import Value
from picovoice import Picovoice
from pvrecorder import PvRecorder
from datetime import datetime
from ast import literal_eval
from random import random
from time import sleep
import threading
import gtts
import json
import time
import os

from .avocet_property import avocetSwitchProperty, avocetIntentProperty
from .util import MIN_TEMPERATURE, MAX_TEMPERATURE, relative_temp_to_kelvin


_POLL_INTERVAL = 3

class avocetDevice(Device):

    def __init__(self, adapter, _id, name):
        Device.__init__(self, adapter, _id)
        self._type = []
        self.name = name
        self.adapter = adapter
        self.href = "/things/" + _id
        self.status = False
        self.intent = ""
        self.voice_service = VoiceThread(
            os.path.join(os.path.dirname(__file__), '../resources/languages/' + self.adapter.language + '/wake/' + self.adapter.wakeword + '_raspberry-pi.ppn'),
            os.path.join(os.path.dirname(__file__), '../resources/languages/' + self.adapter.language + '/default_raspberry-pi.rhn'),
            self.adapter.access_key, 
            self.set_intent
        )
        self.special_map = literal_eval(open(os.path.join(os.path.dirname(__file__), "../resources/languages/" + self.adapter.language + "/maps/special_map.txt"), "r").read())
        self.intent_to_property_map = literal_eval(open(os.path.join(os.path.dirname(__file__), "../resources/languages/" + self.adapter.language + "/maps/intent_to_property_map.txt"), "r").read())
        self.value_map = literal_eval(open(os.path.join(os.path.dirname(__file__), "../resources/languages/" + self.adapter.language + "/maps/value_map.txt"), "r").read())
        self.inv_value_map = {v: k for k, v in self.value_map.items()}
        self.alive = False
        self.switch()
        # self.voice_service.run()

        # t = threading.Thread(target=self.poll)
        # t.daemon = True
        # t.start()

    # def poll(self):
    #     """Poll the device for changes."""
    #     if not(self.voice_serviceis_alive()):
    #             self.voice_servicerun()
    #     self.voice_servicestop()
    #     self.voice_servicejoin()
    #     time.sleep(5)

    def is_on(self):
        return self.status

    def get_intent(self):
        return self.intent

    def set_intent(self, value):
        self.adapter.set_property(self.href, 'IntentProperty', json.dumps(value))

    """
    Starts and stops the wakeword listener
    """
    def switch(self):
        if not(self.alive):
            # print("STARTING HERE")
            self.voice_service.start()
            self.alive = True

        # print("SWITCHING STATUS")
        self.voice_service.pause_n_resume()
    
    """
    Generate and mp3 file and plays it
    """
    def speak(self, value):
        self.switch()
        try:
            response = gtts.gTTS(value, lang=self.adapter.language)
            response.save('response.mp3')
            os.system("ffplay -nodisp -autoexit -volume 50 response.mp3 > /dev/null 2>&1")
        except gtts.tts.gTTSError as e:
            print("COULD NOT RETRIVE FEEDBACK SPEECH")
        finally:
            self.switch()

    """
    When an intention is received, this method parse it and execute the correct command
    """
    def action(self, intent: dict):
        # print("RECEIVED INTENT IS: " + str(intent))
        if not(intent.get('is_understood')):
            return False

        if 'thing' in intent.get('slots')[0]:
            if 'location' in intent.get('slots')[0]:
                target = self.adapter.get_href(intent.get('slots')[0].get('location') + " " + intent.get('slots')[0].get('thing'))
            else:
                target = self.adapter.get_href(intent.get('slots')[0].get('thing'))
        else:
            target = None

        # print("= THING ============== " + str(target))
        prop = (self.intent_to_property_map[intent.get('intent')] if not(isinstance(self.intent_to_property_map[intent.get('intent')], dict)) else self.intent_to_property_map[intent.get('intent')][intent.get('slots')[0].get('property')])
        # print("= PROPE ============== " + str(prop))
        if not(isinstance(target, type(None))):
            if self.adapter.href_has_property(target, prop) or self.adapter.href_has_action(target, (self.value_map.get(intent.get('slots')[0].get('to')) if not(isinstance(self.value_map.get(intent.get('slots')[0].get('to')), type(None))) else intent.get('slots')[0].get('to'))):
                if intent.get('intent_type') == 0:
                    val = next(iter(self.adapter.get_property(target, prop).values()))
                    if isinstance(val, int) and not(isinstance(val, bool)):
                        val = 'at ' + str(val)
                    else:
                        val = self.inv_value_map.get(val)
                    # print(str(intent.get('slots')[0].get('thing')))
                    # print(type(val))
                    # print(str(val))
                    # print(str(next(iter(self.adapter.get_property(target, prop).values()))))
                    # print(str(self.adapter.get_property(target, prop)))
                    # print(str(self.inv_value_map))
                    self.speak('The ' + str(intent.get('slots')[0].get('thing')) + ' is ' + val)
                elif intent.get('intent_type') == 1:
                    # if not(isinstance(self.value_map.get(intent.get('slots')[0].get('to')), type(None))):
                    #     print("= VALUE ============== " + str(self.value_map.get(intent.get('slots')[0].get('to'))), type(self.value_map.get(intent.get('slots')[0].get('to'))))
                    # else:
                    #     print("= VALUE ============== " + str(intent.get('slots')[0].get('to')), type(intent.get('slots')[0].get('to')))
                    done = self.adapter.set_property(target, prop, (self.value_map.get(intent.get('slots')[0].get('to')) if not(isinstance(self.value_map.get(intent.get('slots')[0].get('to')), type(None))) else int(intent.get('slots')[0].get('to'))))
                    if done:
                        self.speak('I\'ve setted the ' + str(intent.get('slots')[0].get('thing')) + ' to ' + str(intent.get('slots')[0].get('to')))
                    else:
                        self.speak('I could not set the property')
                elif intent.get('intent_type') == 2:
                    done = self.adapter.exe_action(target, (self.value_map.get(intent.get('slots')[0].get('to')) if not(isinstance(self.value_map.get(intent.get('slots')[0].get('to')), type(None))) else intent.get('slots')[0].get('to')))
                    if done:
                        self.speak('I\'ve setted the ' + str(intent.get('slots')[0].get('thing')) + ' to ' + str(intent.get('slots')[0].get('to')))
                    else:
                        self.speak('I could not execute the action')
                else:
                    self.speak('I don\'t know this intent type')
            else:
                self.speak('I could not find the property')
        else:
            if intent.get('intent_type') == 3:
                self.speak(eval(self.special_map.get(intent.get('intent'))[int(random()*len(self.special_map.get(intent.get('intent'))))]))
            else:
                self.speak('I could not find the device')
        return True
        
class VoiceThread(threading.Thread):
    def __init__(
            self,
            keyword_path,
            context_path,
            access_key,
            set_function,
            porcupine_sensitivity=0.65,
            rhino_sensitivity=0.25):
        super(VoiceThread, self).__init__()

        def inference_callback(inference):
            return self._inference_callback(inference)

        self._picovoice = Picovoice(
            access_key=access_key,
            keyword_path=keyword_path,
            wake_word_callback=self._wake_word_callback,
            context_path=context_path,
            inference_callback=inference_callback,
            porcupine_sensitivity=porcupine_sensitivity,
            rhino_sensitivity=rhino_sensitivity)

        self.daemon = True
        self._context = self._picovoice.context_info
        self.paused = False
        self.wasactive = False
        self.set_function = set_function

    @staticmethod
    def _wake_word_callback():
        os.system('aplay /home/pi/.webthings/addons/avocet/resources/sounds/ding-high.wav > /dev/null 2>&1')
        print('[wake word]')

    def _inference_callback(self, inference):
        if inference.is_understood:
            th = threading.Thread(target=lambda: os.system('aplay /home/pi/.webthings/addons/avocet/resources/sounds/ding-low.wav > /dev/null 2>&1'))
        else:
            th = threading.Thread(target=lambda: os.system('aplay /home/pi/.webthings/addons/avocet/resources/sounds/error.wav > /dev/null 2>&1'))
        th.start()
        if inference.is_understood:
            response = {
                "is_understood" : inference.is_understood,
                "intent_type" : (0 if inference.intent[:3] == "get" else (1 if inference.intent[:3] == "set" else (2 if inference.intent[:3] == "exe" else 3))), # get = 0, set = 1, action = 2, special = 3
                "intent" : inference.intent,
                "slots" : [{}]
            }
            response 
            for slot, value in inference.slots.items():
                response.get('slots')[0][slot] = value
            for slot in response.get('slots'):
                if 'status' in slot:
                    slot['to'] = slot.pop('status')
                if 'color' in slot:
                    slot['to'] = slot.pop('color')
                if 'value' in slot:
                    slot['to'] = slot.pop('value')
                if 'heat' in slot:
                    slot['to'] = slot.pop('heat')
                if 'action' in slot:
                    slot['to'] = slot.pop('action')
        else:
            response = {
                "is_understood" : inference.is_understood,
            }
        self.set_function(response)
        th.join()
    
    def run(self):
        recorder = None
        try:
            recorder = PvRecorder(device_index=-1, frame_length=self._picovoice.frame_length)
            recorder.start()
            # print(self._context)
            print('[Listening ...]')
            while True:
                if not(self.paused) and not(self.wasactive):
                    pcm = recorder.read()
                    self._picovoice.process(pcm)
                elif self.paused and not(self.wasactive):
                    recorder.stop()
                    self.wasactive = not(self.wasactive)
                elif not(self.paused) and self.wasactive:
                    recorder.start()
                    self.wasactive = not(self.wasactive)
                else:
                    sleep(1)
        except (KeyboardInterrupt, SystemExit):
            sys.stdout.write('\b' * 2)
            print('Stopping ...')
        finally:
            if recorder is not None:
                recorder.delete()

            self._picovoice.delete()

    def pause_n_resume(self):
        self.wasactive = self.paused
        self.paused = not(self.paused)


class avocetSwitch(avocetDevice):

    def __init__(self, adapter, _id, name):
        avocetDevice.__init__(self, adapter, _id, name)
        self._type.extend(['OnOffSwitch'])

        self.properties['on'] = avocetSwitchProperty(
            self,
            'on',
            {
                '@type': 'OnOffProperty',
                'title': 'On/Off',
                'type': 'boolean',
            },
            self.is_on()
        )

        self.properties['intent'] = avocetIntentProperty(
            self,
            'intent',
            {
                '@type': 'IntentProperty',
                'title': 'Last Intent',
                'type': 'string',
                'visible': False,
            },
            self.get_intent(),
        )

"""
EXAMPLE OF VALID JSON FOR SETTING THE INTENT PROPERTY

{
    "is_understood": true,
    "intent_type":1,
    "intent" : "setOnOffProperty",
    "slots" : [{
        "to" : "off",
        "thing" : "radio"
    }]
}

OR AS A ONELINER

{"is_understood": true, "intent_type":1, "intent" : "setOnOffProperty", "slots" : [{"to" : "off", "thing" : "radio"}]}

"""