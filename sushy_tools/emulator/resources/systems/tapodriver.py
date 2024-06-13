#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import random
import time
import amt.client
import amt.wsman
from PyP100 import PyP100

from sushy_tools.emulator import memoize
from sushy_tools.emulator.resources.systems.base import AbstractSystemsDriver
from sushy_tools import error


DEFAULT_UUID = 'test'
CHECK_PERIOD = 30

class TapoDriver(AbstractSystemsDriver):
    """Tapo Driver"""

    @classmethod
    def initialize(cls, config, logger):
        config.setdefault('SUSHY_EMULATOR_TAPO_SYSTEMS', [
            {
                'uuid': DEFAULT_UUID,
                'name': 'fake',
                'power_state': 'Off',
                'address': '127.0.0.1',
                'tapo_username': '', 
                'tapo_password': '', 
                'nics': [
                    {'address': '00:5c:52:31:3a:9c'}
                ]
            }
        ])
        cls._config = config
        cls._logger = logger
        return cls

    def __init__(self):
        super().__init__()
        self._systems = memoize.PersistentDict()
        if hasattr(self._systems, 'make_permanent'):
            self._systems.make_permanent(
                self._config.get('SUSHY_EMULATOR_STATE_DIR'), 'fakedriver')

        for system in self._config['SUSHY_EMULATOR_TAPO_SYSTEMS']:
            # Be careful to reduce racing with other processes
            identity = system['uuid']
            if system['uuid'] not in self._systems:
                self._systems[system['uuid']] = copy.deepcopy(system)
            sys = self._systems[identity]
            if not sys['last_updated']: 
                client = self._get_client(identity)
                check_time = int(time.time())
                power_state = self._get_power_state(client, identity)
                self._update(sys, power_state=power_state, last_updated=check_time)


        self._by_name = {
            system['name']: uuid
            for uuid, system in self._systems.items()
        }

    def _tapo_login(self, identity, attempts=5):
        addr = self._get(identity)['address']
        username = self._get(identity)['tapo_username']
        password = self._get(identity)['tapo_password'] 
        p100 = PyP100.P100(addr, username, password) #Creates a P100 plug object        
        
        attempt = 0 
        while attempt < attempts: 
            try:
                p100.handshake() 
                p100.login() 
                return p100
            except: 
                time.sleep(0.1) 
                attempt += 1

        return p100

    def _update_if_needed(self, system):
        pending_power = system.get('pending_power')
        if pending_power and time.time() >= pending_power['apply_time']:
            self._update(system,
                         power_state=pending_power['power_state'],
                         pending_power=None)

        return system

    def _get(self, identity):
        try:
            result = self._systems[identity]
        except KeyError:
            try:
                uuid = self._by_name[identity]
            except KeyError:
                raise error.NotFound(f'Fake system {identity} was not found')
            else:
                raise error.AliasAccessError(uuid)

        # NOTE(dtantsur): since the state change can only be observed after
        # a _get() call, we can cheat a bit and update it on reading.
        return self._update_if_needed(result)

    def _update(self, system, **changes):
        if isinstance(system, str):
            system = self._get(system)
        system.update(changes)
        self._systems[system['uuid']] = system

    def _amt_login(self, identity): 
        host = self._get(identity)['amt_address']
        password = self._get(identity)['amt_password']
        return amt.client.Client(host, password)

    def _amt_turnOn(self, client): 
        client.power_on()
        
    def _amt_turnOff(self, client): 
        client.power_off()

    def _amt_restart(self, client): 
        client.power_cycle()

    def _get_amt_power_state(self, client): 
        status = amt.wsman.friendly_power_state(client.power_status()) 
        if status == 'on':
            return 'On'
        elif status == 'off': 
            return 'Off'
        else: 
            return False
    # get power state from tapo unit
    def _get_tapo_power_state(self, client): 
        # client = self._tapo_login(identity)
        return 'On' if client.getDeviceInfo()['result']['device_on'] else 'Off'

    def _tapo_turnOff(self, client, count=5): 
        attempts = 0
        while attempts < count:
            try: 
                client.turnOff()
                time.sleep(0.3)
                break
            except: 
                time.sleep(0.1)
                attempts += 1
            #    client.turnOff()
    def _tapo_turnOn(self, client, count=5): 
        attempts = 0
        while attempts < count:
            try: 
                client.turnOn()
                break
            except: 
                time.sleep(0.1)
                attempts += 1

    def _tapo_restart(self, client): 
        self._tapo_turnOff(client)
        time.sleep(1)
        self._tapo_turnOn(client)
    
    def _get_power_state(self, client, identity): 
        if self._get(identity)['amt']: 
            return self._get_amt_power_state(client)
        else:
            return self._get_tapo_power_state(client)
    
    def _get_client(self, identity):
        client = ""
        if self._get(identity)['amt']: 
            return self._amt_login(identity)
        else: 
            return self._tapo_login(identity)


    def _restart(self, client, identity): 
        if self._get(identity)['amt']: 
            self._amt_restart(client)
        else:
            self._tapo_restart(client)

    def _turnOn(self, client, identity): 
        if self._get(identity)['amt']: 
            self._amt_turnOn(client)
        else:
            self._tapo_turnOn(client)

    def _turnOff(self, client, identity): 
        if self._get(identity)['amt']: 
            self._amt_turnOff(client)
        else:
            self._tapo_turnOff(client)


    @property
    def driver(self):
        return '<tapo>'

    @property
    def systems(self):
        return list(self._systems)

    def uuid(self, identity):
        try:
            return self._get(identity)['uuid']
        except error.AliasAccessError as exc:
            return str(exc)

    def name(self, identity):
        try:
            return self._get(identity)['name']
        except error.AliasAccessError:
            return identity

    def get_power_state(self, identity):
        client = self._get_client(identity)
        check_time = int(time.time())
        system = self._get(identity)
        if (check_time - system['last_updated']) > CHECK_PERIOD: 
            power_state = self._get_power_state(client, identity)
            self._update(system, power_state=power_state, last_updated=check_time)
        return self._get(identity)['power_state']

    def set_power_state(self, identity, state):

        client = self._get_client(identity)
        
        system = self._get(identity)

        if 'On' in state:
            pending_state = 'On'
        elif state in ('ForceOff', 'GracefulShutdown'):
            pending_state = 'Off'
        elif 'Restart' in state:
            self._restart(client, identity)
            #client.turnOff()
            pending_state = 'On'
        else:
            raise error.NotSupportedError(
                f'Power state {state} is not supported')

        if self.get_power_state(identity) != pending_state:
            self._update(system, pending_power={
                'power_state': pending_state, 
                'apply_time': 0
            })
            if pending_state == 'On':
                self._turnOn(client, identity)
            elif pending_state == 'Off': 
                self._turnOff(client, identity)
            


    def get_boot_device(self, identity):
        return self._get(identity).get('boot_device', 'Hdd')

    def set_boot_device(self, identity, boot_source):
        self._update(identity, boot_device=boot_source)

    def get_boot_mode(self, identity):
        return self._get(identity).get('boot_mode', 'UEFI')

    def set_boot_mode(self, identity, boot_mode):
        self._update(identity, boot_mode=boot_mode)

    def get_secure_boot(self, identity):
        return self._get(identity).get('secure_boot', False)

    def set_secure_boot(self, identity, secure):
        self._update(identity, secure_boot=secure)

    def get_boot_image(self, identity, device):
        devinfo = self._get(identity).get('boot_image') or {}
        return devinfo.get(device) or (None, False, False)

    def set_boot_image(self, identity, device, boot_image=None,
                       write_protected=True):
        system = self._get(identity)
        devinfo = system.get('boot_image') or {}
        devinfo[device] = (boot_image, write_protected, bool(boot_image))
        self._update(system, boot_image=devinfo)

    def get_nics(self, identity):
        nics = self._get(identity)['nics']
        return [{'id': nic.get('address'), 'mac': nic.get('address')}
                for nic in nics]
