"""avocet device"""

from gateway_addon import Device, Action
# from webthing import Value
from picovoice import Picovoice
from pvrecorder import PvRecorder
from datetime import datetime
from ast import literal_eval
from random import random
from time import sleep
import traceback
import threading
import gtts
import json
import time
import os

from .avocet_property import avocetSwitchProperty, avocetVolumeProperty
# from .led import Led

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
        self.volume = 50 #%
        self.voice_service = VoiceThread(
            # Wakewords are currently in english also for other languages, except Italian though we only have "avocet" available
            os.path.join(os.path.dirname(__file__), '../resources/languages/' + self.adapter.language + '/wake/' + self.adapter.wakeword + '_raspberry-pi.ppn'),
            os.path.join(os.path.dirname(__file__), '../resources/languages/' + self.adapter.language + '/default_raspberry-pi.rhn'),
            os.path.join(os.path.dirname(__file__), '../resources/languages/' + self.adapter.language + '/porcupine_params_' + self.adapter.language + '.pv'),
            os.path.join(os.path.dirname(__file__), '../resources/languages/' + self.adapter.language + '/rhino_params_' + self.adapter.language + '.pv'),
            self.adapter.access_key, 
            self.set_intent
        )
        self.responses = literal_eval(open(os.path.join(os.path.dirname(__file__), "../resources/languages/" + self.adapter.language + "/maps/responses.txt"), "r").read())
        self.special_map = literal_eval(open(os.path.join(os.path.dirname(__file__), "../resources/languages/" + self.adapter.language + "/maps/special_map.txt"), "r").read())
        self.intent_to_property_map = literal_eval(open(os.path.join(os.path.dirname(__file__), "../resources/languages/" + self.adapter.language + "/maps/intent_to_property_map.txt"), "r").read())
        self.value_map = literal_eval(open(os.path.join(os.path.dirname(__file__), "../resources/languages/" + self.adapter.language + "/maps/value_map.txt"), "r").read())
        self.inv_value_map = {v: k for k, v in self.value_map.items()}
        self.alive = False
        self.hat = os.path.isdir('/proc/device-tree/wm8960_mclk') # True is respeaker drivers are installed
        self.set_status()

        os.system("rm /dev/shm/response.mp3 > /dev/null 2>&1")
        self.save(self.responses[13], '/dev/shm/backup.mp3')

        # self.led = (Led() if self.hat else False)

    def get_status(self):
        return self.status

    def get_volume(self):
        return self.volume

    """
    Starts and stops the wakeword listener
    """
    def set_status(self):
        if not(self.alive):
            # print("STARTING HERE")
            self.voice_service.start()
            self.alive = True

        # print("SWITCHING STATUS")
        self.voice_service.pause_n_resume()

    """
    Adjust the volume of the speech
    """
    def set_volume(self, value):
        self.volume = value

    """
    Send the action/intent request
    """
    def set_intent(self, value):
        self.adapter.exe_action(self.href, 'new-intent', value)

    """
    Generate and save an mp3 file
    """
    def save(self, value, path):
        try:
            response = gtts.gTTS(value, lang=self.adapter.language)
            response.save(path)
            return True
        except gtts.tts.gTTSError:
            print("COULD NOT RETRIEVE FEEDBACK SPEECH")
            return False
    
    """
    Play an mp3 file
    """
    def speak(self, value):
        rate = str(48000*0.5*float(self.adapter.pitch))
        tempo = str(1.0/float(self.adapter.pitch))
        # if self.hat:
        #     self.led.wake()
        if self.save(value, '/dev/shm/response.mp3'):
            cmd = "ffplay -nodisp -autoexit -volume {0} -af asetrate={1},atempo={2},aresample=48000 -i /dev/shm/response.mp3 > /dev/null 2>&1".format(str(self.volume), rate, tempo)
            os.system(cmd)
        elif os.path.isfile('/dev/shm/backup.mp3'):
            cmd = "ffplay -nodisp -autoexit -volume {0} -af asetrate={1},atempo={2},aresample=48000 -i /dev/shm/backup.mp3 > /dev/null 2>&1".format(str(self.volume), rate, tempo)
            os.system(cmd)
        else:
            print("NO BACKUP AUDIO FOUND")
        # if self.hat:
        #     self.led.sleep()

    """
    When an intention is received, this method parse it and execute the correct command
    """
    def action(self, intent: dict):
        if not(intent.get('is_understood')):
            return False

        try:
            if 'thing' in intent.get('slots')[0]:
                if 'location' in intent.get('slots')[0]:
                    target = self.adapter.get_href(intent.get('slots')[0].get('location') + " " + intent.get('slots')[0].get('thing'))
                    if isinstance(target, type(None)):
                        target = self.adapter.get_href(intent.get('slots')[0].get('thing') + " " + intent.get('slots')[0].get('location'))
                else:
                    target = self.adapter.get_href(intent.get('slots')[0].get('thing'))
            else:
                target = None

            prop = (self.intent_to_property_map[intent.get('intent')] if not(isinstance(self.intent_to_property_map[intent.get('intent')], dict)) else self.intent_to_property_map[intent.get('intent')][intent.get('slots')[0].get('property')])
            if prop == 'FirstProperty' and not(isinstance(target, type(None))):
                props = self.adapter.get_properties(target)
                if 'OnOffProperty' in props:
                    prop = 'OnOffProperty'
                elif len(props) > 0:
                    prop = props[0]

            if not(isinstance(target, type(None))):
                if self.adapter.href_has_property(target, prop) or self.adapter.href_has_action(target, (self.value_map.get(intent.get('slots')[0].get('to')) if not(isinstance(self.value_map.get(intent.get('slots')[0].get('to')), type(None))) else intent.get('slots')[0].get('to'))):
                    if intent.get('intent_type') == 0:
                        val = next(iter(self.adapter.get_property(target, prop).values()))
                        if isinstance(val, int) and not(isinstance(val, bool)):
                            val = self.responses[2] + str(val)
                        else:
                            val = self.inv_value_map.get(val)
                        self.speak(self.responses[0] + str(intent.get('slots')[0].get('thing')) + self.responses[1] + val)
                    elif intent.get('intent_type') == 1:
                        done = self.adapter.set_property(target, prop, (self.value_map.get(intent.get('slots')[0].get('to')) if not(isinstance(self.value_map.get(intent.get('slots')[0].get('to')), type(None))) else int(intent.get('slots')[0].get('to'))))
                        if done:
                            # "I've setted the thing to [val]"
                            self.speak(self.responses[7] + str(intent.get('slots')[0].get('thing')) + self.responses[3] + str(intent.get('slots')[0].get('to')))
                        else:
                            # "I could not set the property"
                            self.speak(self.responses[8] + self.responses[4])
                    elif intent.get('intent_type') == 2:
                        # TODO: ad a value parameter, only empty input actions are currently supported
                        done = self.adapter.exe_action(target, (self.value_map.get(intent.get('slots')[0].get('to')) if not(isinstance(self.value_map.get(intent.get('slots')[0].get('to')), type(None))) else intent.get('slots')[0].get('to')), {})
                        if done:
                            # "I've setted the thing to [val]"
                            self.speak(self.responses[7] + str(intent.get('slots')[0].get('thing')) + self.responses[3] + str(intent.get('slots')[0].get('to')))
                        else:
                            # "I've setted execute the action"
                            self.speak(self.responses[10] + self.responses[6])
                    else:
                        # "I don't know this intent type"
                        self.speak(self.responses[11])
                else:
                    # "I could not find the property"
                    self.speak(self.responses[9] + self.responses[4])
            else:
                if intent.get('intent_type') == 3:
                    self.set_status()
                    self.speak(eval(self.special_map.get(intent.get('intent'))[int(random()*len(self.special_map.get(intent.get('intent'))))]))
                    self.set_status()
                else:
                    # "I could not find the device"
                    self.speak(self.responses[9] + self.responses[5])
            return True
        except Exception as e:
            print(traceback.format_exc())
            # "I've encountered an unexpected error"
            self.speak(self.responses[12])
            return False
        
