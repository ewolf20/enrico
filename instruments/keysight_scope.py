# import os
# import sys
# main_path = os.path.abspath(os.path.join(__file__, '../..'))
# sys.path.insert(0, main_path)
import visa
import numpy as np
import pandas as pd
from status_monitor import StatusMonitor
import time
import parse
import matplotlib.pyplot as plt

rm = visa.ResourceManager('C:\\Windows\\System32\\visa64.dll')
scope_visa_addresses = {'near laser tables':"TCPIP0::192.168.1.9::inst0::INSTR",
                        'near control PC':"TCPIP0::192.168.1.11::inst0::INSTR"}


class Oscilloscope():
    """docstring for Oscilloscope"""

    def __init__(self, visa_address):
        GLOBAL_TOUT = 10000
        self.scope_obj = rm.open_resource(visa_address)
        self.scope_obj.timeout = GLOBAL_TOUT

    def __enter__(self):
        if self.scope_obj.session == 3:
            self.scope_obj = rm.open_resource(visa_address)
        return self.scope_obj

    def __exit__(self, type, value, traceback):
        self.scope_obj.close()

    def acquire_traces(self):
        USER_REQUESTED_POINTS = 1000
        with self.scope_obj as scope_obj:
            scope_obj.clear()
            scope_obj.write(':STOP')
            # Get Number of analog channels on scope
            IDN = str(scope_obj.query("*IDN?"))
            # Parse IDN
            IDN = IDN.split(',') # IDN parts are separated by commas, so parse on the commas
            MODEL = IDN[1]
            if list(MODEL[1]) == "9": # This is the test for the PXIe scope, M942xA)
                NUMBER_ANALOG_CHS = 2
            else:
                NUMBER_ANALOG_CHS = int(MODEL[len(MODEL)-2])
            if NUMBER_ANALOG_CHS == 2:
                CHS_LIST = [0,0] # Create empty array to store channel states
            else:
                CHS_LIST = [0,0,0,0]
            NUMBER_CHANNELS_ON = 0
            # After the CHS_LIST array is filled it could, for example look like: if chs 1,3 and 4 were on, CHS_LIST = [1,0,1,1]

            ###############################################
            # Pre-allocate holders for the vertical Pre-ambles and Channel units

            ANALOGVERTPRES = np.zeros([12])
                # For readability: ANALOGVERTPRES = (Y_INCrement_Ch1, Y_INCrement_Ch2, Y_INCrement_Ch3, Y_INCrement_Ch4, Y_ORIGin_Ch1, Y_ORIGin_Ch2, Y_ORIGin_Ch3, Y_ORIGin_Ch4, Y_REFerence_Ch1, Y_REFerence_Ch2, Y_REFerence_Ch3, Y_REFerence_Ch4)

            CH_UNITS = ["BLANK", "BLANK", "BLANK", "BLANK"]

            #########################################
            # Actually find which channels are on, have acquired data, and get the pre-amble info if needed.
            # The assumption here is that, if the channel is off, even if it has data behind it, data will not be retrieved from it.
            # Note that this only has to be done once for repetitive acquisitions if the channel scales (and on/off) are not changed.

            scope_obj.write(":WAVeform:POINts:MODE MAX") # MAX mode works for all acquisition types, so this is done here to avoid Acq. Type vs points mode problems. Adjusted later for specific acquisition types.

            ch = 1 # Channel number
            for each_value in CHS_LIST:
                On_Off = int(scope_obj.query(":CHANnel" + str(ch) + ":DISPlay?")) # Is the channel displayed? If not, don't pull.
                if On_Off == 1: # Only ask if needed... but... the scope can acquire waveform data even if the channel is off (in some cases) - so modify as needed
                    Channel_Acquired = int(scope_obj.query(":WAVeform:SOURce CHANnel" + str(ch) + ";POINts?")) # If this returns a zero, then this channel did not capture data and thus there are no points
                    # Note that setting the :WAV:SOUR to some channel has the effect of turning it on
                else:
                    Channel_Acquired = 0
                if Channel_Acquired == 0 or On_Off == 0: # Channel is off or no data acquired
                    scope_obj.write(":CHANnel" + str(ch) + ":DISPlay OFF") # Setting a channel to be a waveform source turns it on... so if here, turn it off.
                    CHS_LIST[ch-1] = 0 # Recall that python indices start at 0, so ch1 is index 0
                else: # Channel is on AND data acquired
                    CHS_LIST[ch-1] = 1 # After the CHS_LIST array is filled it could, for example look like: if chs 1,3 and 4 were on, CHS_LIST = [1,0,1,1]
                    NUMBER_CHANNELS_ON += 1
                    # Might as well get the pre-amble info now
                    Pre = scope_obj.query(":WAVeform:PREamble?").split(',') # ## The programmer's guide has a very good description of this, under the info on :WAVeform:PREamble.
                        # In above line, the waveform source is already set; no need to reset it.
                    ANALOGVERTPRES[ch-1]  = float(Pre[7]) # Y INCrement, Voltage difference between data points; Could also be found with :WAVeform:YINCrement? after setting :WAVeform:SOURce
                    ANALOGVERTPRES[ch+3]  = float(Pre[8]) # Y ORIGin, Voltage at center screen; Could also be found with :WAVeform:YORigin? after setting :WAVeform:SOURce
                    ANALOGVERTPRES[ch+7]  = float(Pre[9]) # Y REFerence, Specifies the data point where y-origin occurs, always zero; Could also be found with :WAVeform:YREFerence? after setting :WAVeform:SOURce
                    # In most cases this will need to be done for each channel as the vertical scale and offset will differ. However,
                        # if the vertical scales and offset are identical, the values for one channel can be used for the others.
                        # For math waveforms, this should always be done.
                    CH_UNITS[ch-1] = str(scope_obj.query(":CHANnel" + str(ch) + ":UNITs?").strip('\n')) # This isn't really needed but is included for completeness
                ch += 1
            del ch, each_value, On_Off, Channel_Acquired

            ##########################
            if NUMBER_CHANNELS_ON == 0:
                scope_obj.clear()
                scope_obj.close()
                sys.exit("No data has been acquired. Properly closing scope and aborting script.")

            ############################################
            # Find first channel on (as needed/desired)
            ch = 1
            for each_value in CHS_LIST:
                if each_value == 1:
                    FIRST_CHANNEL_ON = ch
                    break
                ch +=1
            del ch, each_value

            ############################################
            # Find last channel on (as needed/desired)
            ch = 1
            for each_value in CHS_LIST:
                if each_value == 1:
                    LAST_CHANNEL_ON = ch
                ch +=1
            del ch, each_value

            ############################################
            # Create list of Channel Numbers that are on
            CHS_ON = [] # Empty list
            ch = 1
            for each_value in CHS_LIST:
                if each_value == 1:
                    CHS_ON.append(int(ch)) # for example, if chs 1,3 and 4 were on, CHS_ON = [1,3,4]
                ch +=1
            del ch, each_value

            #####################################################

            ################################################################################################################
            # Setup data export - For repetitive acquisitions, this only needs to be done once unless settings are changed

            scope_obj.write(":WAVeform:FORMat WORD") # 16 bit word format... or BYTE for 8 bit format - WORD recommended, see more comments below when the data is actually retrieved
                # WORD format especially  recommended  for Average and High Res. Acq. Types, which can produce more than 8 bits of resolution.
            scope_obj.write(":WAVeform:BYTeorder LSBFirst") # Explicitly set this to avoid confusion - only applies to WORD FORMat
            scope_obj.write(":WAVeform:UNSigned 0") # Explicitly set this to avoid confusion

            #####################################################################################################################################
            #####################################################################################################################################
            # Set and get points to be retrieved - For repetitive acquisitions, this only needs to be done once unless scope settings are changed
            # This is non-trivial, but the below algorithm always works w/o throwing an error, as long as USER_REQUESTED_POINTS is a positive whole number (positive integer)

            #########################################################
            # Determine Acquisition Type to set points mode properly

            ACQ_TYPE = str(scope_obj.query(":ACQuire:TYPE?")).strip("\n")
                    # This can also be done when pulling pre-ambles (pre[1]) or may be known ahead of time, but since the script is supposed to find everything, it is done now.
            if ACQ_TYPE == "AVER" or ACQ_TYPE == "HRES": # Don't need to check for both types of mnemonics like this: if ACQ_TYPE == "AVER" or ACQ_TYPE == "AVERage": becasue the scope ALWAYS returns the short form
                POINTS_MODE = "NORMal" # Use for Average and High Resoultion acquisition Types.
                    # If the :WAVeform:POINts:MODE is RAW, and the Acquisition Type is Average, the number of points available is 0. If :WAVeform:POINts:MODE is MAX, it may or may not return 0 points.
                    # If the :WAVeform:POINts:MODE is RAW, and the Acquisition Type is High Resolution, then the effect is (mostly) the same as if the Acq. Type was Normal (no box-car averaging).
                    # Note: if you use :SINGle to acquire the waveform in AVERage Acq. Type, no average is performed, and RAW works. See sample script "InfiniiVision_2_Simple_Synchronization_Methods.py"
            else:
                POINTS_MODE = "RAW" # Use for Acq. Type NORMal or PEAK
                # Note, if using "precision mode" on 5/6/70000s or X6000A, then you must use POINTS_MODE = "NORMal" to get the "precision record."

            # Note:
                # :WAVeform:POINts:MODE RAW corresponds to saving the ASCII XY or Binary data formats to a USB stick on the scope
                # :WAVeform:POINts:MODE NORMal corresponds to saving the CSV or H5 data formats to a USB stick on the scope

            ###########################################################################################################
            # Find max points for scope as is, ask for desired points, find how many points will actually be returned
                # KEY POINT: the data must be on screen to be retrieved.  If there is data off-screen, :WAVeform:POINts? will not "see it."
                    # Addendum 1 shows how to properly get all data on screen, but this is never needed for Average and High Resolution Acquisition Types,
                    # since they basically don't use off-screen data; what you see is what you get.

            # First, set waveform source to any channel that is known to be on and have points, here the FIRST_CHANNEL_ON - if we don't do this, it could be set to a channel that was off or did not acquire data.
            scope_obj.write(":WAVeform:SOURce CHANnel" + str(FIRST_CHANNEL_ON))

            # The next line is similar to, but distinct from, the previously sent command ":WAVeform:POINts:MODE MAX".  This next command is one of the most important parts of this script.
            scope_obj.write(":WAVeform:POINts MAX") # This command sets the points mode to MAX AND ensures that the maximum # of points to be transferred is set, though they must still be on screen

            # Since the ":WAVeform:POINts MAX" command above also changes the :POINts:MODE to MAXimum, which may or may not be a good thing, so change it to what is needed next.
            scope_obj.write(":WAVeform:POINts:MODE " + str(POINTS_MODE))
            # If measurements are also being made, they are made on the "measurement record."  This record can be accessed by using:
                # :WAVeform:POINts:MODE NORMal instead of :WAVeform:POINts:MODE RAW
                # Please refer to the progammer's guide for more details on :WAV:POIN:MODE RAW/NORMal/MAX

            # Now find how many points are actually currently available for transfer in the given points mode (must still be on screen)
            MAX_CURRENTLY_AVAILABLE_POINTS = int(scope_obj.query(":WAVeform:POINts?")) # This is the max number of points currently available - this is for on screen data only - Will not change channel to channel.
            # NOTES:
                # For getting ALL of the data off of the scope, as opposed to just what is on screen, see Addendum 1
                # For getting ONLY CERTAIN data points, see Addendum 2
                # The methods shown in these addenda are combinable
                # The number of points can change with the number of channels that have acquired data, the Acq. Mode, Acq Type, time scale (they must be on screen to be retrieved),
                    # number of channels on, and the acquisition method (:RUNS/:STOP, :SINGle, :DIGitize), and :WAV:POINts:MODE

            # The scope will return a -222,"Data out of range" error if fewer than 100 points are requested, even though it may actually return fewer than 100 points.
            if USER_REQUESTED_POINTS < 100:
                USER_REQUESTED_POINTS = 100
            # One may also wish to do other tests, such as: is it a whole number (integer)?, is it real? and so forth...

            if MAX_CURRENTLY_AVAILABLE_POINTS < 100:
                MAX_CURRENTLY_AVAILABLE_POINTS = 100

            if USER_REQUESTED_POINTS > MAX_CURRENTLY_AVAILABLE_POINTS or ACQ_TYPE == "PEAK":
                 USER_REQUESTED_POINTS = MAX_CURRENTLY_AVAILABLE_POINTS
                 # Note: for Peak Detect, it is always suggested to transfer the max number of points available so that narrow spikes are not missed.
                 # If the scope is asked for more points than :ACQuire:POINts? (see below) yields, though, not necessarily MAX_CURRENTLY_AVAILABLE_POINTS, it will throw an error, specifically -222,"Data out of range"

            # If one wants some other number of points...
            # Tell it how many points you want
            scope_obj.write(":WAVeform:POINts " + str(USER_REQUESTED_POINTS))

            # Then ask how many points it will actually give you, as it may not give you exactly what you want.
            NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE = int(scope_obj.query(":WAVeform:POINts?"))
            # Warn user if points will be less than requested, if desired...
            # Note that if less than the max is set, it will stay at that value (or whatever is closest) until it is changed again, even if the time base is changed.
            # What does the scope return if less than MAX_CURRENTLY_AVAILABLE_POINTS is returned?
                # It depends on the :WAVeform:POINts:MODE
                # If :WAVeform:POINts:MODE is RAW
                    # The scope decimates the data, only returning every Nth point.
                    # The points are NOT re-mapped; the values of the points, both vertical and horizontal, are preserved.
                    # Aliasing, lost pulses and transitions, are very possible when this is done.
                # If :WAVeform:POINts:MODE is NORMal
                    # The scope re-maps this "measurement record" down to the number of points requested to give the best representation of the waveform for the requested number of points.
                    # This changes both the vertical and horizontal values.
                    # Aliasing, lost pulses and transitions, are definitely possible, though less likely for well displayed waveforms in many, but not all, cases.

            # This above method always works w/o errors.  In summary, after an acquisition is complete:
                    # Set POINts to MAX
                    # Set :POINts:MODE as desired/needed
                    # Ask for the number of points available.  This is the MOST the scope can give for current settings/timescale/Acq. Type
                    # Set a different number of points if desired and if less than above
                    # Ask how many points it will actually return, use that

            # What about :ACQUIRE:POINTS?
            # The Programmers's Guide says:
                # The :ACQuire:POINts? query returns the number of data points that the
                # hardware will acquire from the input signal. The number of points
                # acquired is not directly controllable. To set the number of points to be
                # transferred from the oscilloscope, use the command :WAVeform:POINts. The
                # :WAVeform:POINts? query will return the number of points available to be
                # transferred from the oscilloscope.

            # It is not a terribly useful query. It basically only gives the max amount of points available for transfer if:
                    # The scope is stopped AND has acquired data the way you want to use it and the waveform is entirely on screen
                        # In other words, if you do a :SINGle, THEN turn on, say digital chs, this will give the wrong answer for digital chs on for the next acquisition.
                    # :POINts:MODE is RAW or MAX - thus it DOES NOT work for Average or High Res. Acq. Types, which need NORMal!
                    # and RUN/STOP vs SINGle vs :DIG makes a difference!
                    # and Acq. Type makes a difference! (it can be misleading for Average or High Res. Acq. Types)
                    # and all of the data is on screen!
                    # Thus it is not too useful here.
            # What it is good for is:
                # 1. determining if there is off screen data, for Normal or Peak Detect Acq. Types, after an acquisition is complete, for the current settings (compare this result with MAX_CURRENTLY_AVAILABLE_POINTS).
                # 2. finding the max possible points that could possibly be available for Normal or Peak Detect Acq. Types, after an acquisition is complete, for the current settings, if all of the data is on-screen.

            #####################################################################################################################################
            #####################################################################################################################################
            # Get timing pre-amble data and create time axis
            # One could just save off the preamble factors and #points and post process this later...

            Pre = scope_obj.query(":WAVeform:PREamble?").split(',') # This does need to be set to a channel that is on, but that is already done... e.g. Pre = scope_obj.query(":WAVeform:SOURce CHANnel" + str(FIRST_CHANNEL_ON) + ";PREamble?").split(',')
            # While these values can always be used for all analog channels, they need to be retrieved and used separately for math/other waveforms as they will likely be different.
            # ACQ_TYPE    = float(Pre[1]) # Gives the scope Acquisition Type; this is already done above in this particular script
            X_INCrement = float(Pre[4]) # Time difference between data points; Could also be found with :WAVeform:XINCrement? after setting :WAVeform:SOURce
            X_ORIGin    = float(Pre[5]) # Always the first data point in memory; Could also be found with :WAVeform:XORigin? after setting :WAVeform:SOURce
            X_REFerence = float(Pre[6]) # Specifies the data point associated with x-origin; The x-reference point is the first point displayed and XREFerence is always 0.; Could also be found with :WAVeform:XREFerence? after setting :WAVeform:SOURce
            # This could have been pulled earlier...
            del Pre
                # The programmer's guide has a very good description of this, under the info on :WAVeform:PREamble.
                # This could also be reasonably be done when pulling the vertical pre-ambles for any channel that is on and acquired data.
                # This is the same for all channels.
                # For repetitive acquisitions, it only needs to be done once unless settings change.

            DataTime = ((np.linspace(0,NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE-1,NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE)-X_REFerence)*X_INCrement)+X_ORIGin
            if ACQ_TYPE == "PEAK": # This means Peak Detect Acq. Type
                DataTime = np.repeat(DataTime,2)
                # The points come out as Low(time1),High(time1),Low(time2),High(time2)....
                # SEE IMPORTANT NOTE ABOUT PEAK DETECT AT VERY END, specific to fast time scales

            #####################################################################################################################################
            #####################################################################################################################################
            # Pre-allocate data array
                # Obviously there are numerous ways to actually place data  into an array... this is just one

            if ACQ_TYPE == "PEAK": # This means peak detect mode ### SEE IMPORTANT NOTE ABOUT PEAK DETECT MODE AT VERY END, specific to fast time scales
                Wav_Data = np.zeros([2*NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE,NUMBER_CHANNELS_ON])
                # Peak detect mode returns twice as many points as the points query, one point each for LOW and HIGH values
            else: # For all other acquistion modes
                Wav_Data = np.zeros([NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE,NUMBER_CHANNELS_ON])

            ###################################################################################################
            ###################################################################################################
            # Determine number of bytes that will actually be transferred and set the "chunk size" accordingly.

                # When using PyVisa, this is in fact completely unnecessary, but may be needed in other leagues, MATLAB, for example.
                # However, the benefit in Python is that the transfers can take less time, particularly longer ones.

            # Get the waveform format
            WFORM = str(scope_obj.query(":WAVeform:FORMat?"))
            if WFORM == "BYTE":
                FORMAT_MULTIPLIER = 1
            else: #WFORM == "WORD"
                FORMAT_MULTIPLIER = 2

            if ACQ_TYPE == "PEAK":
                POINTS_MULTIPLIER = 2 # Recall that Peak Acq. Type basically doubles the number of points.
            else:
                POINTS_MULTIPLIER = 1

            TOTAL_BYTES_TO_XFER = POINTS_MULTIPLIER * NUMBER_OF_POINTS_TO_ACTUALLY_RETRIEVE * FORMAT_MULTIPLIER + 11
                # Why + 11?  The IEEE488.2 waveform header for definite length binary blocks (what this will use) consists of 10 bytes.  The default termination character, \n, takes up another byte.
                    # If you are using mutliplr termination characters, adjust accordingly.
                # Note that Python 2.7 uses ASCII, where all characters are 1 byte.  Python 3.5 uses Unicode, which does not have a set number of bytes per character.

            # Set chunk size:
                # More info @ http://pyvisa.readthedocs.io/en/stable/resources.html
            if TOTAL_BYTES_TO_XFER >= 400000:
                scope_obj.chunk_size = TOTAL_BYTES_TO_XFER
            # else:
                # use default size, which is 20480

            # Any given user may want to tweak this for best throughput, if desired.  The 400,000 was chosen after testing various chunk sizes over various transfer sizes, over USB,
                # and determined to be the best, or at least simplest, cutoff.  When the transfers are smaller, the intrinsic "latencies" seem to dominate, and the default chunk size works fine.

            # How does the default chuck size work?
                # It just pulls the data repeatedly and sequentially (in series) until the termination character is found...

            # Do I need to adjust the timeout for a larger chunk sizes, where it will pull up to an entire 8,000,000 sample record in a single IO transaction?
                # If you use a 10s timeout (10,000 ms in PyVisa), that will be good enough for USB and LAN.
                # If you are using GPIB, which is slower than LAN or USB, quite possibly, yes.
                # If you don't want to deal with this, don't set the chunk size, and use a 10 second timeout, and everything will be fine in Python.
                    # When you use the default chunk size, there are repeated IO transactions to pull the total waveform.  It is each individual IO transaction that needs to complete within the timeout.

            #####################################################
            #####################################################
            # Pull waveform data, scale it

            i  = 0 # index of Wav_data, recall that python indices start at 0, so ch1 is index 0
            for channel_number in CHS_ON:
                    # Gets the waveform in 16 bit WORD format
                # The below method uses an IEEE488.2 compliant definite length binary block transfer invoked by :WAVeform:DATA?.
                    # ASCII transfers are also possible, but MUCH slower.
                    Wav_Data[:,i] = np.array(scope_obj.query_binary_values(':WAVeform:SOURce CHANnel' + str(channel_number) + ';DATA?', "h", False)) # See also: https://PyVisa.readthedocs.io/en/stable/rvalues.html#reading-binary-values
                    # Here, WORD format, LSBF, and signed integers are used (these are the scope settings in this script).  The query_binary_values function must be setup the same (https://docs.python.org/2/library/struct.html#format-characters):
                        # For BYTE format and unsigned, use "b" instead of "h"; b is a signed char; see link from above line
                        # For BYTE format and signed,   use "B" instead of "h"; B is an unsigned char
                        # For WORD format and unsigned, use "h"; h is a short
                        # For WORD format and signed,   use "H" instead of "h"; H is an unsigned short
                        # For MSBFirst use True (Don't use MSBFirst unless that is the computer architecture - most common WinTel are LSBF - see sys.byteorder @ https://docs.python.org/2/library/sys.html)

                     # WORD is more accurate, but slower for long records, say over 100 kPts.
                     # WORD strongly suggested for Average and High Res. Acquisition Types.

                    # query_binary_values() is a PyVisa specific IEEE 488.2 binary block reader.  Most languages have a similar function.
                        # The InfiniiVision and InfiniiVision-X scopes always return a definite length binary block in response to the :WAVeform:DATA? querry
                        # query_binary_values() does also read the termination character, but this is not always the case in other languages (MATLAB, for example)
                            # In that case, another read is needed to read the termination character (or a device clear).
                        # In the case of Keysight VISA (IO Libraries), the default termination character is '\n' but this can be changed, depending on the interface....
                            # For more on termination characters: https://PyVisa.readthedocs.io/en/stable/resources.html#termination-characters

                    # Notice that the waveform source is specified, and the actual data query is concatenated into one line with a semi-colon (;) essentially like this:
                        # :WAVeform:SOURce CHANnel1;DATA?
                        # This makes it "go" a little faster.

                    # When the data is being exported w/ :WAVeform:DATA?, the oscilloscope front panel knobs don't work; they are blocked like :DIGitize, and the actions take effect AFTER the data transfer is complete.
                    # The :WAVeform:DATA? query can be interrupted without an error by doing a device clear: scope_obj.clear()

                    # Scales the waveform
                    # One could just save off the preamble factors and post process this later.
                    Wav_Data[:,i] = ((Wav_Data[:,i]-ANALOGVERTPRES[channel_number+7])*ANALOGVERTPRES[channel_number-1])+ANALOGVERTPRES[channel_number+3]
                        # For clarity: Scaled_waveform_Data[*] = [(Unscaled_Waveform_Data[*] - Y_reference) * Y_increment] + Y_origin

                    i +=1

            # Reset the chunk size back to default if needed.
            if TOTAL_BYTES_TO_XFER >= 400000:
                scope_obj.chunk_size = 20480
                # If you don't do this, and now wanted to do something else... such as ask for a measurement result, and leave the chunk size set to something large,
                    # it can really slow down the script, so set it back to default, which works well.

            del i, channel_number

            ###################################################################
            ###################################################################
            # Done with scope operations - resume scope live mode
            scope_obj.write(':RUN')
            scope_obj.clear()
        #TODO check if a time column is the 0th column of Wav_Data
        #TODO standardize units to be V (not mV)
        Wav_Data = np.insert(Wav_Data,0,DataTime,axis=1)
        columns = ['time'] + ['ch{idx}_in_{unit}'.format(idx=str(i+1), unit=str(CH_UNITS[i])) 
                    for i in range(len(CH_UNITS))]
        scope_traces = pd.DataFrame(Wav_Data, 
            columns = columns)
        return scope_traces

    @staticmethod
    def plot_traces(scope_traces):
        plt.close('all')
        i = 1
        for column in scope_traces.columns:
            if column == 'time':
                continue
            plt.subplot(len(scope_traces.columns) - 1, 1, i)
            plt.plot(scope_traces['time'], scope_traces[column])
            i+=1
        plt.show()

