import pprint

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

class Fan():
    """This class defines an object for an INSTEON FanLinc"""
    def __init__(self, hub, device_id):
        self.device_id = device_id.upper()
        self.hub = hub
        self.logger = hub.logger


    def status(self):
        """Get status from device"""
        status = self.hub.get_device_status(self.device_id, level='03')
        self.logger.info("Fan %s status: %s", self.device_id,
                         pprint.pformat(status))
        return status


    def on(self, level):
        """Turn fan on at saved ramp rate"""
        self.logger.info("Fan %s on level %s", self.device_id, level)

        if level == 'off':
            new_level = '00'
        elif level == 'low':
            new_level = '55'
        elif level == 'medium':
            new_level = 'AA'
        elif level == 'high':
            new_level = 'FF'

        self.hub.direct_command(self.device_id, '11', new_level, '02')

        success = self.hub.check_success(self.device_id, '11', new_level)
        if success:
            self.logger.info("Fan %s on: Fan turned on successfully",
                             self.device_id)
            self.hub.clear_device_command_cache(self.device_id)
        else:
            self.logger.error("Fan %s on: Fan did not turn on", self.device_id)

        return success

    def off(self):
        """Turn fan off at saved ramp rate"""
        self.logger.info("Fan %s off", self.device_id)

        self.hub.direct_command(self.device_id, '13', '00', '02')

        success = self.hub.check_success(self.device_id, '13', '00')
        if success:
            self.logger.info("Fan %s off: Fan turned off successfully",
                             self.device_id)
            self.hub.clear_device_command_cache(self.device_id)
        else:
            self.logger.error("Fan %s off: Fan did not turn off",
                              self.device_id)

        return success
