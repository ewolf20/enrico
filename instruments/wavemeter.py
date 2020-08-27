# append main enrico folder to python path
import os
import sys
main_path = os.path.abspath(os.path.join(__file__, '../..'))
sys.path.insert(0, main_path)

from utility_functions import load_breadboard_client, get_newest_run_dict, time_diff_in_sec
import datetime
import time
from collections import OrderedDict
import numpy as np
bc = load_breadboard_client()

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

file_handler = logging.FileHandler(os.path.join(
    os.path.dirname(__file__), 'wavemeter_debugging.log'))
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

import enrico_bot


def main():
    refresh_time = 1  # seconds
    print('Reading wavemeter... \n')
    old_run_id = None
    warned = False
    wavemeter_backlog = OrderedDict()
    max_length = 30
    # Main Loop
    while True:
        wavemeter_reading = 42  # TODO: replace this!
        wavemeter_backlog[datetime.datetime.today()] = wavemeter_reading
        print('wavemeter reading: {reading}'.format(
            reading=str(wavemeter_reading)))
        if len(wavemeter_backlog) > max_length:
            wavemeter_backlog.popitem(last=False)

        # listen to breadboard server for new run_id
        try:
            new_run_dict = get_newest_run_dict(bc)
            new_run_id = new_run_dict['run_id']
        except:
            logger.error(sys.exc_info()[1])
            pass

        # log new run_id
        if new_run_id != old_run_id:
            logger.debug('list bound variables: {run_dict}'.format(run_dict={key: new_run_dict[key]
                                                                             for key in new_run_dict['ListBoundVariables']}))
            logger.debug(
                'new run_id: ' + str(new_run_dict['run_id']) + '. runtime: ' + str(new_run_dict['runtime']))
            logger.debug('wavemeter reading: {reading}'.format(
                reading=str(wavemeter_reading)))
            # write to Breadboard
            time_diffs = np.array([time_diff_in_sec(
                new_run_dict['runtime'], wavemeter_time) for wavemeter_time in wavemeter_backlog])
            time_diffs[time_diffs < 0] = -np.infty
            min_idx = np.argmin(np.abs(time_diffs))
            min_time_diff = time_diffs[min_idx]
            max_time_diff_tolerance = 5  # seconds
            if np.abs(min_time_diff) < max_time_diff_tolerance:
                closest_wavemeter_time = list(
                    wavemeter_backlog.keys())[min_idx]
                wavemeter_reading_to_upload = wavemeter_backlog[closest_wavemeter_time]
                resp = bc.add_instrument_readout_to_run(
                    new_run_id, {'wavemeter_in_THz': wavemeter_reading_to_upload})
                if resp.status_code == 200:
                    logger.debug('Associated wavemeter reading {reading} from {time_str} to run_id {id}'.format(reading=str(wavemeter_reading_to_upload),
                                                                                                                time_str=str(closest_wavemeter_time), id=str(new_run_id)
                                                                                                                ))
                else:
                    logger.warning('Error uploading wavemeter reading {reading} from {time_str} to run_id {id}. Error text: '.format(reading=str(wavemeter_reading_to_upload),
                                                                                                                                     time_str=str(closest_wavemeter_time), id=str(new_run_id)
                                                                                                                                     ) + resp.text)
                old_run_id = new_run_id
            else:
                warning_message = 'Time difference between wavemeter reading and latest breadboard entry exceeds max tolerance of {tol} sec. Check breadboard-cicero-client.'.format(
                    tol=str(max_time_diff_tolerance))
                logger.debug(warning_message)
                if not warned:
                    enrico_bot.post_message(warning_message)
                    warned = True

        # Wait before checking again
        time.sleep(refresh_time)

if __name__ == '__main__':
    main()
