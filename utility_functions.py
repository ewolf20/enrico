import json
import time
from json import JSONDecodeError


def fancy_plot(x, y, fmt='', **kwargs):
    """Wraps around matplotlib.pyplot (aliased to plt) with last-point highlighting and statistics

    Plots x and y as in plt.plot, but a) averages together y-values with the same x-value and calculates and plots 
    an error bar, and b) plots the final (x,y) point in a different color than the previous ones. 

    Args:
        x: The x-data to be plotted. Assumed to be an iterable with contents of
            numeric type, including possibly np.nan
        y: The y-data to be plotted. Same assumptions on type.
        fmt: The format string. In contrast to plt.plot, it is a kwarg.
        kwargs: Any kwarg that can be passed to plt.errorbar.

    Returns:
        ErrorbarContainer, as detailed in the docs for plt.errorbar

    Raises:
        ValueError if x and y are not of the same length
    """

    import numpy as np
    import matplotlib.pyplot as plt
    if(len(x) != len(y)):
        raise ValueError(
            "The input x and y arrays must be of the same length.")
    # Filter out the NaNs in either x or y while preserving order
    zipped_list = list(zip(x, y))
    nan_filter = filter(lambda v: (
        (not np.isnan(v[0])) and (not np.isnan(v[1]))), zipped_list)
    nan_stripped_list = list(nan_filter)
    # Pull off the last point so that it can be plotted in a different color
    if(len(nan_stripped_list) != 0):
        most_recent_xy_pair = nan_stripped_list[-1]
        nan_stripped_list = nan_stripped_list[:len(nan_stripped_list) - 1]
    else:
        most_recent_xy_pair = None
    # Sort the NaN-stripped list to make getting statistics faster for large data
    sorted_list = sorted(nan_stripped_list, key=(lambda v: v[0]))
    # Reconstitute to x- and y- lists
    if(len(sorted_list) > 0):
        x_sorted, y_sorted = zip(*sorted_list)
        sorted_x_list = list(x_sorted)
        sorted_y_list = list(y_sorted)
    else:
        sorted_x_list = []
        sorted_y_list = []
    # Perform statistics and condense repeated measurements
    index = 0
    final_x_list = []
    final_y_list = []
    final_error_list = []
    while(index < len(sorted_x_list)):
        current_x_value = sorted_x_list[index]
        final_x_list.append(current_x_value)
        y_list_for_current_x = []
        while(index < len(sorted_x_list) and sorted_x_list[index] == current_x_value):
            y_list_for_current_x.append(sorted_y_list[index])
            index += 1
        y_array_for_current_x = np.array(y_list_for_current_x)
        y_mean = sum(y_array_for_current_x) / float(len(y_array_for_current_x))
        final_y_list.append(y_mean)
        # Calculate the standard error of mean if possible
        if(len(y_list_for_current_x) == 1):
            final_error_list.append(np.nan)
        else:
            variance_estimate = sum(np.square(
                y_mean - y_array_for_current_x)) / float(len(y_array_for_current_x) - 1)
            standard_error_of_mean = np.sqrt(
                variance_estimate / len(y_array_for_current_x))
            final_error_list.append(standard_error_of_mean)
    # Convert all lists to np arrays
    final_x_values = np.array(final_x_list)
    final_y_values = np.array(final_y_list)
    final_error_values = np.array(final_error_list)
    # Plot the most recent point with a hardcoded but distinctive black diamond symbol
    if(most_recent_xy_pair != None):
        plt.plot(most_recent_xy_pair[0], most_recent_xy_pair[1], 'dr')
    # Plot and return the errorbar graph with the input kwargs
    return plt.errorbar(final_x_values, final_y_values, final_error_values, fmt=fmt, **kwargs)


def load_breadboard_client():
    """Wraps the breadboard import process

    Uses a system-specific .json config file, stored in the working directory, to import breadboard
    without hard-coded paths.

    Returns:
        BreadboardClient object; see breadboard documentation

    Raises:
        FileNotFoundError if no .json file exists
        KeyError if a .json file exists but does not contain the right keys
        ValueError if the breadboard_repo_path variable in the .json does not lead to a breadboard install
    """

    import json
    import sys
    import os
    with open(os.path.join(os.path.dirname(__file__), "breadboard_path_config.json")) as my_file:
        breadboard_dict = json.load(my_file)
        breadboard_repo_path = breadboard_dict.get("breadboard_repo_path")
        if(breadboard_repo_path is None):
            raise KeyError(
                "The .json config does not contain variable breadboard_repo_path")
        breadboard_API_config_path = breadboard_dict.get(
            "breadboard_API_config_path")
        if(breadboard_API_config_path is None):
            raise KeyError(
                "The .json config does not contain variable breadboard_API_config_path")
        sys.path.insert(0, breadboard_repo_path)
        try:
            from breadboard import BreadboardClient
        except ModuleNotFoundError:
            raise ValueError(
                "Unable to import breadboard using specified value of breadboard_repo_path")
        bc = BreadboardClient(breadboard_API_config_path)
    return bc


def get_newest_run_dict(bc, max_retries=10):
    """Gets newest run dictionary containing runtime, run_id, and parameters via breadboard client bc
    """
    retries = 0
    while retries < max_retries:
        try:
            resp = bc._send_message(
                'get', '/runs/', params={'lab': 'fermi1', 'limit': 1})
            if resp.status_code != 200:
                retries += 1
                time.sleep(0.3)
                continue
            new_run_dict = resp.json()['results'][0]
            break
        except JSONDecodeError:
            time.sleep(0.3)
            retries += 1

    new_run_dict_clean = {'runtime': new_run_dict['runtime'],
                          'run_id': new_run_dict['id'],
                          **new_run_dict['parameters']}
    return new_run_dict_clean


def time_diff_in_sec(runtime_str, trigger_time):
    """Returns time difference in seconds between trigger time and runtime.
    Args:
        runtime_str: The string value from run_dict['runtime'], e.g. from get_newest_run_dict.
        trigger_time: a datetime object.
    """
    import datetime
    runtime = datetime.datetime.strptime(runtime_str, "%Y-%m-%dT%H:%M:%SZ")
    time_diff = (runtime - trigger_time)
    return time_diff.total_seconds()


def load_bec1serverpath():
    import json
    import os
    with open(os.path.join(os.path.dirname(__file__), "bec1server_config.json")) as my_file:
        breadboard_dict = json.load(my_file)
        bec1_server_path = breadboard_dict.get("BEC1server_path")
    return bec1_server_path
