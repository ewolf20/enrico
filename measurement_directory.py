import os
import datetime
import shutil
import parse

MONTH_DIR_FMT = '%Y%m'

def measurement_directory(warn=False, measurement_name=None):
    # name the run test if you want test files to be cleaned up later
    if measurement_name is None:
        measurement_idx = input('Enter run index: ')
        measurement_name = 'run' + measurement_idx + '_' + \
            input('Enter name for run: ')
    today = datetime.datetime.today()
    month = datetime.datetime.strftime(today, MONTH_DIR_FMT)
    date = datetime.datetime.strftime(today, '%y%m%d')
    if not os.path.exists(month):
        os.mkdir(month)
    if not os.path.exists(r'{month}\{date}'.format(month=month, date=date)):
        os.mkdir(r'{month}\{date}'.format(month=month, date=date))
    ready = False
    while not ready:
        measurement_dir = r'{month}\{date}\{measurement_name}'.format(
            month=month, date=date, measurement_name=measurement_name)
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


def todays_measurements():
    # name the run test if you want test files to be cleaned up later
    today = datetime.datetime.today()
    month = datetime.datetime.strftime(today, MONTH_DIR_FMT)
    date = datetime.datetime.strftime(today, '%y%m%d')
    if not os.path.exists(r'{month}\{date}'.format(month=month, date=date)):
        os.mkdir(r'{month}\{date}'.format(month=month, date=date))
        ValueError('No datasets saved today.')
    month_date_dir = r'{month}\{date}\\'.format(
        month=month, date=date)
    return os.listdir(month_date_dir)


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
