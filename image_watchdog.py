'''
image_watchdog.py watches the images folder and attempts to match them to a breadboard entry. On match, files are moved to MM/YYMMDD/run_idx_name/.
Otherwise, they are moved to MM/YYMMDD/run_idx_name_misplaced.

A debugging log is created in the MM/YYMMDD with info to manually associate files that failed to match.
'''
# import latest version of breadboard from github, rather than using the pip install.
import os
import time
import datetime
import shutil
import posixpath
import sys
from utility_functions import load_breadboard_client, load_bec1serverpath
import utility_functions
bc = load_breadboard_client()
import warnings
import pandas as pd
from measurement_directory import *
import enrico_bot
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

file_handler = logging.FileHandler(measurement_directory(
    measurement_name='') + 'image_watchdog_debugging.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

warnings.filterwarnings(
    "ignore", "Your application has authenticated using end user credentials")
warnings.filterwarnings(
    "ignore", "Could not find appropriate MS Visual C Runtime")


def getFileList(folder=os.getcwd()):
    # Get a list of files in a folder
    if not os.path.exists(folder):
        raise ValueError("Folder '{}' doesn't exist".format(folder))
    # Folder contents
    filenames = [filename for filename in os.listdir(folder)]
    # Output
    paths = [os.path.join(folder, f) for f in filenames]
    return (filenames, paths)


def get_newest_run_dict():
    return utility_functions.get_newest_run_dict(bc)


def check_run_image_concurrent(runtime_str, incomingfile_time, max_time_diff_in_sec=10, min_time_diff_in_sec=0):
    runtime = datetime.datetime.strptime(runtime_str, "%Y-%m-%dT%H:%M:%SZ")
    time_diff = (incomingfile_time - runtime)
    if min_time_diff_in_sec < time_diff.total_seconds() < max_time_diff_in_sec:
        return True
    else:
        print("time diff in seconds: {time_diff}".format(
            time_diff=str(time_diff.total_seconds())))
        return False


def rename_file(filename):
    # appends a timestamp to files with redudant names to avoid overwriting
    bare_name = filename[0:len(filename) - 4]
    today = datetime.datetime.today()
    time_now = datetime.datetime.strftime(today, '%H%M%S')
    extension = filename[-4:len(filename)]
    rename = '{bare_name}_{time_now}{extension}'.format(bare_name=bare_name,
                                                        time_now=time_now,
                                                        extension=extension)
    warnings.warn(filename + ' exists here already. Saving as ' + rename)
    return rename


def main(measurement_name=None, n_images_per_run=None, existing_directory_warning=False,
         backup_to_bec1server=True):

    refresh_time = 1  # seconds

    """Name the set of runs"""
    print('existing runs: ')
    print(todays_measurements())
    measurement_dir = measurement_directory(
        measurement_name=measurement_name, warn=existing_directory_warning)

    if backup_to_bec1server:
        BEC1_path = load_bec1serverpath()
        # create directories on server
        measurement_backup_path = os.path.join(BEC1_path, measurement_dir)
        dummy_path = measurement_backup_path
        dummy_paths = []
        subfolder_depth = 3  # monthdir/daydir/rundir
        for _ in range(subfolder_depth):
            dummy_paths += [dummy_path]
            dummy_path = os.path.dirname(dummy_path)
        for path in reversed(dummy_paths):
            if not os.path.exists(path):
                print('{path} does not exist.'.format(path=path))
                print('creating {path}'.format(path=path))
                os.mkdir(path)

    # feed the program your watchfolder
    watchfolder = os.path.join(os.getcwd(), 'images')

    names_old, paths_old = getFileList(watchfolder)
    if n_images_per_run is None:
        n_images_per_run = int(
            input('How many images arrive per run? (e.g. 3 for triple imaging sequence) '))
    print("\n\nWatching this folder for changes: " + watchfolder +
          ". Moving images to " + measurement_dir + "\n\n")

    names, _ = getFileList(watchfolder)
    if len(names) > 0:
        move_misplaced_images()
    old_run_id = None
    old_list_bound_variables = None
    warned = False
    displayed_run_id = None
    # Main Loop
    while True:
        # Get a list of all the images in the folder
        names, paths = getFileList(watchfolder)
        new_names = sorted(names)

        # listen to breadboard server for new run_id
        try:
            new_row_dict = get_newest_run_dict()
        except:
            logger.error(sys.exc_info()[1])
            pass

        if new_row_dict['run_id'] != displayed_run_id:
            # print(
            #     'new run_id: ' + str(new_row_dict['run_id']) + '. runtime: ' + str(new_row_dict['runtime']))
            # print('list bound variables: {run_dict}'.format(run_dict={key: new_row_dict[key]
            #                                                           for key in new_row_dict['ListBoundVariables']}))
            logger.debug('list bound variables: {run_dict}'.format(run_dict={key: new_row_dict[key]
                                                                             for key in new_row_dict['ListBoundVariables']}))
            logger.debug(
                'new run_id: ' + str(new_row_dict['run_id']) + '. runtime: ' + str(new_row_dict['runtime']))
            displayed_run_id = new_row_dict['run_id']

        # check if new images has come in
        if len(new_names) > 0:
            incomingfile_time = datetime.datetime.today()
            if len(new_names) == n_images_per_run:
                print('\n')
                # safety checks that run_id is updating and image came within 10 seconds of last Cicero upload.
                safety_check_passed = True
                if new_row_dict['run_id'] == old_run_id and old_run_id is not None:
                    get_dict_tries, max_tries = 0, 20
                    while get_dict_tries < max_tries:
                        new_row_dict = get_newest_run_dict()
                        if new_row_dict['run_id'] != old_run_id:
                            break
                        else:
                            get_dict_tries += 1
                            time.sleep(0.1)
                    if new_row_dict['run_id'] == old_run_id:
                        warning_message = 'run_id did not update from old id {id} between shots, check on control PC if cicero breadboard logger is on.'.format(
                            id=str(old_run_id))
                        warnings.warn(warning_message)
                        logger.warning(warning_message)
                        if not warned:  # prevent enrico_bot from spamming
                            enrico_bot.post_message(warning_message)
                            warned = True
                        safety_check_passed = False
                if not check_run_image_concurrent(new_row_dict['runtime'], incomingfile_time) and safety_check_passed:
                    warning_message = 'Incoming image time and latest Breadboard runtime differ by too much. Check run_id {id} manually later.'.format(
                        id=str(new_row_dict['run_id']))
                    if not warned:
                        # enrico_bot.post_message(warning_message)
                        warned = True
                    warning = warnings.warn(warning_message)
                    # print(warning)
                    logger.warning(warning_message)
                    safety_check_passed = False

                if not safety_check_passed:
                    destination = measurement_dir + '_misplaced'
                    if not os.path.exists(destination):
                        os.mkdir(destination)
                else:
                    destination = measurement_dir

                output_filenames = []
                new_names = sorted(new_names)
                image_idx = 0
                run_id = new_row_dict['run_id']
                for filename in new_names[0:n_images_per_run]:
                    # prevent python from corrupting file, wait for writing to disk to finish
                    old_filesize = 0
                    while os.path.getsize(os.path.join(r'images\\', filename)) != old_filesize:
                        old_filesize = os.path.getsize(
                            os.path.join(r'images\\', filename))
                        time.sleep(0.2)
                    # rename images according to their associated run_id
                    old_filename = filename
                    if safety_check_passed:
                        new_filename = str(run_id) + '_' + \
                            str(image_idx) + '.spe'
                    else:
                        new_filename = old_filename
                    new_filepath = os.path.join(
                        destination, new_filename)  # relative local path in enrico folder
                    if os.path.exists(new_filepath):
                        new_filename = rename_file(new_filename)
                        new_filepath = os.path.join(
                            destination, new_filename)
                    if safety_check_passed and backup_to_bec1server:
                        shutil.copyfile(os.path.join(r'images\\', old_filename),
                                        os.path.join(BEC1_path, new_filepath))
                        print('copying file to ' +
                              os.path.join(BEC1_path, new_filepath))
                    shutil.move(os.path.join(
                        r'images\\', old_filename), new_filepath)

                    logger.debug('moving {old_name} to {destination}'.format(old_name=old_filename,
                                                                             destination=new_filepath))
                    image_idx += 1
                    output_filenames.append(new_filename)

                # Write to Breadboard
                if safety_check_passed:
                    old_run_id = new_row_dict['run_id']
                    try:
                        resp = bc.append_images_to_run(
                            new_row_dict['run_id'], output_filenames)
                        bc.add_measurement_name_to_run(
                            new_row_dict['run_id'], measurement_dir)
                        if resp.status_code != 200:
                            logger.warning('Upload error: ' + resp.text)
                        else:
                            logger.debug('Uploaded filenames {files} to breadboard run_id {id}.'.format(
                                files=str(output_filenames), id=str(new_row_dict['run_id'])))
                    except:
                        warning = 'Failed to write {files} to breadboard run_id {id}.'.format(
                            files=str(output_filenames), id=str(new_row_dict['run_id']))
                        warnings.warn(warning)
                        logger.warning(warning)
                        pass

        # Wait before checking again
        time.sleep(refresh_time)


if __name__ == "__main__":
    if len(sys.argv) == 3:
        measurement_name = sys.argv[1]
        n_images_per_run = int(sys.argv[2])
    elif len(sys.argv) == 1:
        measurement_name, n_images_per_run = None, None
    else:
        raise ValueError(
            'If using command line inputs, input both measurement name and n_images_per_run. E.g. python image_watchdog.py run1_foo 3')

    try:
        main(measurement_name=measurement_name,
             n_images_per_run=n_images_per_run)
    except KeyboardInterrupt:  # often the error is not being able to complete the API request, so this may need modification
        # from log_editor import get_newest_df
        # watchfolder = measurement_directory(measurement_name=suggest_run_name(newrun_input='n', appendrun_input='y'))
        # print('exporting csv... do not close window or interrupt with Ctrl-C!\n')
        # df = get_newest_df(watchfolder)
        # df.to_csv(os.path.join(os.path.dirname(watchfolder),
        #                        os.path.basename(watchfolder) + '_params.csv'))
        # print('done. exiting')
        pass
