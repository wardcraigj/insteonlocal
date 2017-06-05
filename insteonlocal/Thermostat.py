import pprint
from time import sleep

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
TEMP_UNIT_CELSIUS = 'C'
TEMP_UNIT_FAHRENHEIT = 'F'

class Thermostat():
    """This class defines an object for an INSTEON Thermostat"""
    def __init__(self, hub, device_id):
        self.device_id = device_id.upper()
        self.hub = hub
        self.logger = hub.logger


    def status(self, return_led=0):
        """Get status from device"""
        status = self.hub.get_device_status(self.device_id, return_led)
        self.logger.info("Thermostat %s status: %s", self.device_id,
                         pprint.pformat(status))
        return status
    def tempUnits(self):
        """Get the temperature units from device"""

        status = self.getExtendedStatus()

        if status['success']:
            cels_mask = 0x08
            celsius = cels_mask & int(status['msgs'][0]['user_data_13'], 16)

            if celsius > 0:
                units = TEMP_UNIT_CELSIUS
            else:
                units = TEMP_UNIT_FAHRENHEIT
        else:
            units = False

        return units

    def currentTemp(self):
        """Get the current temperature from device"""


        #ext = self.hub.build_extended_payload()

        self.hub.direct_command(self.device_id, '6A', '00')
        status = self.hub.get_buffer_status(self.device_id)

        #status = self.getExtendedStatus()
        #status = self.getResponseStatus('6A', '00')

        attempts = 0
        temp = False
        if status['success'] is True and status['msgs'][0]['cmd2'] != '00':
            temp = int(status['cmd2'], 16) / 2

        while temp is False and attempts < 9:
            if status['success'] is True:
                temp = int(status['cmd2'], 16) / 2
            else:
                if attempts % 3 == 0:
                    self.hub.direct_command(self.device_id, '6A', '00')
                sleep(1)
                attempts += 1
                status = self.hub.get_buffer_status(self.device_id)

        return temp

    def systemMode(self):
        """Get the current mode from device"""
        modes = {
            0: 'Off',
            1: 'Auto',
            2: 'Heat',
            3: 'Cool',
            4: 'Program'
        }

        status = self.getExtendedStatus()

        if status['success']:
            ret = modes.get(int(status['msgs'][0]['user_data_8']))
        else:
            ret = False

        return ret

    def getExtendedStatus(self):
        """Get extended status from thermostat"""
        ext = self.hub.build_extended_payload()
        self.hub.direct_command(self.device_id, '2E', '00', ext)
        status = self.getResponseStatus('2E', '00', ext)

        return status

    def getResponseStatus(self, command, command2, ext={}):
        status = self.hub.get_buffer_status(self.device_id)

        attempts = 0
        while not status['success'] and attempts < 9:
            if attempts % 3 == 0:
                sleep(1)
                # self.hub.direct_command(self.device_id, command, command2, ext)
            else:
                sleep(1)
            status = self.hub.get_buffer_status(self.device_id)

            if status['success'] and ext == {}:
                status['success'] = True
            elif status['success'] and ext != {} and status['im_code'] == '51':
                status['success'] = True
            else:
                status['success'] = False

            attempts += 1

        if status['success']:
            return status
        else:
            return False

    def beep(self):
        """Make dimmer beep. Not all devices support this"""
        self.logger.info("Thermostat %s beep", self.device_id)

        self.hub.direct_command(self.device_id, '30', '00')

        success = self.hub.check_success(self.device_id, '30', '00')

        return success
