"""
Library to control the picomotor driver.
"""

import serial
import time
import datetime
from collections import OrderedDict
from random import randint
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
import warnings
import matplotlib.cbook
warnings.filterwarnings("ignore",category=matplotlib.cbook.mplDeprecation)


class MSerial:
    axis_names = dict(x=0, y=1)
    unit = dict(x=1, y=1)
    
    def __init__(self, port, echo=True, max_retry=2, wait=0.1, sendwidget=None, recvwidget=None, **serial_kws):
        kws = dict(baudrate=19200, bytesize=serial.EIGHTBITS, 
                   parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, 
                   timeout=0, xonxoff=True, rtscts=False, dsrdtr=False)
        kws.update(serial_kws)
        self.serial = serial.Serial(port, **kws)
        self.echo = echo
        self.wait = wait
        self.sendwidget = sendwidget
        self.recvwidget = recvwidget
        self.history = {}
        for idx in range(1, 4):
            self.history['driver{idx}'.format(
                idx=str(idx))] = {'m{idx}'.format(
                    idx=str(idx)): OrderedDict() for idx in range(0, 3)}
        self.MAX_LENGTH = 1e3

    def send(self, cmd):
        """Send a command to the picomotor driver."""
        line = cmd + '\r\n'
        retval = self.serial.write(bytes(line, encoding='ascii'))
        self.serial.flush()
        if self.echo:
            self.log(cmd, widget=self.sendwidget)
        return retval
    
    def readlines(self):
        """Read response from picomotor driver."""
        return ''.join([l.decode('ASCII') for l in self.serial.readlines()])
    
    def log(self, msg, widget=None):
        if widget is None:
            print(msg, flush=True)
        else:
            widget.value = msg
        
    def sendrecv(self, cmd):
        """Send a command and (optionally) printing the picomotor driver's response."""
        res = self.send(cmd) 
        if self.echo:
            time.sleep(self.wait)
            ret_str = self.readlines()
            self.log(ret_str, widget=self.recvwidget)
        return res

    def update_motor_history(self, driver_idx, motor_idx, step_size):
        # TODO

        driver_key = 'driver{i}'.format(i=str(driver_idx))
        motor_key = 'm{i}'.format(i=str(motor_idx))
        # time_now = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        time_now = datetime.datetime.today()
        self.history[driver_key][motor_key][time_now] = step_size
        if len(self.history[driver_key][motor_key]) > self.MAX_LENGTH:
            self.history[driver_key][motor_key].popitem(last=False)
        print(time_now)

    def move(self, driver_idx, motor_idx, step_size):
        time.sleep(self.wait)
        active_motor_cmd = 'chl a{driver}={motor}'.format(driver=str(driver_idx), motor=str(motor_idx))
        self.sendrecv(active_motor_cmd)
        time.sleep(self.wait)
        move_cmd = 'rel {driver} {step} g'.format(driver=str(driver_idx), step=str(step_size))
        self.sendrecv(move_cmd)
        print('motor {motor} on driver a{driver} moved {step} steps'.format(motor=str(motor_idx),
                                                                            driver=str(driver_idx), 
                                                                            step=str(step_size)))
        self.update_motor_history(driver_idx, motor_idx, step_size)
        
    def status_msg(self):
        """Return the driver status byte as an integer (see manual pag. 185)."""
        self.send('STA')
        time.sleep(self.wait)
        ret_str = self.readlines()
        if self.echo:
            self.log(repr(ret_str), widget=self.recvwidget)
        return ret_str
    
    def status(self):
        ret_str = self.status_msg()
        i = ret_str.find('A1=')
        if i >= 0:
            status = int(ret_str[i+5:i+7], 16)
        else:
            raise IOError("Received: '%s'" % ret_str)
        return status
    
    def is_moving(self):
        """Return True if motor is moving, else False."""
        status = self.status()
        return status & 0x01

    def plot_positions(self, xaxis='move_idx'):
        plt.style.use('seaborn')
        i = 1
        for driver_key in self.history:
            for motor_key in self.history[driver_key]:
                # if len(self.history[driver_key][motor_key]) == 0:
                #     continue
                plt.subplot(len(self.history), 2, i)
                x_data = list(self.history[driver_key][motor_key].keys())
                y_data = np.cumsum(list(self.history[driver_key][motor_key].values()))
                plt.plot(x_data, y_data, marker = 'o', linestyle='dashed', label=str(driver_key) + str(motor_key))

                plt.legend(loc='best')
                plt.xlabel('time (TODO: formatting)')
                plt.ylabel('position')
            i += 2
        i = 2
        for driver_key in self.history:
            for motor_key in self.history[driver_key]:
                # if len(self.history[driver_key][motor_key]) == 0:
                #     continue
                plt.subplot(len(self.history), 2, i)
                x_data = list(self.history[driver_key][motor_key].keys())
                y_data = list(self.history[driver_key][motor_key].values())
                plt.plot(x_data, y_data, marker = 'o', linestyle='dotted', label=str(driver_key) + str(motor_key))
                plt.legend(loc='best')
                plt.xlabel('time (TODO: formatting)')
                plt.ylabel('step size')
            i += 2

        plt.tight_layout()
        plt.show()

    def pickle(self):
        #save histories in .pkl file
        pass


picomotor = MSerial('COM4')
print('\n INFO: picomotor has methods picomotor.move(driver_idx, motor_idx, step_size), picomotor.plot_positions() \n')