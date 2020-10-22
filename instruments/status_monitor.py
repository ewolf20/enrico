from collections import OrderedDict
import datetime
import os
import sys
main_path = os.path.abspath(os.path.join(__file__, '../..'))
sys.path.insert(0, main_path)
from utility_functions import load_breadboard_client, get_newest_run_dict, time_diff_in_sec
import enrico_bot
import numpy as np
# TODO: logging errors


class StatusMonitor:
    def __init__(self, backlog_max=30, warning_interval_in_min=10, read_run_time_offset=3, max_time_diff_tolerance=15):
        self.bc = load_breadboard_client()
        self.backlog_max = backlog_max
        self.backlog = OrderedDict()
        self.last_warning = None
        self.warning_interval_in_min = warning_interval_in_min
        self.read_run_time_offset = read_run_time_offset
        # seconds, to avoid off-by-one run_id uploads to breadboard
        self.max_time_diff_tolerance = max_time_diff_tolerance

    def append_to_backlog(self, values_dict, time_now=None):
        for value_name in values_dict:
            if '_in_' not in value_name:
                raise ValueError(
                    '{name} not in format VALNAME_in_UNITNAME'.format(name=value_name))

        if len(self.backlog) > self.backlog_max:
            self.backlog.popitem(last=False)
        if time_now is None:
            time_now = datetime.datetime.today()
        self.backlog[time_now] = values_dict
        print('Logged {value} at {time_now}'.format(value=str(values_dict),
                                                    time_now=str(time_now)))

    def warn_on_slack(self, warning_message):
        print(warning_message)
        now = datetime.datetime.now()
        if (self.last_warning is None or
                (now - self.last_warning).seconds / 60 > self.warning_interval_in_min):
            enrico_bot.post_message(warning_message)
            self.last_warning = now
        else:
            print('Posted to slack {min} min ago, silenced for now.'.format(
                min=str((now - self.last_warning).seconds / 60)))

    def upload_to_breadboard(self):
        # matches backlog times to run_id times and writes (but not overwrites) closest log entry to breadboard
        try:
            run_dict = get_newest_run_dict(self.bc)
        except:
            pass
        new_run_id = run_dict['run_id']
        time_diffs = np.array([time_diff_in_sec(
            run_dict['runtime'], backlog_time) for backlog_time in self.backlog])
        time_diffs[time_diffs < self.read_run_time_offset] = -np.infty
        min_idx = np.argmin(np.abs(time_diffs - self.read_run_time_offset))
        min_time_diff_from_ideal = (time_diffs[min_idx] -
                                    self.read_run_time_offset)
        if np.abs(min_time_diff_from_ideal) < self.max_time_diff_tolerance:
            print("Newest breadboard run_id {id} at time: ".format(id=str(run_dict['run_id']))
                  + str(run_dict['runtime']))
            closest_backlog_time = list(
                self.backlog.keys())[min_idx]
            dict_to_upload = self.backlog[closest_backlog_time]
            readout_exists_on_breadboard = False
            for value_name in dict_to_upload.keys():
                if value_name in run_dict:
                    readout_exists_on_breadboard = True
                    # print('{name} already exists for run_id {id} on breadboard.'.format(name=value_name,id=run_dict['run_id']))
            if not readout_exists_on_breadboard:
                resp = self.bc.add_instrument_readout_to_run(
                    new_run_id, dict_to_upload)
                if resp.status_code != 200:
                    warning_text = ('Error uploading {dict_to_upload} from {time_str} to run_id {id}. Error text: '.format(dict_to_upload=str(dict_to_upload),
                                                                                                                           reading=str(
                                                                                                                               value_to_upload),
                                                                                                                           time_str=str(
                                                                                                                               closest_backlog_time),
                                                                                                                           id=str(
                                                                                                                               new_run_id)
                                                                                                                           ) + resp.text)
                    self.warn_on_slack(warning_text)
        else:
            warning_text = 'Time difference {diff} sec between reading and latest breadboard entry exceeds max tolerance of {tol} sec. Check breadboard-cicero-client.'.format(
                diff=str(np.abs(min_time_diff_from_ideal)), tol=str(self.max_time_diff_tolerance))
            if np.abs(min_time_diff_from_ideal) != np.inf:
                self.warn_on_slack(warning_text)
