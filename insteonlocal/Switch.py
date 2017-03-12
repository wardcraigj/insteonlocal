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

class Switch():
    """Creates a Switch object representing an INStEON Toggle Device"""
    def __init__(self, hub, device_id):
        self.device_id = device_id
        self.hub = hub
        self.logger = hub.logger


   ## @TODO IN DEVELOPMENT
   ### TODO listen for linked page 35 http://cache.insteon.com/developer/2242-222dev-062013-en.pdf
   ## Begin all linking
   # link type:
   #  00 as responder/slave
   #  01 as controller/master
   #  03 as controller with im initiates all linking or as responder when
   #      another device initiates all linking
   #  FF deletes the all link
    def start_all_linking(self, link_type, group_id):
        """Start all linking"""
        self.logger.info("Start_all_linking for device %s type %s group %s",
                         self.device_id, link_type, group_id)
        self.hub.direct_command(self.device_id, '02', '64' + link_type + group_id)
       # TODO: read response
        #    Byte Value Meaning
        #1 0x02 Echoed Start of IM Command
        #2 0x64 Echoed IM Command Number
        #3 <Code> Echoed <Code>
        #4 <ALL-Link Group> Echoed <ALL-Link Group>
        #5 <ACK/NAK> 0x06 (ACK) if the IM executed the Command correctly
        #0x15 (NAK) if an error occurred


    def cancel_all_linking(self):
        """Cancel all linking"""
        self.logger.info("Cancel_all_linking for device %s", self.device_id)
        self.hub.direct_command(self.device_id, '02', '65')


    def status(self, return_led=0):
        """Get status from device"""
        status = self.hub.get_device_status(self.device_id, return_led)
        self.logger.info("Dimmer %s status: %s", self.device_id,
                         pprint.pformat(status))
        return status


    def on(self):
        """ Turn switch on"""
        self.logger.info("Switch %s on", self.device_id)

        self.hub.direct_command(self.device_id, '11', 'FF')

        success = self.hub.check_success(self.device_id, '11', 'FF')

        if success:
            self.logger.info("Switch %s on: Switch turned on successfully",
                             self.device_id)
            self.hub.clear_device_command_cache(self.device_id)
        else:
            self.logger.error("Switch %s on: Switch did not turn on",
                              self.device_id)

        return success


    def off(self):
        """Turn switch off"""
        self.logger.info("Switch {} off".format(self.device_id))

        self.hub.direct_command(self.device_id, '13', 'FF')

        success = self.hub.check_success(self.device_id, '13', 'FF')

        if success:
            self.logger.info("Switch %s off: Switch turned off successfully",
                             self.device_id)
            self.hub.clear_device_command_cache(self.device_id)
        else:
            self.logger.error("Switch %s off: Switch did not turn off",
                              self.device_id)

        return success


    def beep(self):
        """Make switch beep. Not all devices support this"""
        self.logger.info("Switch %s beep", self.device_id)

        self.hub.direct_command(self.device_id, '30', '00')

        success = self.hub.check_success(self.device_id, '30', '00')

        return success