class LockDetector(StatusMonitor):
    """docstring for LockDetector"""
    def __init__(self, visa_address, channel = None, refresh_time = 5):
        StatusMonitor.__init__(self)
        self.scope = Oscilloscope(visa_address)
        self.low_level = float(input('Enter low level in volts: '))
        if channel is None:
            self.channel = int(input('Which channel is the lock signal on? '))
        else:
            self.channel = channel
        self.refresh_time = refresh_time
        self.name = input('What laser are you monitoring? e.g. dye or TiSa ')

    def main(self):
        scope = self.scope
        i=0
        while i<10:
            scope_traces = scope.acquire_traces()
            for column in scope_traces.columns:
                if 'ch{idx}'.format(idx=str(self.channel)) in column:
                    lock_trace = np.array(scope_traces[column])
                    break
            _, unit = parse.parse('{}_in_{}', column)
            lock_dict = {'{name}lockPDmin_in_{unit}'.format(name = self.name, unit=unit): np.min(lock_trace),
                         '{name}lockPDmax_in_{unit}'.format(name = self.name, unit=unit): np.max(lock_trace),
                         '{name}lockPDmean_in_{unit}'.format(name = self.name, unit=unit): np.mean(lock_trace)}
            if np.min(lock_trace) < self.low_level:
                self.warn_on_slack('{name} laser out of lock'.format(name=self.name))
            else:
                print(lock_dict)
                print('{name} laser locked'.format(name=self.name))
            self.append_to_backlog(lock_dict)
            # self.upload_to_breadboard() 
            time.sleep(self.refresh_time)
            i+=1

#testing code
# lockdetector = LockDetector(visa_address=scope_visa_addresses['near laser tables'])
# lockdetector.main()
scope = Oscilloscope(visa_address=scope_visa_addresses['near laser tables'])
for i in range(3):
    breakpoint()
    traces = scope.acquire_traces()
    print(traces)
# scope.plot_traces(traces)