'''
breadboard_python_watchdog.py
=============================
This lets you watch a folder for new single images and upload the metadata to Breadboard.
Usage:

python3 breadboard_python_watchdog.py [WATCHFOLDER]

where [WATCHFOLDER] is the folder your camera program writes images to.

'''
# import latest version of breadboard from github, rather than using the pip install.
breadboard_repo_path = r'D:\Fermidata1\enrico\breadboard-python-client\\'

import os
import time
import datetime
import shutil
import posixpath
import sys
sys.path.insert(0, breadboard_repo_path)
from breadboard import BreadboardClient
import warnings
import pandas as pd
from measurement_directory import *
import enrico_bot
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

file_handler = logging.FileHandler('image_watchdog_debugging.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# stream_handler = logging.StreamHandler()
# stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
# logger.addHandler(stream_handler)


warnings.filterwarnings(
    "ignore", "Your application has authenticated using end user credentials")
warnings.filterwarnings(
    "ignore", "Could not find appropriate MS Visual C Runtime")
bc = BreadboardClient(config_path='API_CONFIG_fermi1.json')


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
    run_id_guess = bc._send_message(
        'get', '/runs/', params={'lab': 'fermi1'}).json()['results'][0]['id']
    while True:
        run_dict = bc._send_message(
            'get', '/runs/' + str(run_id_guess) + '/', params={'lab': 'fermi1'}).json()
        if 'runtime' not in run_dict.keys():
            new_run_dict = bc._send_message(
                'get', '/runs/' + str(run_id_guess - 1) + '/').json()
            new_run_dict_clean = {'runtime': new_run_dict['runtime'],
                                  'run_id': new_run_dict['id'],
                                  **new_run_dict['parameters']}
            return new_run_dict_clean, run_id_guess - 1
        run_id_guess += 1


def check_run_image_concurrent(runtime_str, max_time_diff_in_sec=40, min_time_diff_in_sec=3):
    runtime = datetime.datetime.strptime(runtime_str, "%Y-%m-%dT%H:%M:%SZ")
    time_diff = (datetime.datetime.today() - runtime)
    if min_time_diff_in_sec < time_diff.total_seconds() < max_time_diff_in_sec:
        return True
    else:
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


def main():
    refresh_time = 1  # seconds

    """Name the set of runs"""
    print('existing runs: ')
    print(todays_measurements())
    measurement_dir = measurement_directory(warn=True)

    watchfolder = os.getcwd() + '\images'  # feed the program your watchfolder

    names_old, paths_old = getFileList(watchfolder)
    n_images_per_run = int(
        input('How many images arrive per run? (e.g. 3 for triple imaging sequence) '))
    print("\n\nWatching this folder for changes: " + watchfolder +
          ". Moving images to " + measurement_dir + "\n\n")
#     ready = False
#     while not ready:
#         save_to_BEC1_server = input('copy images to BEC1 server? [y/n] ')
#         if save_to_BEC1_server == 'y':
#             ready = True
#             print('saving to BEC1 server...')
#         elif save_to_BEC1_server == 'n':
#             ready = True
#             print('saving only a local copy...')
#         else:
#             print('input not parsed')

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
        new_row_dict, _ = get_newest_run_dict()
        if new_row_dict['run_id'] != displayed_run_id:
            # print(
            #     'new run_id: ' + str(new_row_dict['run_id']) + '. runtime: ' + str(new_row_dict['runtime']))
            # print('list bound variables: {run_dict}'.format(run_dict={key: new_row_dict[key]
            #                                                           for key in new_row_dict['ListBoundVariables']}))
            logger.debug(
                'new run_id: ' + str(new_row_dict['run_id']) + '. runtime: ' + str(new_row_dict['runtime']))
            logger.debug('list bound variables: {run_dict}'.format(run_dict={key: new_row_dict[key]
                                                                             for key in new_row_dict['ListBoundVariables']}))
            displayed_run_id = new_row_dict['run_id']

        # check if new images has come in
        if len(new_names) > 0:
            if len(new_names) < n_images_per_run:
                # waiting for all images from  newest run
                continue
            else:
                # new_row_dict, _ = get_newest_run_dict()

                if new_row_dict['run_id'] == old_run_id and old_run_id is not None:
                    get_dict_tries, max_tries = 0, 20
                    while get_dict_tries < max_tries:
                        new_row_dict, _ = get_newest_run_dict()
                        if new_row_dict['run_id'] != old_run_id:
                            break
                        else:
                            get_dict_tries += 1
                            time.sleep(0.2)
                    if new_row_dict['run_id'] == old_run_id:
                        warning_message = 'run_id did not update between shots, check on control PC if cicero breadboard logger is on.'
                        warnings.warn(warning_message)
                        # print(warning)
                        logger.warn(warning_message)
                        if not warned:  # prevent enrico_bot from spamming
                            enrico_bot.post_message(warning_message)
                            warned = True
                        move_misplaced_images()
                        continue
    #             if old_list_bound_variables is not None:
    #                 if set(new_row_dict['ListBoundVariables']) != set(old_list_bound_variables):
    #                     warnings.warning('List bound variables changed in Cicero. Check if new run should be started.')
                if not check_run_image_concurrent(new_row_dict['runtime']):
                    warning_message = 'Incoming image and latest Breadboard runtime differ by too much. Assign run_id manually later.'
                    if not warned:
                        enrico_bot.post_message(warning_message)
                        warned = True
                    warning = warnings.warn(warning_message)
                    # print(warning)
                    logger.warn(warning_message)
                    move_misplaced_images()
                    continue

                output_filenames = []
                new_names = sorted(new_names)
                image_idx = 0
                run_id = new_row_dict['run_id']
                for filename in new_names[0:n_images_per_run]:
                    # print('moving ' + filename)
                    logger.debug('moving ' + filename)
                    done_moving = False
                    while not done_moving:
                        # prevent python from corrupting file, wait for writing to disk to finish
                        filesize_changing = True
                        old_filesize = 0
                        while os.path.getsize(os.path.join(r'images\\', filename)) != old_filesize:
                            old_filesize = os.path.getsize(
                                os.path.join(r'images\\', filename))
                            time.sleep(0.2)
                        # rename images according to their associated run_id
                        old_filename = filename
                        new_filename = str(run_id) + '_' + \
                            str(image_idx) + '.spe'
                        print(new_filename)
                        new_filepath = os.path.join(
                            measurement_dir, new_filename)
                        if os.path.exists(new_filepath):
                            new_filename = rename_file(new_filename)
                            new_filepath = os.path.join(
                                measurement_dir, new_filename)
        #                     if save_to_BEC1_server:
        #                         new_filepath_BEC1server = 'foo' #TODO set BEC1 server filepath
        #                         shutil.copyfile(os.path.join(r'images\\', old_filename), new_filepath_BEC1server)
                        shutil.move(os.path.join(
                            r'images\\', old_filename), new_filepath)
                        done_moving = True
                        image_idx += 1
                        output_filenames.append(new_filename)
                    old_run_id = new_row_dict['run_id']

            # Write to Breadboard
            try:
                resp = bc.append_images_to_run(
                    new_row_dict['run_id'], output_filenames)
                bc.add_measurement_name_to_run(
                    new_row_dict['run_id'], measurement_dir)
                if resp.status_code != 200:
                    # print(resp.text)
                    logger.warn(resp.text)
            except:
                warning = warnings.warn('Failed to write to breadboard.')
                # print(warning)
                logger.warn('Failed to write to breadboard.')
                pass

            old_list_bound_variables = new_row_dict['ListBoundVariables']

        # Wait before checking again
        time.sleep(refresh_time)


# if __name__ == "__main__":
#     main()
