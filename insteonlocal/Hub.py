import pprint, logging, logging.handlers, json, requests, pkg_resources
from collections import OrderedDict
from time import sleep
from io import StringIO
from sys import stdout
from insteonlocal.Switch import Switch
from insteonlocal.Group import Group
from insteonlocal.Dimmer import Dimmer

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

# Todo:
# error handling
# linking devices
# scene management
# double tap scenes
# switch on updates/broadcasts

class Hub(object):
    def __init__(self, ip, username, password, port="25105", logfile="/tmp/insteonlocal.log", consoleLog = False):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port

        self.buffer_status = OrderedDict()

        json_cats = pkg_resources.resource_string(__name__, 'data/device_categories.json')
        json_cats_str = json_cats.decode('utf-8')
        self.deviceCategories = json.loads(json_cats_str)

        json_models = pkg_resources.resource_string(__name__, 'data/device_models.json')
        json_models_str = json_models.decode('utf-8')
        self.deviceModels = json.loads(json_models_str)

        self.hubUrl = 'http://' + self.ip + ':' + self.port

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(logfile, mode='a')
        fh.setLevel(logging.INFO)

        formatter = logging.Formatter('[%(asctime)s] ' +
                     '(%(filename)s:%(lineno)s) %(message)s',
    				datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)

        self.logger.addHandler(fh)

        if (consoleLog):
            ch = logging.StreamHandler(stream=stdout)
            ch.setLevel(logging.INFO)
            self.logger.addHandler(ch)


    ## Convert numeric brightness percentage into hex for insteon
    def brightnessToHex(self, level):
        levelInt = int(level)
        newInt = int((levelInt * 255)/100)
        newLevel = format(newInt, '02X')
        self.logger.debug("brightnessToHex: {} to {}".format(level, str(newLevel)))
        return str(newLevel)


    ## Send raw command via post
    def postDirectCommand(self, commandUrl):
        self.logger.info("postDirectCommand: {}".format(commandUrl))
        return requests.post(commandUrl,
            auth=requests.auth.HTTPBasicAuth(self.username, self.password))


    ## Send raw comment via get
    def getDirectCommand(self, commandUrl):
        self.logger.info("getDirectCommand: {}".format(commandUrl))
        return requests.get(commandUrl,
            auth=requests.auth.HTTPBasicAuth(self.username, self.password))


    # Wrapper to send posted direct command and get response
    # level 0 to 100
    # extendedPayload is 14 bytes/28 chars
    def directCommand(self, deviceId, command, command2, extendedPayload = None):
        extendedPayload = extendedPayload or ''
        if not extendedPayload:
            msgType = '0'
            msgTypeDesc = 'Standard'
        else:
            msgType = '1'
            msgTypeDesc = 'Extended'

        self.logger.info("directCommand: Device: {} Command: {} Command 2: {} MsgType: {}".format(deviceId, command, command2, msgTypeDesc))
        deviceId = deviceId.upper()
        commandUrl = (self.hubUrl + '/3?' + "0262"
                    + deviceId + msgType + "F"
                    + command + command2 + extendedPayload + "=I=3")
        return self.postDirectCommand(commandUrl)


    # Direct hub command
    def directCommandHub(self, command):
        self.logger.info("directCommandHub: Command {}".format(command))
        commandUrl = (self.hubUrl + '/3?' + command + "=I=3")
        return self.postDirectCommand(commandUrl)


    # Wrapper for short-form commands (doesn't need device id or flags byte)
    # For group commands
    def directCommandShort(self, command):
        self.logger.info("directCommandShort: Command {}".format(command))
        commandUrl = (self.hubUrl + '/3?' + command + "=I=0")
        return self.postDirectCommand(commandUrl)


    # Get a list of all currently linked devices
    def getLinked(self):
        linked_devices = {}
        self.logger.info("\ngetLinked")

        #todo instead of sleep, create loop to keep checking buffer
        self.directCommandHub('0269')
        sleep(1)
        self.getBufferStatus()
        msgs = self.buffer_status.get('msgs', [])
        for entry in msgs:
            im_code = entry.get('im_code', '')
            #self.logger.info("getLinked entry {}".format(pprint.pformat(entry)))

            if (im_code == '57'):
                id = entry.get('id_high', '') + entry.get('id_mid', '') + entry.get('id_low', '')
                group = entry.get('group', '')
                if id not in linked_devices:
                    dev_info = self.idRequest(id)
                    dev_cat = dev_info.get('id_high', '')
                    dev_sub_cat = dev_info.get('id_mid', '')
                    dev_cat_record = self.getDeviceCategory(dev_cat)
                    if dev_cat_record and 'name' in dev_cat_record:
                        dev_cat_name = dev_cat_record['name']
                        dev_cat_type = dev_cat_record['type']
                    else:
                        dev_cat_name = 'unknown'
                        dev_cat_type = 'unknown'

                    linked_dev_model = self.getDeviceModel(dev_cat, dev_sub_cat)
                    if 'name' in linked_dev_model:
                        dev_model_name = linked_dev_model['name']
                    else:
                        dev_model_name = 'unknown'

                    if 'sku' in linked_dev_model:
                        dev_sku = linked_dev_model['sku']
                    else:
                        dev_sku = 'unknown'

                    self.logger.info("getLinked: Got first device: {} group {} cat type {} cat name {} dev model name {}".format(id, group, dev_cat_type, dev_cat_name, dev_model_name))
                    linked_devices[id] = {
                        'cat_name': dev_cat_name,
                        'cat_type': dev_cat_type,
                        'model_name' : dev_model_name,
                        'cat': dev_cat,
                        'sub_cat': dev_sub_cat,
                        'sku': dev_sku,
                        'group': []
                    }

                linked_devices[id]['group'].append(group)

        while (self.buffer_status['success']):
            self.directCommandHub('026A')
            sleep(1)
            self.getBufferStatus()
            msgs = self.buffer_status.get('msgs', [])
            for entry in msgs:
                im_code = entry.get('im_code', '')
                if (im_code == '57'):
                    id = entry.get('id_high', '') + entry.get('id_mid', '') + entry.get('id_low', '')
                    group = entry.get('group', '')

                    if id not in linked_devices:
                        dev_info = self.idRequest(id)
                        dev_cat = dev_info.get('id_high', '')
                        dev_sub_cat = dev_info.get('id_mid', '')
                        dev_cat_record = self.getDeviceCategory(dev_cat)
                        if dev_cat_record and 'name' in dev_cat_record:
                            dev_cat_name = dev_cat_record['name']
                            dev_cat_type = dev_cat_record['type']
                        else:
                            dev_cat_name = 'unknown'
                            dev_cat_type = 'unknown'

                        linked_dev_model = self.getDeviceModel(dev_cat, dev_sub_cat)
                        if 'name' in linked_dev_model:
                            dev_model_name = linked_dev_model['name']
                        else:
                            dev_model_name = 'unknown'

                        if 'sku' in linked_dev_model:
                            dev_sku = linked_dev_model['sku']
                        else:
                            dev_sku = 'unknown'

                        self.logger.info("getLinked: Got device: {} group {} cat type {} cat name {} dev model name {}".format(id, group, dev_cat_type, dev_cat_name, dev_model_name))
                        linked_devices[id] = {
                            'cat_name': dev_cat_name,
                            'cat_type': dev_cat_type,
                            'model_name' : dev_model_name,
                            'cat': dev_cat,
                            'sub_cat': dev_sub_cat,
                            'sku': dev_sku,
                            'group': []
                        }

                    linked_devices[id]['group'].append(group)

        self.logger.info("getLinked: Final device list: {}".format(pprint.pformat(linked_devices)))
        return linked_devices


    # Given the category id, return name and type for the category
    def getDeviceCategory(self, cat):
        if cat in self.deviceCategories:
            return self.deviceCategories[cat]
        else:
            return False


    # Return the model name given cat/subcat or product key
    def getDeviceModel(self, cat, subCat, key=''):
        if cat + ':' + subCat in self.deviceModels:
            return self.deviceModels[cat + ':' + subCat]
        else:
            for k,v in self.deviceModels.items():
                if 'key' in v:
                    if v['key'] == key:
                        return v
            return False


    # Get the device for the ID. ID request can return device type (cat/subcat), firmware ver, etc.
    # cat is status['is_high'], sub cat is status['id_mid']
    def idRequest(self, deviceId):
        self.logger.info("\nidRequest for device {}".format(deviceId))
        deviceId = deviceId.upper()

        self.directCommand(deviceId, '10', '00')

        sleep(2)

        status = self.getBufferStatus(deviceId)

        return status

    # Do a separate query to get device status. This can tell if device is on/off, lighting level, etc.
    # status['responseCmd2'] is lighting level
    # responseCmd1 contains All-Link Database delta
    # if returnLED = 0. returns light level in responseCmd2
    # if returnLED = 1, returns LED Bit Flags in responseCmd1

    def getDeviceStatus(self, deviceId, returnLED=0):
        self.logger.info("\ngetDeviceStatus for device {}".format(deviceId))
        deviceId = deviceId.upper()

        if (returnLED == 1):
            level = '01'
        else:
            level = '00'
        self.directCommand(deviceId, '19', level)

        sleep(2)

        status = self.getBufferStatus(deviceId)

        return status


    # Main method to read from buffer
    # Optionally pass in device to only get response from that device
    def getBufferStatus(self, device_from = None):
        device_from = device_from or ''

        # only used if device_from passed in
        return_record =  OrderedDict()

        command_url = self.hubUrl + '/buffstatus.xml'
        self.logger.info("getBufferStatus: {}".format(command_url))

        response = self.getDirectCommand(command_url)
        raw_text = response.text
        raw_text = raw_text.replace('<response><BS>', '')
        raw_text = raw_text.replace('</BS></response>', '')
        raw_text = raw_text.strip()
        self.logger.info('getBufferStatus: Got raw text of: {}'.format(raw_text))

        # the last byte in the buffer indicates where it stopped writing. checking for text after that
        # position would show if the buffer has overlapped and allow ignoring the old stuff after
        buffer_end = raw_text[-2:]
        buffer_end_int = int(buffer_end, 16)
        #raw_text = raw_text[0:buffer_end_int]
        self.logger.info('bufferEnd hex {} dec {}'.format(buffer_end, buffer_end_int))
        self.logger.info('getBufferStatus: non wrapped {}'.format(raw_text))

        self.buffer_status = OrderedDict()

        self.buffer_status['error']   = False
        self.buffer_status['success'] = True
        self.buffer_status['message'] = ''
        self.buffer_status['msgs']    = []

        buffer_contents = StringIO(raw_text)

        while True:

            msg = buffer_contents.read(4)
            if ((len(msg) < 4) or (msg == '') or (msg == '0000')):
                break

            im_start = msg[0:2]
            im_cmd = msg[2:4]

            response_record = OrderedDict()
            response_record['im_code'] = im_cmd

            # Standard Message Received
            if im_cmd == '50':
                msg = msg + buffer_contents.read(18)
                response_record['im_code_desc'] = 'Standard Message Received'
                response_record['raw']          = msg
                response_record['id_from']      = msg[4:10]
                response_record['id_high']      = msg[10:12] # direct id high, group groupid, broadcast cat
                response_record['id_mid']       = msg[12:14] # direct id mid, broadcast subcat
                response_record['id_low']       = msg[14:16] # direct id low, broadcast firmware version
                response_record['flag1']        = msg[16:17] # 2 ack, 8 broadcast
                response_record['flag2']        = msg[17:18] # hop count B
                response_record['cmd1']         = msg[18:20] # direct cmd, broadcast 01, status db delta
                response_record['cmd2']         = msg[20:22] # direct cmd 2, broadcast 00, status on level

            # Extended Mesage Received
            elif im_cmd == '51':
                msg = msg + buffer_contents.read(46)

                response_record['im_code_desc'] = 'Extended Message Received'
                response_record['raw']          = msg
                response_record['id_from']      = msg[4:10]
                response_record['id_high']      = msg[10:12] # direct id high, group groupid, broadcast cat
                response_record['id_mid']       = msg[12:14] # direct id mid, broadcast subcat
                response_record['id_low']       = msg[14:16] # direct id low, broadcast firmware version
                response_record['flags']        = msg[16:18] # 2 ack, 8 broadcast + hop count B
                response_record['cmd1']         = msg[18:20] # direct cmd, broadcast 01, status db delta
                response_record['cmd2']         = msg[20:22] # direct cmd 2, broadcast 00, status on level
                response_record['user_data_1']  = msg[22:24]
                response_record['user_data_2']  = msg[24:26]
                response_record['user_data_3']  = msg[26:28]
                response_record['user_data_4']  = msg[28:30]
                response_record['user_data_5']  = msg[30:32]
                response_record['user_data_6']  = msg[32:34]
                response_record['user_data_7']  = msg[34:36]
                response_record['user_data_8']  = msg[36:38]
                response_record['user_data_9']  = msg[38:40]
                response_record['user_data_10'] = msg[40:42]
                response_record['user_data_11'] = msg[42:44]
                response_record['user_data_12'] = msg[44:46]
                response_record['user_data_13'] = msg[46:48]
                response_record['user_data_14'] = msg[48:50]

            # X10 Received (not implemented)
            elif im_cmd == '52':
                self.logger.error('Not implemented handling of 0252 X10 Received')
                break

            # ALL-Linking Completed
            elif im_cmd == '53':
                msg = msg = buffer_contents.read(16)

                response_record['im_code_desc']    = 'ALL-Linking Completed'
                response_record['raw']             = msg
                response_record['link_status']     = msg[4:6]

                if (response_record['link_status'] == '00'):
                    response_record['link_status_desc'] = 'IM is Responder'
                elif (response_record['link_status'] == '01'):
                    response_record['link_status_desc'] = 'IM is Controller'
                elif (response_record['link_status'] == 'FF'):
                    response_record['link_status_desc'] = 'Link Deleted'

                response_record['group']            = msg[6:8]
                response_record['id_high']          = msg[8:10]
                response_record['id_mid']           = msg[10:12]
                response_record['id_low']           = msg[12:14]
                response_record['dev_cat']          = msg[14:16]
                response_record['dev_subcat']       = msg[16:18]
                response_record['dev_firmware_rev'] = msg[18:20] # or FF for newer devices

            # Button Event Report
            elif im_cmd == '54':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']    = 'Button Event Report'
                response_record['raw']             = msg
                response_record['report_type']     = msg[4:6]
                if (response_record['report_type'] == "02"):
                    response_record['report_type_desc'] = "IM's SET Button tapped"
                elif (response_record['report_type'] == "03"):
                    response_record['report_type_desc'] = "IM's SET Button held"
                elif (response_record['report_type'] == "04"):
                    response_record['report_type_desc'] = "IM's SET Button released after hold"
                elif (response_record['report_type'] == "12"):
                    response_record['report_type_desc'] = "IM's Button 2 tapped"
                elif (response_record['report_type'] == "13"):
                    response_record['report_type_desc'] = "IM's Button 2 held"
                elif (response_record['report_type'] == "14"):
                    response_record['report_type_desc'] = "IM's Button 2 released after hold"
                elif (response_record['report_type'] == "22"):
                    response_record['report_type_desc'] = "IM's Button 3 tapped"
                elif (response_record['report_type'] == "23"):
                    response_record['report_type_desc'] = "IM's Button 3 held"
                elif (response_record['report_type'] == "24"):
                    response_record['report_type_desc'] = "IM's Button 3 released after hold"

            # User Reset Detected
            elif im_cmd == '55':
                response_record['im_code_desc']  = 'User Reset Detected'
                response_record['raw']           = msg
                response_record['im_code_desc2'] = "User pushed and held IM's SET Button on power up"

            # ALL-Link Cleanup Failure Report
            elif im_cmd == '56':
                msg = msg + buffer_contents.read(10)

                response_record['im_code_desc']  = 'ALL-Link Cleanup Failure Report'
                response_record['raw']           = msg
                response_record['group']         = msg[4:6]
                response_record['ack']           = msg[6:8] # 01 means member did not acknlowedge all-link cleanup cmd
                response_record['id_high']       = msg[8:10]
                response_record['id_mid']        = msg[10:12]
                response_record['id_low']        = msg[12:14]

            # ALL-Link Record Response
            elif im_cmd == '57':
                msg = msg + buffer_contents.read(20)

                response_record['im_code_desc'] = 'ALL-Link Record Response'
                response_record['raw']          = msg
                response_record['flags']        = msg[4:6] # hub dev manual p 39
                response_record['group']        = msg[6:8]
                response_record['id_high']      = msg[8:10]
                response_record['id_mid']       = msg[10:12]
                response_record['id_low']       = msg[12:14]
                response_record['link_data_1']  = msg[14:16]
                response_record['link_data_2']  = msg[16:18]
                response_record['link_data_3']  = msg[18:20]

            # ALL-Link Cleanup Status Report
            elif im_cmd == '58':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']   = 'ALL-Link Cleanup Status Report'
                response_record['raw']            = msg
                response_record['cleanup_status'] = msg[4:6]
                if (response_record['cleanup_status'] == '06'):
                    response_record['cleanup_status_desc'] = 'ALL-Link Cleanup sequence completed'
                elif (response_record['cleanup_status'] == '15'):
                    response_record['cleanup_status_desc'] = 'ALL-Link Cleanup sequence aborted due to INSTEON traffic'

            # Database Record Found
            elif im_cmd == '59':
                msg = msg + buffer_contents.read(18)

                response_record['im_code_desc'] = 'Database Record Found'
                response_record['raw']          = msg
                response_record['address_low']  = msg[4:6]
                response_record['record_flags'] = msg[6:8]
                response_record['group']        = msg[8:10]
                response_record['id_high']      = msg[10:12]
                response_record['id_mid']       = msg[12:14]
                response_record['id_low']       = msg[14:16]
                response_record['link_data_1']  = msg[16:18]
                response_record['link_data_2']  = msg[18:20]
                response_record['link_data_3']  = msg[20:22]

            # Get IM Info
            elif im_cmd == '60':
                msg = msg + buffer_contents.read(14)

                response_record['im_code_desc']     = 'Get IM Info'
                response_record['raw']              = msg
                response_record['id_high']          = msg[4:6]
                response_record['id_mid']           = msg[6:8]
                response_record['id_low']           = msg[8:10]
                response_record['dev_cat']          = msg[10:12]
                response_record['dev_subcat']       = msg[12:14]
                response_record['dev_firmware_rev'] = msg[14:16]
                response_record['ack_or_nak']       = msg[16:18] # 06 ack

            # Send ALL-Link Command
            elif im_cmd == '61':
                msg = msg + buffer_contents.read(8)

                response_record['im_code_desc']   = 'Send ALL-Link Command'
                response_record['raw']            = msg
                response_record['group']          = msg[4:6]
                response_record['cmd']            = msg[6:8]
                response_record['broadcast_cmd2'] = msg[8:10] # FF or 00
                response_record['ack_or_nak']     = msg[10:12] # 06 ack

            # Send Message (Pass through command to PLM)
            elif im_cmd == '62':
                msg = msg + buffer_contents.read(14)

                response_record['im_code_desc'] = 'Send Message'
                response_record['raw']          = msg
                response_record['id']           = msg[4:10]
                response_record['flags']        = msg[10:12]
                response_record['cmd1']         = msg[12:14]
                response_record['cmd2']         = msg[14:16]
                response_record['ack_or_nak']   = msg[16:18] # 06 ack 15 nak

            # Send X10 (not implemented)
            elif im_cmd == '63':
                self.logger.error('Not implemented handling of 0263 Send X10')
                break

            # Start ALL-Linking
            elif im_cmd == '64':
                msg = msg + buffer_contents.read(6)

                response_record['im_code_desc'] = 'Start ALL-Linking'
                response_record['raw']          = msg
                response_record['link_type']    = msg[4:6]

                if (response_record['link_type'] == '00'):
                    response_record['link_type_desc'] = 'IM is Responder'
                elif (response_record['link_type'] == '01'):
                    response_record['link_type_desc'] = 'IM is Controller'
                elif (response_record['link_type'] == '03'):
                    response_record['link_type_desc'] = 'IM is Either Responder or Controller'
                elif (response_record['link_type'] == 'FF'):
                    response_record['link_type_desc'] = 'Link Deleted'

                response_record['group']        = msg[6:8]
                response_record['ack_or_nak']   = msg[8:10] # 06 ack 15 nak

            # Cancel ALL-Linking
            elif im_cmd == '65':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc'] = 'Cancel ALL-Linking'
                response_record['raw']          = msg
                response_record['ack_or_nak']   = msg[4:6] # 06 ack 15 nak

            # Set Host Device Category
            elif im_cmd == '66':
                msg = msg + buffer_contents.read(8)

                response_record['im_code_desc']     = 'Set Host Device Category'
                response_record['raw']              = msg
                response_record['dev_cat']          = msg[4:6]
                response_record['dev_subcat']       = msg[6:8]
                response_record['dev_firmware_rev'] = msg[8:10] # or 00
                response_record['ack_or_nak']       = msg[10:12] # 06 ack 15 nak

            # Reset the IM
            elif im_cmd == '67':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'Reset the IM'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack 15 nak

            # Set INSTEON ACK Message Byte
            elif im_cmd == '68':
                msg = msg + buffer_contents.read(4)

                response_record['im_code_desc']     = 'Set INSTEON ACK Message Byte'
                response_record['raw']              = msg
                response_record['cmd2_data']        = msg[4:6]
                response_record['ack_or_nak']       = msg[6:8] # 06 ack 15 nak

            # Get First ALL-Link Record
            elif im_cmd == '69':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'Get First ALL-Link Record'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack 15 nak

            # Get Next ALL-Link Record
            elif im_cmd == '6A':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'Get Next ALL-Link Record'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack 15 nak

            # Set IM Configuration
            elif im_cmd == '6B':
                msg = msg + buffer_contents.read(4)

                response_record['im_code_desc']     = 'Set IM Configuration'
                response_record['raw']              = msg
                response_record['im_cfg_flags']     = msg[4:6]
                response_record['ack_or_nak']       = msg[6:8] # 06 ack 15 nak

            # Get ALL-Link Record for Sender
            elif im_cmd == '6C':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'Get ALL-Link Record for Sender'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack 15 nak

            # LED On
            elif im_cmd == '6D':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'LED On'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack 15 nak

            # LED Off
            elif im_cmd == '6E':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'LED Off'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack 15 nak

            # Manage ALL-Link Record
            elif im_cmd == '6F':
                msg = msg + buffer_contents.read(20)

                response_record['im_code_desc']     = 'Manage ALL-Link Record'
                response_record['raw']              = msg
                response_record['ctrl_flags']       = msg[4:6]
                response_record['record_flags']     = msg[6:8]
                response_record['group']            = msg[8:10]
                response_record['id_high']          = msg[10:12]
                response_record['id_mid']           = msg[12:14]
                response_record['id_low']           = msg[14:16]
                response_record['link_data_1']      = msg[16:18]
                response_record['link_data_2']      = msg[18:20]
                response_record['link_data_3']      = msg[20:22]
                response_record['ack_or_nak']       = msg[22:24] # 06 ack

            # Set INSTEON ACK Message Two Bytes
            elif im_cmd == '71':
                msg = msg + buffer_contents.read(6)

                response_record['im_code_desc']     = 'Set INSTEON ACK Message Two Bytes'
                response_record['raw']              = msg
                response_record['cmd1_data']        = msg[4:6]
                response_record['cmd2_data']        = msg[6:8]
                response_record['ack_or_nak']       = msg[8:10] # 06 ack

            # RF Sleep
            elif im_cmd == '72':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'RF Sleep'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack

            # Get IM Configuration
            elif im_cmd == '73':
                msg = msg + buffer_contents.read(8)

                response_record['im_code_desc']     = 'Get IM Configuration'
                response_record['raw']              = msg
                response_record['im_cfg_flags']     = msg[4:6]
                response_record['spare1']           = msg[6:8]
                response_record['spare2']           = msg[8:10]
                response_record['ack_or_nak']       = msg[10:12] # 06 ack

            # Cancel Cleanup
            elif im_cmd == '74':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'Cancel Cleanup'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack 15 nak

            # Read 8 bytes from Database
            elif im_cmd == '75':
                msg = msg + buffer_contents.read(30)

                response_record['im_code_desc']     = 'Read 8 bytes from Database'
                response_record['raw']              = msg
                response_record['db_addr_high']     = msg[4:6]
                response_record['db_addr_low']      = msg[6:8] # low nibble F, or 8
                response_record['ack_or_nak']       = msg[8:10] # 06 ack
                response_record['record']           = msg[10:34] # database record founnd response 12 bytes

            # Write 8 bytes to Database
            elif im_cmd == '76':
                msg = msg + buffer_contents.read(22)

                response_record['im_code_desc']     = 'Write 8 bytes to Database'
                response_record['raw']              = msg
                response_record['db_addr_high']     = msg[4:6]
                response_record['db_addr_low']      = msg[6:8] # low nibble F, or 8
                response_record['record_flags']     = msg[8:10]
                response_record['group']            = msg[10:12]
                response_record['id_high']          = msg[12:14]
                response_record['id_middle']        = msg[14:16]
                response_record['id_low']           = msg[16:18]
                response_record['link_data_1']      = msg[18:20]
                response_record['link_data_2']      = msg[20:22]
                response_record['link_data_3']      = msg[22:24]
                response_record['ack_or_nak']       = msg[24:26] # 06 ac

            # Beep
            elif im_cmd == '77':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'Beep'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack 15 nak

            # Set Status
            # IM reports Status in cmd2 of direct Status Request command (19)
            elif im_cmd == '78':
                msg = msg + buffer_contents.read(2)

                response_record['im_code_desc']     = 'Set Status'
                response_record['raw']              = msg
                response_record['ack_or_nak']       = msg[4:6] # 06 ack

            # Set Database Link Data for Next Link
            elif im_cmd == '79':
                msg = msg + buffer_contents.read(8)

                response_record['im_code_desc']     = 'Set Database Link Data for Next Link'
                response_record['raw']              = msg
                response_record['link_data_1']      = msg[4:6]
                response_record['link_data_2']      = msg[6:8]
                response_record['link_data_3']      = msg[8:10]
                response_record['ack_or_nak']       = msg[10:12] # 06 ack

            # Set Application Retries for New Links
            elif im_cmd == '7A':
                msg = msg + buffer_contents.read(4)

                response_record['im_code_desc']     = 'Set Application Retries for New Links'
                response_record['raw']              = msg
                response_record['num_retries']      = msg[4:6]
                response_record['ack_or_nak']       = msg[6:8] # 06 ack

            # Set RF Frequency Offset
            elif im_cmd == '7B':
                msg = msg + buffer_contents.read(4)

                response_record['im_code_desc']     = 'Set RF Frequency Offset'
                response_record['raw']              = msg
                response_record['rf_freq_offset']   = msg[4:6]
                response_record['ack_or_nak']       = msg[6:8] # 06 ack

            # Set Acknowledge for TempLinc Command (not implemented)
            elif im_cmd == '7C':
                self.logger.error("Not implemented handling of 027C Set Acknowledge for TempLinc command")
                break

            if (response_record.get('ack_or_nak', '') == '15'):
                self.buffer_status['error'] = True
                self.buffer_status['success'] = False
                self.buffer_status['message'] = 'Device returned nak'

            response_device_from = response_record.get('id_from', '')
            if device_from and device_from == response_device_from:
                return_record = response_record

            self.buffer_status['msgs'].append(response_record)

        # Tell hub to clear buffer
        self.clearBuffer()

        pprint.pprint(self.buffer_status)

        if device_from:
            return return_record



    ## Check if last command succeeded  by checking buffer
    def checkSuccess(self, device_id, sent_cmd1, sent_cmd2):
        device_id = device_id.upper()

        self.logger.info('checkSuccess: for device {} cmd1 {} cmd2 {}'.format(device_id, sent_cmd1, sent_cmd2))

        sleep(2)
        status = self.getBufferStatus(device_id)
        id = status.get('id_from', '')
        cmd1 = status.get('cmd1', '')
        cmd2 = status.get('cmd2', '')
        if ((id == device_id) and (cmd1 == sent_cmd1) and (cmd2 == sent_cmd2)):
            self.logger.info("checkSuccess: Response device {} cmd {} cmd2 {} SUCCESS".format(id, cmd1, cmd2))
            return True

        self.logger.info("checkSuccess: No valid response found for device {} cmd {} cmd2 {}".format(device_id, sent_cmd1, sent_cmd2))
        return False


    ## Clear the hub buffer
    def clearBuffer(self):
        commandUrl = self.hubUrl + '/1?XB=M=1'
        response = self.postDirectCommand(commandUrl)
        self.logger.info("clearBuffer: {}".format(response))
        return response



   ## @TODO IN DEVELOPMENT
   ### TODO listen for linked page 35 http://cache.insteon.com/developer/2242-222dev-062013-en.pdf
   ## Begin all linking
   # linkType:
   #  00 as responder/slave
   #  01 as controller/master
   #  03 as controller with im initiates all linking or as responder when another device initiates all linking
   #  FF deletes the all link
    def startAllLinking(self, linkType, groupId):
        self.logger.info("\nstartAllLinking for type {} group {}".format(linkType, groupId))
        self.directCommandHub('0264' + linkType + groupId)
       # TODO: read response
        #    Byte Value Meaning
        #1 0x02 Echoed Start of IM Command
        #2 0x64 Echoed IM Command Number
        #3 <Code> Echoed <Code>
        #4 <ALL-Link Group> Echoed <ALL-Link Group>
        #5 <ACK/NAK> 0x06 (ACK) if the IM executed the Command correctly
        #0x15 (NAK) if an error occurred


    def cancelAllLinking(self):
        self.logger.info("\ncancelAllLinking")
        self.directCommandHub('0265')
        ## TODO read response
            # 0x02 echoed start of command
            # 0x65 echoed im command
            # ack 06 or nak 15


    def group(self, groupId):
        groupObj = Group(self, groupId)
        return groupObj

    def dimmer(self, deviceId):
        dimmerObj = Dimmer(self, deviceId)
        return dimmerObj

    def switch(self, deviceId):
        switchObj = Switch(self, deviceId)
        return switchObj


