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

class OnOffOutlet():
    """Creates a Switch object representing an INSTEON On/Off Device With Independent Top/Bottom like 2633-222 (2 39)"""
    def __init__(self, hub, device_id):
        self.device_id = device_id
        self.hub = hub
        self.logger = hub.logger


    def status(self, return_led=0):
        """Get status from device"""
        status = self.hub.get_device_status(self.device_id, return_led)
        self.logger.info("Dimmer %s status: %s", self.device_id,
                         pprint.pformat(status))
        return status


    def top_on(self):
        """ Turn top outlet on"""
        self.logger.info("On/Off Outlet Top %s on", self.device_id)

        self.hub.direct_command(self.device_id, '11', 'FF')

        success = self.hub.check_success(self.device_id, '11', 'FF')

        if success:
            self.logger.info("On/Off Outlet Top %s on: Outlet top turned on successfully",
                             self.device_id)
            self.hub.clear_device_command_cache(self.device_id)
        else:
            self.logger.error("On/Off Outlet Top %s on: Outlet top did not turn on",
                              self.device_id)

        return success


    def top_off(self):
        """Turn top off"""
        self.logger.info("On/Off Outlet Top {} off".format(self.device_id))

        self.hub.direct_command(self.device_id, '13', 'FF')

        success = self.hub.check_success(self.device_id, '13', 'FF')

        if success:
            self.logger.info("On/Off Outlet %s Top off: Outlet top turned off successfully",
                             self.device_id)
            self.hub.clear_device_command_cache(self.device_id)
        else:
            self.logger.error("On/Off Outlet Top %s off: Outlet top did not turn off",
                              self.device_id)

        return success


    def bottom_on(self):
        """ Turn bottom outlet on"""
        self.logger.info("On/Off Outlet Bottom %s on", self.device_id)

        self.hub.direct_command(self.device_id, '11', 'FF', '02000000000000000000000000')

        success = self.hub.check_success(self.device_id, '11', 'FF')

        if success:
            self.logger.info("On/Off Outlet Bottom %s on: Outlet bottom turned on successfully",
                             self.device_id)
            self.hub.clear_device_command_cache(self.device_id)
        else:
            self.logger.error("On/Off Outlet Bottom %s on: Outlet bottom did not turn on",
                              self.device_id)

        return success



    def bottom_off(self):
        """Turn top off"""
        self.logger.info("On/Off Outlet Bottom {} off".format(self.device_id))

        self.hub.direct_command(self.device_id, '13', 'FF', '02000000000000000000000000')

        success = self.hub.check_success(self.device_id, '13', 'FF')

        if success:
            self.logger.info("On/Off Outlet %s Bottom off: Outlet bottom turned off successfully",
                             self.device_id)
            self.hub.clear_device_command_cache(self.device_id)
        else:
            self.logger.error("On/Off Outlet %s Bottom off: Outlet bottom did not turn off",
                              self.device_id)

        return success


    def beep(self):
        """Make outlet beep. Not all devices support this"""
        self.logger.info("On/Off Outlet %s beep", self.device_id)

        self.hub.direct_command(self.device_id, '30', '00')

        success = self.hub.check_success(self.device_id, '30', '00')

        return success
