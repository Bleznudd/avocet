"""avocet adapter"""

from gateway_addon import Adapter, Database
from .avocet_device import avocetSwitch
import requests
import json

_TIMEOUT = 3


class avocetAdapter(Adapter):

    def __init__(self, verbose=False):
        self.name = self.__class__.__name__
        Adapter.__init__(self,
                         'avocet',
                         'avocet',
                         verbose=verbose)
        self.api_server = 'http://127.0.0.1:8080'

        database = Database(self.package_name)
        if database.open():
            config = database.load_config()
            if 'token' in config and len(config['token']) > 0:
                self.token = config['token']
            else:
                self.token='eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IjJhOTQ2MjMzLWVjNzUtNGM3OS05NzdkLWFhOGU3YmMwNzY2NyJ9.eyJjbGllbnRfaWQiOiJsb2NhbC10b2tlbiIsInJvbGUiOiJhY2Nlc3NfdG9rZW4iLCJzY29wZSI6Ii90aGluZ3M6cmVhZHdyaXRlIiwiaWF0IjoxNjQzMzY0Mjk5LCJpc3MiOiJOb3Qgc2V0LiJ9.5mvh7KLCF6TPgC075LtfwaSV7C3tpxpiiRLZtSR40eG9DwfCbr8QunJJ8Q9QLTfM6bHiQfBOXy8AtNKwVTIeDw'
            self.language = config['language']
            self.wakeword = config['wakeword']
            self.access_key = config['access_key']
            self.pitch = config['pitch']
            database.close()

        self.things = self.get_things()

        _id = 'main-voice-assistant-device'
        if _id not in self.devices:
            name = "Voice assistant"
            try:
                self.device = avocetSwitch(self, _id, name)
            except OSError:
                pass
            else:
                self.handle_device_added(self.device)


    # HIGH LEVEL INTERACTION METHODS

    def get_things(self):
        # print('RETRIVING THINGS')
        return self.api_get('/things')

    def get_href(self, title: str):
        try:
            self.things = self.get_things()
            for thing in self.things:
                if thing.get('title').lower() == title.lower():
                    return thing.get('href')
        except (TypeError, AttributeError):
            print("CANNOT FIND: ", title)

    def href_has_property(self, href: str, proptype: str):
        for i in self.get_properties(href):
            if i == proptype:
                return True
        return False

    def href_has_action(self, href: str, action: str):
        for i in self.get_actions(href):
            if i == action:
                return True
        return False

    def get_properties(self, href: str):
        props = []
        for prop in self.api_get(href).get('properties'):
            props.append(self.api_get(href).get('properties').get(prop).get('@type'))
        return props

    def get_actions(self, href: str):
        acts = []
        for act in self.api_get(href).get('actions'):
            acts.append(act)
        return acts

    def get_property(self, href: str, proptype: str):
        # print("yes you are calling me")
        # print("with these values: ", href, proptype, value)
        # print("and I got: ", str(self.api_get(href).get('properties')))
        propname = ""
        for prop in self.api_get(href).get('properties'):
            # print("prop cycle: " + str(prop))
            if self.api_get(href).get('properties').get(prop).get('@type') == proptype:
                # print("found the right one")
                propname = prop
                break
        if propname:
            # print(href + '/properties/' + propname + '  ->  ' + str({propname:value}))
            return self.api_get(href + '/properties/' + propname)
        return False

    def set_property(self, href: str, proptype: str, value):
        # print("yes you are calling me")
        # print("with these values: ", href, proptype, value)
        # print("and I got: ", str(self.api_get(href).get('properties')))
        propname = ""
        for prop in self.api_get(href).get('properties'):
            # print("prop cycle: " + str(prop))
            if self.api_get(href).get('properties').get(prop).get('@type') == proptype:
                # print("found the right one")
                propname = prop
                break
        if propname:
            # print(href + '/properties/' + propname + '  ->  ' + str({propname:value}))
            return self.api_put(href + '/properties/' + propname, {propname:value})
        return False

    def exe_action(self, href: str, action: str, value: dict):
        # print("yes you are calling me")
        # print("with these values: ", href, action, value)
        # print("and I got: ", str(self.api_get(href).get('actions')))
        actname = ""
        for act in self.api_get(href).get('actions'):
            if act == action:
                # print("found the right one")
                actname = act
                break
        if actname:
            return self.api_post(href + '/actions/' + actname, {actname:{'input':value}})
        return False

    # LOW LEVEL INTERACTION METHODS

    def api_get(self, api_path):
        try:
            # print("---------- GETTING : " + self.api_server + api_path)
            r = requests.get(self.api_server + api_path, headers={
                        'Accept': 'application/json',
                        'Authorization': 'Bearer ' + str(self.token),
                    }, verify=False, timeout=3)
            return json.loads(r.text)
            
        except Exception as ex:
            print("Error in http GET, returned json: " + str(ex))
            return {"error": "not available"}

    def api_put(self, api_path, json_dict):
        try:
            print("---------- SENDING: " + str(json.dumps(json_dict)))
            print("--------- TO THING: " + self.api_server + api_path)
            r = requests.put(self.api_server + api_path, headers={
                        'Content-type': 'application/json',
                        'Accept': 'application/json',
                        'Authorization': 'Bearer ' + str(self.token),
                    },
                    data=json.dumps(json_dict),
                    verify=False,
                    timeout=5
            )
            # return_value['succes'] = True
            return (True if r.status_code == 200 else False)

        except Exception as ex:
            print("Error in http PUT, returned json: " + str(ex))
            return {"error": 500}

    def api_post(self, api_path, json_dict):
        try:
            print("---------- SENDING: " + str(json.dumps(json_dict)))
            print("--------- TO THING: " + self.api_server + api_path)
            r = requests.post(self.api_server + api_path, headers={
                        'Content-type': 'application/json',
                        'Accept': 'application/json',
                        'Authorization': 'Bearer ' + str(self.token),
                    },
                    data=json.dumps(json_dict),
                    verify=False,
                    timeout=5
            )
            # return_value['succes'] = True
            return (True if r.status_code == 201 else False)

        except Exception as ex:
            print("Error in http POST, returned json: " + str(ex))
            return {"error": 500}
