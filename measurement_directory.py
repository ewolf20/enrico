import os
import datetime
import shutil
import parse

MONTH_DIR_FMT = '%Y%m'


def todays_measurements(basepath=''):
    """returns list of run_folders in basepath/month/date folder. By default, 
    basepath is the cwd.
    """
    today = datetime.datetime.today()
    month = datetime.datetime.strftime(today, MONTH_DIR_FMT)
    date = datetime.datetime.strftime(today, '%y%m%d')
    month_dir = os.path.join(basepath, month)
    month_date_dir = os.path.join(month_dir, date)
    if not os.path.exists(month_dir):
        os.mkdir(month_dir)
    if not os.path.exists(month_date_dir):
        os.mkdir(month_date_dir)
        return []

    dirs = os.listdir(month_date_dir)
    run_folders = []
    for directory in dirs:
        dir_path = os.path.join(month_date_dir, directory)
        if ('run' in directory) and ('misplaced' not in directory) and os.path.isdir(dir_path):
            run_folders += [directory]
    return run_folders


def suggest_run_name(newrun_input=None, appendrun_input=None, basepath=''):
    run_folders = todays_measurements(basepath=basepath)
    runs = {}
    for directory in run_folders:
        result = parse.parse('run{}_{}', directory)
        run_idx, run_name = int(result[0]), result[1]
        runs[run_idx] = run_name
    if len(runs) == 0:
        print('first run of the day! run_idx: 0')
        measurement_name = 'run0_' + input('Enter name for run: ')
    else:
        last_run_idx = sorted(runs.keys())[-1]
        print('last run: run{idx}_{name} ...'.format(
            idx=str(last_run_idx), name=runs[last_run_idx]))
        if newrun_input is None:
            newrun_input = input('Start new run? [y/n]: ')
        if newrun_input is 'y':
            new_run_idx = last_run_idx + 1
            measurement_name = 'run{idx}_'.format(
                idx=str(new_run_idx)) + input('Enter name for run{idx}: '.format(idx=str(new_run_idx)))
        else:
            if appendrun_input is None:
                appendrun_input = input('Append to last run: run{idx}_{name}? [y/n]: '.format(
                    idx=str(last_run_idx), name=runs[last_run_idx]))
            if appendrun_input is 'y':
                measurement_name = 'run{idx}_{name}'.format(
                    idx=str(last_run_idx), name=runs[last_run_idx])
            else:
                measurement_name = suggest_run_name()
    return measurement_name


def measurement_directory(warn=False, measurement_name=None, basepath=''):
    if measurement_name is None:
        measurement_name = suggest_run_name()
    today = datetime.datetime.today()
    month = datetime.datetime.strftime(today, MONTH_DIR_FMT)
    date = datetime.datetime.strftime(today, '%y%m%d')
    month_dir = os.path.join(basepath, month)
    month_date_dir = os.path.join(month_dir, date)
    if not os.path.exists(month_dir):
        os.mkdir(month_dir)
    if not os.path.exists(month_date_dir):
        os.mkdir(month_date_dir)
    ready = False
    while not ready:
        measurement_dir = os.path.join(month_date_dir, measurement_name)
        # breakpoint()
        if not os.path.exists(measurement_dir):
            os.mkdir(measurement_dir)
            ready = True
        else:
            if warn:
                unpause = input(
                    'WARNING: measurement name already exists. Are you unpausing a previously paused measurement? [y/n] ')
                if unpause == 'y':
                    ready = True
                elif unpause == 'n':
                    measurement_name = input(
                        'Enter different name for this set of runs: ')
                else:
                    print('input not parsed')
            else:
                ready = True

    return measurement_dir


def move_misplaced_images():
    today = datetime.datetime.today()
    month = datetime.datetime.strftime(today, MONTH_DIR_FMT)
    date = datetime.datetime.strftime(today, '%y%m%d')
    time_now = datetime.datetime.strftime(today, '%H%M%S')
    misplaced_filepath = month + r'\\' + date + r'\\misplacedimages' + time_now
    shutil.move(r'images', misplaced_filepath)
    print('moved misplaced file(s) to {path}'.format(path=misplaced_filepath))
    os.mkdir(r'images')


def run_id_from_filename(filename, filename_format='{}_{}.spe'):
    result = parse.parse(filename_format, filename)
    run_id = int(result[0])
    return run_id


def run_ids_from_filenames(filenames, images_per_shot=1):
    run_ids = []
    for file in filenames:
        run_id = run_id_from_filename(file)
        if run_id not in run_ids:
            run_ids.append(run_id)
    return(run_ids)


def run_ids_from_txt(run_id_filepath):
    run_ids = []
    with open(run_id_filepath, 'r') as file:
        for line in file:
            run_ids.append(int(line.strip()))
    return(run_ids)
