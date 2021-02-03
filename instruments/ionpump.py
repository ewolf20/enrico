"""
Library to read and control the ion pump
"""

import serial
import os
import time
import datetime

DEFAULT_LOG_FILE_STRING = "Ion_Pump_Log" 
MPC_DEFAULT_ADDRESS = 5
SPC_DEFAULT_ADDRESS = 1


# def get_key(my_dict, val):
#     for key, value in my_dict.items():
#         if val == value:
#             return key


class IonPump:


    """Constructor.

    Args:
        pump_label: str, the label describing the type of pump. Supports "spc" and "mpc".
        COM_PORT: str, the string describing the COM port of the pump serial connection, e.g. 'COM7'
        address: int, the address of the pump. Default is 1 for spc, 5 for mpc
        echo: bool, whether to echo the response after a send command
        wait_time: float, the wait time for a read after a send command
        sendwidget: Widget; ignore unless making a gui
        recvwidget: Widget; ignore unless making a gui
        history_file_string: A string path to a history file which the ion pump should log into. If not specified, a default name is chosen
        and an empty file created
        log_history: bool, whether the ion pump should log its readings.
        overwrite_history: bool, whether the ion pump should overwrite the specified history file
        can_control: bool, whether the class is allowed to make changes to the pump (i.e. turn on and off) or only to read
    """
    def __init__(self, pump_label, COM_PORT, address = None, echo = False, wait_time = 0.1, sendwidget = None, recvwidget = None,
                history_file_string = None, log_history = True, overwrite_history = False, can_control = False):
        #Default port settings for ion pumps
        PORT_SETTINGS = {'baudrate':9600, 'bytesize':serial.EIGHTBITS, 'parity':serial.PARITY_NONE, 'stopbits':serial.STOPBITS_ONE, 'timeout':1}
        self.serial_port = serial.Serial(COM_PORT, **PORT_SETTINGS)
        self.pump_label = pump_label
        self.echo = echo
        self.wait_time = wait_time
        self.sendwidget = sendwidget
        self.recvwidget = recvwidget
        self.log_history = log_history
        self.overwrite_history = overwrite_history
        self.can_control = can_control
        if(address is None):
            if(pump_label == "mpc"):
                self.address = MPC_DEFAULT_ADDRESS
            elif(pump_label == "spc"):
                self.address = SPC_DEFAULT_ADDRESS
        else:
            self.address = address
        if(history_file_string == None):
            label_index = 0 
            label_ok = False
            while(not label_ok):
                attempted_filename = DEFAULT_LOG_FILE_STRING + str(label_index) + ".csv"
                label_ok = not os.path.exists(attempted_filename) 
                label_index += 1
            history_file_string = attempted_filename
        if(self.log_history):
            if(self.overwrite_history):
                self.history_csv_file = open(history_file_string, 'w')
            else:
                self.history_csv_file = open(history_file_string, 'a')
        else:
            self.history_csv_file = None 
        

    def __enter__(self):
        return self 
    """
    Sends an arbitrary command to the turbo pump

    Args: 
        command: str, the command to be sent to the turbo pump. Is encoded as ASCII bytes
        add_checksum_and_end: Convenience. If True, the command string has a checksum and carriage return character 
        appended, following the initial tilde convention
    
    Returns:
        the return value of serial.write() 
    """

    def send(self, command, add_checksum_and_end = False):
        if(add_checksum_and_end):
            to_be_checked_string = command[1:]
            checksum_string = get_checksum_string(to_be_checked_string)
            command = command + checksum_string + "\r"
        return_value = self.serial_port.write(bytes(command, encoding = "ASCII"))
        self.serial_port.flush()
        if(self.echo):
            self.log(command, widget = self.sendwidget)
        time.sleep(self.wait_time)
        return return_value
         
    """Convenience method which measures the ion pump current, pressure, and voltage simultaneously"""

    def measure_all(self, supply_index = 1):
        current_value = self.measure_current(supply_index = supply_index) 
        pressure_value = self.measure_pressure(supply_index = supply_index) 
        voltage_value = self.measure_voltage(supply_index = supply_index) 
        return (current_value, pressure_value, voltage_value)

    """Measures the ion pump current.

    Queries the ion pump for its current. In the mpc model, supply_index describes which 
    supply (there are two) should be queried.
    """
    def measure_current(self, supply_index = 1):
        CURRENT_MEASURE_CODE = '0A'
        if(self.pump_label == "spc"):
            data_field = ''
        elif(self.pump_label == "mpc"):
            data_field = str(supply_index) + ' '
        current_measure_command = self._make_command(CURRENT_MEASURE_CODE, data_field = data_field)
        current_bytes_list = self.send_and_get_response(current_measure_command)
        current_value = self.parse_current_bytes(current_bytes_list)
        return current_value 

    """Measures ion pump pressure."""
    def measure_pressure(self, supply_index = 1):
        PRESSURE_MEASURE_CODE = '0B'
        if(self.pump_label == "spc"):
            data_field = ''
        elif(self.pump_label == "mpc"):
            data_field = str(supply_index) + ' '
        pressure_measure_command = self._make_command(PRESSURE_MEASURE_CODE, data_field = data_field) 
        pressure_bytes_list = self.send_and_get_response(pressure_measure_command)
        pressure_value = self.parse_pressure_bytes(pressure_bytes_list) 
        return pressure_value 

    """Measures ion pump voltage"""
    def measure_voltage(self, supply_index = 1):
        VOLTAGE_MEASURE_CODE = '0C'
        if(self.pump_label == "spc"):
            data_field = ''
        elif(self.pump_label == "mpc"):
            data_field = str(supply_index) + ' '
        voltage_measure_command = self._make_command(VOLTAGE_MEASURE_CODE, data_field = data_field)
        voltage_bytes_list = self.send_and_get_response(voltage_measure_command)
        voltage_value = self.parse_voltage_bytes(voltage_bytes_list) 
        return voltage_value 

    """Convenience method to turn off the pump.

    When called, turns off the ion pump power supply. Only works if 
    self.can_control = True, and if the pump is in a mode that accepts remote turn-off commands

    Returns:
    A boolean. True if the pump was successfully turned off, False otherwise.
    """
    def turn_off_pump(self):
        if(not can_control):
            return False
        TURN_OFF_CODE = '38'
        try:
            if(self.pump_label == "spc"):
                turn_off_command = self._make_command(TURN_OFF_CODE)
                response_bytes_list = self.send_and_get_response(turn_off_command)
                response_string = response_bytes_list[0].decode("ASCII")
                status_code = response_string[3:5]
                if(status_code == "OK"):
                    return True
                else:
                    return False
            elif(self.pump_label == "mpc"):
                data_field_1 = '1'
                data_field_2 = '2'
                turn_off_command_1 = self._make_command(TURN_OFF_CODE, data_field = data_field_1)
                turn_off_command_2 = self._make_command(TURN_OFF_CODE, data_field = data_field_2)
                response_1_bytes_list = self.send_and_get_response(turn_off_command_1) 
                response_1_string = response_1_bytes_list[0].decode("ASCII")
                response_2_bytes_list = self.send_and_get_response(turn_off_command_2) 
                response_2_string = response_2_bytes_list[0].decode("ASCII")
                response_1_status_code = response_1_string[3:5]
                response_2_status_code = response_2_string[3:5]
                if(response_1_status_code == "OK" and response_2_status_code == "OK"):
                    return True
        except IndexError as e:
            return False
            


    """Convenience function which makes a command to be sent to the pump.

    Given a command code and, optionally, a data field, automatically prepares a 
    string command with the correct checksum, termination, etc. 

    Params:
        command_code: str, the two byte command code to be sent
        data_field: str, the data field to be sent if needed. If None, no data field is added.
    Remark: Neither the data field nor the command code should include delimiting spaces; these 
    are automatically added.

    Returns:
        A str containing the properly formatted command, suitable to be sent to the ion pump by send()

    """
    def _make_command(self, command_code, data_field = None):
        address_string = self.get_address_string()
        command_initial = ' ' + address_string + ' ' + command_code + ' '
        if(not (data_field is None)):
            command_initial = command_initial + data_field + ' '
        checksum_string = self.get_checksum_string(command_initial) 
        command_final = '~' + command_initial + checksum_string + "\r"
        return command_final 

    @staticmethod
    def parse_current_bytes(current_bytes_list):
        current_string = current_bytes_list[0].decode("ASCII")
        status_code = current_string[3:5]
        if(status_code == "OK"):
            current_value_string = current_string[9:15]
            current_value = float(current_value_string)
            return current_value
        else:
            return -1
        
    @staticmethod
    def parse_pressure_bytes(pressure_bytes_list):
        pressure_string = pressure_bytes_list[0].decode("ASCII")
        status_code = pressure_string[3:5]
        if(status_code == "OK"):
            pressure_value_string = pressure_string[9:15]
            pressure_value = float(pressure_value_string) 
            return pressure_value
        else:
            return -1

    @staticmethod
    def parse_voltage_bytes(voltage_bytes_list):
        voltage_string = voltage_bytes_list[0].decode("ASCII")
        status_code = voltage_string[3:5]
        if(status_code == "OK"):
            voltage_value_string = voltage_string[9:13]
            voltage_value = int(voltage_value_string)
            return voltage_value 
        else:
            return -1



    def get_address_string(self):
        address_string = hex(self.address)[2:]
        address_string = address_string.upper() 
        if(self.address < 16):
            address_string = "0" + address_string 
        return address_string 

    @staticmethod
    def get_checksum_string(checked_string):
        checksum_val = 0
        for byte in checked_string.encode("ASCII"):
            checksum_val += int(byte) 
        checksum_val = checksum_val % 256
        checksum_string = hex(checksum_val)[2:]
        checksum_string = checksum_string.upper() 
        if(checksum_val < 16):
            checksum_string = "0" + checksum_string
        return checksum_string

    def send_and_get_response(self, command, add_checksum_and_end = False):
        self.send(command, add_checksum_and_end= add_checksum_and_end)
        return self.serial_port.readlines()


    # def sendrecv(self, cmd):
    #     """Send a command and (optionally) printing the picomotor driver's response."""
    #     res = self.send(cmd)
    #     if self.echo:
    #         time.sleep(self.wait)
    #         ret_str = self.readlines()
    #         self.log(ret_str, widget=self.recvwidget)
    #     return res




    # def __init__(self, COM_PORT, echo=True, wait=0.1, sendwidget=None, recvwidget=None):
    #     """
    #     Args: 
    #     - COM_PORT: str, e.g. 'COM7'
    #     - FILL OUT:
    #     """
    #     COM_SETTINGS = dict(baudrate=9600, bytesize=serial.EIGHTBITS,
    #                         parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
    #                         timeout=1)
    #     super.__init__(COM_PORT, **COM_SETTINGS)
    #     self.echo = echo
    #     self.wait = wait
    #     self.sendwidget = sendwidget
    #     self.recvwidget = recvwidget
    #     self.history = {}
    #     for idx in range(1, 4):
    #         self.history[str(idx)] = {str(idx): OrderedDict()
    #                                   for idx in range(0, 3)}
    #     self.MAX_LENGTH = 1e3

    #     def construct_cmd(args):
    #     """Returns bytes object to be sent over COM port to ion pump."""
    #         def calculate_checksum(args):
    #             pass
    #         pass
    #     command_codes = {}  # key, val pairs of string descriptor and 2 character hex codes
    #     self.command_dict = command_dict

    # def send(self, cmd):
    #     """Send a command to the picomotor driver."""
    #     line = cmd + '\r\n'
    #     retval = self.write(bytes(line, encoding='ascii'))
    #     self.flush()
    #     if self.echo:
    #         self.log(cmd, widget=self.sendwidget)
    #     time.sleep(self.wait)
    #     return retval

    # def readlines(self):
    #     """Read response from picomotor driver."""
    #     return ''.join([l.decode('ASCII') for l in self.readlines()])

    def log(self, msg, widget=None):
        if widget is None:
            print(msg, flush=True)
        else:
            widget.value = msg

    # def sendrecv(self, cmd):
    #     """Send a command and (optionally) printing the picomotor driver's response."""
    #     res = self.send(cmd)
    #     if self.echo:
    #         time.sleep(self.wait)
    #         ret_str = self.readlines()
    #         self.log(ret_str, widget=self.recvwidget)
    #     return res