class VoiceThread(threading.Thread):
    def __init__(
            self,
            keyword_path,
            context_path,
            porcupine_model_path, 
            rhino_model_path,
            access_key,
            set_function,
            porcupine_sensitivity=0.75,
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
            rhino_sensitivity=rhino_sensitivity,
            porcupine_model_path=porcupine_model_path,
            rhino_model_path=rhino_model_path
            )

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
                "intent" : inference.intent.split('_')[0],
                "slots" : [{}]
            }
            response 
            for slot, value in inference.slots.items():
                response.get('slots')[0][slot] = value
            if len(inference.intent.split('_')) > 1:
                response.get('slots')[0][inference.intent.split('_')[1]] = inference.intent.split('_')[2]
            for slot in response.get('slots'):
                for i in ['status', 'color', 'value', 'heat', 'action']:
                    if i in slot:
                        slot['to'] = slot.pop(i)
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
            self.get_status()
        )

        self.properties['volume'] = avocetVolumeProperty(
            self,
            'volume',
            {
                '@type': 'LevelProperty',
                'title': 'Volume',
                'type': 'integer',
                'minimum': 0,
                'maximum': 100
            },
            self.get_volume()
        )

        self.actions['new-intent'] = {
            'title': 'New Intent',
            'description': 'Send a new intent',
            'input': {
                'type': 'object',
                'required': [
                    'intent',
                ],
                'properties': {
                    'intent': {
                        'type': 'string',
                    },
                    'thing': {
                        'type': 'string',
                    },
                    'location': {
                        'type': 'string',
                    },
                    'property': {
                        'type': 'string',
                    },
                    'to': {
                        'type': 'string',
                    },
                },
            }
        }

    def request_action(self, action_id, action_name, action_input):
        if action_name not in self.actions:
            return

        metadata = self.actions[action_name]
        action = Action(action_id, self, action_name, action_input)
        self.perform_action(action)

    def perform_action(self, action):
        if str(action.name) == 'new-intent':
            if not(isinstance(action.input.get('is_understood'), type(None))):
                # The intention comes from avocet voice thread
                pass
            else:
                # The intention comes from the webthings UI
                action.input['is_understood'] = True
                action.input['intent_type'] = (0 if action.input['intent'][:3] == "get" else (1 if action.input['intent'][:3] == "set" else (2 if action.input['intent'][:3] == "exe" else 3))) # get = 0, set = 1, action = 2, special = 3
                action.input['slots'] = []
                action.input['slots'].append({})
                for i in ['property', 'thing', 'location', 'to']:
                    if i in action.input:
                        action.input['slots'][0][i] = action.input.pop(i)
            self.action(action.input)

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