from collections import OrderedDict
import datetime
import os
import sys
main_path = os.path.abspath(os.path.join(__file__, '../..'))
sys.path.insert(0, main_path)
from utility_functions import load_breadboard_client, get_newest_run_dict
import enrico_bot
# TODO: logging errors


class StatusMonitor:
    def __init__(self, backlog_max, value_name=None, warning_interval_in_min=10, read_run_time_offset=3, max_time_diff_tolerance=5):
        self.bc = load_breadboard_client()
        self.backlog_max = backlog_max
        self.backlog = OrderedDict()
        if value_name is None:
            self.value_name = input(
                'Enter label for logged values in format [VALNAME]_in_[UNITNAME], e.g. wavemeter_in_THz: ')
        else:
            self.value_name = value_name
        self.last_warning = None
        self.warning_interval_in_min = warning_interval_in_min
        self.read_run_time_offset = read_run_time_offset
        # seconds, to avoid off-by-one run_id uploads to breadboard
        self.max_time_diff_tolerance = max_time_diff_tolerance

    def append_to_backlog(self, value):
        if len(self.backlog) > self.backlog_max:
            self.backlog.popitem(last=False)

        time_now = datetime.datetime.today()
        self.backlog[time_now] = value
        print('Logged {value} for {value_name} at {time_now}'.format(value=str(value),
                                                                     value_name=self.value_name,
                                                                     time_now=str(time_now)))

    def warn_on_slack(self, warning_message):
        print(warning_message)
        now = datetime.datetime.now()
        if (self.last_warning is None or
                (now - self.last_warning).seconds / 60 < self.warning_interval_in_min):
            enrico_bot.post_message(warning_message)
            self.last_warning = now
        else:
            print('Posted to slack {min} min ago, silenced for now.'.format(
                min=str((now - self.last_warning).seconds / 60)))

    def upload_to_breadboard(self):
        run_dict = get_newest_run_dict(self.bc)
        if value_name not in run_dict:
            print("Newest breadboard run_id {id} at time: ".format(id=str(run_dict['run_id']))
                  + str(run_dict['runtime']))
            time_diffs = np.array([time_diff_in_sec(
                run_dict['runtime'], backlog_time) for backlog_time in self.backlog])
            time_diffs[time_diffs < self.read_run_time_offset] = -np.infty
            min_idx = np.argmin(np.abs(time_diffs - self.read_run_time_offset))
            min_time_diff_from_ideal = (time_diffs[min_idx] -
                                        self.read_run_time_offset)
            if np.abs(min_time_diff_from_ideal) < self.max_time_diff_tolerance:
                closest_backlog_time = list(
                    self.backlog.keys())[min_idx]
                value_to_upload = self.backlog[closest_backlog_time]
                resp = bc.add_instrument_readout_to_run(
                    new_run_id, {self.value_name: value_to_upload})
                if resp.status_code != 200:
                    warning_text = ('Error uploading {value} reading {reading} from {time_str} to run_id {id}. Error text: '.format(value=self.value_name,
                                                                                                                                    reading=str(
                                                                                                                                        value_to_upload),
                                                                                                                                    time_str=str(closest_backlog_time), id=str(new_run_id)
                                                                                                                                    ) + resp.text)
                    self.warn_on_slack(warning_text)
            else:
                warning_text = 'Time difference between {value} reading and latest breadboard entry exceeds max tolerance of {tol} sec. Check breadboard-cicero-client.'.format(
                    tol=str(self.max_time_diff_tolerance), value=self.value_name)
                self.warn_on_slack(warning_text)
