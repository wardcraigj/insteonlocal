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

    def currentTemp(self):
        """Get the current temperature from device"""
        self.hub.direct_command(self.device_id, '6B', '03')

        success = self.hub.check_success(self.device_id, '6B', '03')

        status = self.hub.get_buffer_status(self.device_id)
        attempts = 0
        while not status['success'] and attempts < 9:
            if attempts % 3 == 0:
                self.hub.direct_command(self.device_id, '6B', '03')
            else:
                sleep(1)
            status = self.hub.get_buffer_status(self.device_id)
            attempts += 1

        if status['success']:
            temp = int(status['cmd2'], 16) / 2
        else:
            temp = False

        return temp


    def beep(self):
        """Make dimmer beep. Not all devices support this"""
        self.logger.info("Thermostat %s beep", self.device_id)

        self.hub.direct_command(self.device_id, '30', '00')

        success = self.hub.check_success(self.device_id, '30', '00')

        return success
