import os
import time
import datetime
import shutil
import sys
from utility_functions import load_breadboard_client, load_bec1serverpath
import utility_functions
bc = load_breadboard_client()
import warnings
from measurement_directory import measurement_directory, todays_measurements
import enrico_bot
import logging


class ImageWatchdog():
    """ImageWatchdog watches the images folder and attempts to match them to a breadboard entry.
    On match and after performing safety checks, files are renamed to runIdx_imageIdx.spe and moved to the MM/YYMMDD/run_idx_name/ folder. 
    Otherwise, they renamed to timestamp.spe and are moved to MM/YYMMDD/run_idx_name_misplaced."""

    def __init__(self, watchfolder=os.path.join(os.path.dirname(__file__), 'images'), new_run=True,
                 num_images_per_shot=1, refresh_time=0.3, backup_to_bec1server=True, MONTH_DIR_FMT='%Y%m',
                 max_time_diff_in_sec=5, min_time_diff_in_sec=0, max_idle_time=60 * 3, runfolder=None):
        self.MONTH_DIR_FMT = MONTH_DIR_FMT
        self.init_logger()
        self.watchfolder = watchfolder
        print("\n\nWatching this folder for changes: " + self.watchfolder)
        # clears watchfolder by moving unmatched images to a temporary storage folder
        self.clear_watchfolder()
        if runfolder is None:
            self.set_runfolder()
        else:
            self.runfolder = runfolder
        self.misplaced_folder = self.runfolder + 'misplaced'
        self.num_images_per_shot = num_images_per_shot
        self.refresh_time = refresh_time
        self.backup_to_bec1server = backup_to_bec1server
        if self.backup_to_bec1server:
            self.set_bec1serverpath()
        self.previous_update_time = datetime.datetime.now()
        self.incomingfile_time = datetime.datetime.now()
        self.newest_run_dict = {'run_id': 0}
        self.max_time_diff_in_sec = max_time_diff_in_sec
        self.min_time_diff_in_sec = min_time_diff_in_sec
        self.idle_message_sent = False
        self.max_idle_time = max_idle_time

    def init_logger(self):
        '''A debugging log is created in the MM/YYMMDD with info to manually associate files that failed to match.'''
        self.logger = logging.getLogger(__name__)
        logger = self.logger
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
        file_handler = logging.FileHandler(measurement_directory(
            measurement_name='') + 'image_watchdog_debugging.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    def getFileList(self):
        folder = self.watchfolder
        if not os.path.exists(folder):
            raise ValueError("Folder '{}' doesn't exist".format(folder))
        filenames = sorted([filename for filename in os.listdir(folder)], reverse=True)
        paths = [os.path.join(folder, f) for f in filenames]
        return (filenames, paths)

    def clear_watchfolder(self):
        filenames, _ = self.getFileList()
        if len(filenames) > 0:
            self.logger.debug(str(filenames) +
                              ' found. Clearing ' + self.watchfolder)
            today = datetime.datetime.today()
            month = datetime.datetime.strftime(today, self.MONTH_DIR_FMT)
            date = datetime.datetime.strftime(today, '%y%m%d')
            time_now = datetime.datetime.strftime(today, '%H%M%S')
            misplaced_filepath = os.path.join(os.path.join(
                month, date), 'misplacedimages' + time_now)
            shutil.move(self.watchfolder, misplaced_filepath)
            self.logger.debug('moved misplaced file(s) to {path}'.format(
                path=misplaced_filepath))
            os.mkdir(self.watchfolder)

    def set_runfolder(self):
        print('existing runs: ')
        print(todays_measurements())
        self.runfolder = measurement_directory(measurement_name=None,
                                               warn=False)
        print('Moving images to ' + self.runfolder + '.\n')

    def set_bec1serverpath(self):
        self.bec1serverpath = load_bec1serverpath()
        measurement_backup_path = os.path.join(
            self.bec1serverpath, self.runfolder)
        dummy_path = measurement_backup_path
        dummy_paths = []
        subfolder_depth = 3  # monthdir/daydir/rundir
        for _ in range(subfolder_depth):
            dummy_paths += [dummy_path]
            dummy_path = os.path.dirname(dummy_path)
        for path in reversed(dummy_paths):
            if not os.path.exists(path):
                print('creating {path} on bec1server.'.format(path=path))
                os.mkdir(path)

    def monitor_watchfolder(self):
        filenames, _ = self.getFileList()
        if len(filenames) >= self.num_images_per_shot:
            self.new_imagenames = filenames[0:self.num_images_per_shot]
            new_images_bool = True
            self.incomingfile_time = datetime.datetime.today()
            self.previous_update_time = datetime.datetime.now()
        else:
            new_images_bool = False
        return new_images_bool

    def update_run_dict(self, MAX_RETRIES=10):
        try_counter = 0
        success = False
        while try_counter < MAX_RETRIES:
            try_counter += 1
            if success:
                break
            else:
                try:
                    if try_counter > 1:
                        print('Retrying to get newest breadboard entry. Tries: {n}'.format(
                            n=str(try_counter)))
                    new_run_dict = utility_functions.get_newest_run_dict(bc)
                    new_id = new_run_dict['run_id']
                    if self.newest_run_dict['run_id'] < new_id:
                        print('new id: {id}'.format(id=str(new_id)))
                        print('list bound variables: {run_dict}'.format(run_dict={key: new_run_dict[key]
                                                                                  for key in new_run_dict['ListBoundVariables']}))
                        self.logger.debug(
                            'new run_id: ' + str(new_run_dict['run_id']) + '. runtime: ' + str(new_run_dict['runtime']))
                        self.newest_run_dict = new_run_dict
                    success = True
                except:
                    self.logger.error(sys.exc_info()[1])

    def move_images(self, safety_check_passed):
        """Renames images according to run_id or timestamp (if safety_check passes or fails) and moves 
        them to the appropriate folder. Returns a list of the renamed image filenames."""

        def rename_file(filename):
            # appends a timestamp to files with redudant names to avoid overwriting
            bare_name = filename[0:len(filename) - 4]
            today = datetime.datetime.today()
            time_now = datetime.datetime.strftime(today, '%H%M%S')
            extension = filename[-4:len(filename)]
            rename = '{bare_name}_{time_now}{extension}'.format(bare_name=bare_name,
                                                                time_now=time_now,
                                                                extension=extension)
            warnings.warn(
                filename + ' exists here already. Saving as ' + rename)
            return rename

        output_filenames = []
        image_idx = 0
        run_id = self.newest_run_dict['run_id']
        for filename in self.new_imagenames:
            # prevent python from corrupting file, wait for writing to disk to finish
            filepath = os.path.join(self.watchfolder, filename)
            old_filesize = 0
            while os.path.getsize(filepath) != old_filesize:
                old_filesize = os.path.getsize(filepath)
                time.sleep(0.2)
            # rename images according to their associated run_id
            old_filename = filename
            if safety_check_passed:
                new_filename = str(run_id) + '_' + \
                    str(image_idx) + '.spe'
                destination = self.runfolder
            else:
                new_filename = old_filename
                destination = self.misplaced_folder
            new_filepath = os.path.join(
                destination, new_filename)
            if os.path.exists(new_filepath):
                new_filename = rename_file(new_filename)
                new_filepath = os.path.join(
                    destination, new_filename)
            if safety_check_passed and self.backup_to_bec1server:
                becserver_filepath = os.path.join(
                    self.bec1serverpath, new_filepath)
                shutil.copyfile(filepath, becserver_filepath)
                print('copying file to ' + becserver_filepath)
            if not os.path.exists(os.path.dirname(new_filepath)):
                os.mkdir(os.path.dirname(new_filepath))
            shutil.move(filepath, os.path.abspath(new_filepath))
            self.logger.debug('moving {old_name} to {destination}'.format(old_name=old_filename,
                                                                          destination=new_filepath))
            image_idx += 1
            output_filenames.append(new_filename)
        return output_filenames

    def match_images_to_run_id(self, MAX_RETRIES=5):
        print('here')
        def check_run_image_concurrent(self):
            max_time_diff_in_sec = self.max_time_diff_in_sec
            min_time_diff_in_sec = self.min_time_diff_in_sec
            runtime_str = self.newest_run_dict['runtime']
            incomingfile_time = self.incomingfile_time
            runtime = datetime.datetime.strptime(
                runtime_str, "%Y-%m-%dT%H:%M:%SZ")
            time_diff = (incomingfile_time - runtime)
            self.logger.debug("time diff in seconds: {time_diff}".format(
                time_diff=str(time_diff.total_seconds())))
            if min_time_diff_in_sec < time_diff.total_seconds() < max_time_diff_in_sec:
                return True
            else:
                self.update_run_dict()
                return False

        try_counter = 0
        safety_check_passed = False
        while try_counter < MAX_RETRIES and (not safety_check_passed):
            try:
                safety_check_passed = check_run_image_concurrent(self)
                try_counter += 1
                time.sleep(1)
            except:
                pass
        output_filenames = self.move_images(safety_check_passed)
        if not safety_check_passed:
            warning_message = 'Incoming image time and latest Breadboard runtime differ by too much. Check run_id {id} manually later.'.format(
                id=str(self.newest_run_dict['run_id']))
            warning = warnings.warn(warning_message)
            self.logger.warning(warning_message)
            matched_to_run_id = False
        else:
            # write to breadboard
            run_id = self.newest_run_dict['run_id']
            try:
                resp = bc.append_images_to_run(run_id, output_filenames)
                bc.add_measurement_name_to_run(run_id, self.runfolder)
                if resp.status_code != 200:
                    self.logger.warning('Upload error: ' + resp.text)
                else:
                    self.logger.debug('Uploaded filenames {files} to breadboard run_id {id}.'.format(
                        files=str(output_filenames), id=str(run_id)))
            except:
                warning = 'Failed to write {files} to breadboard run_id {id}.'.format(
                    files=str(output_filenames), id=str(run_id))
                warnings.warn(warning)
                logger.warning(warning)
            matched_to_run_id = True
        return matched_to_run_id

    def check_idle_time(self):
        idle_time = (datetime.datetime.now() -
                     self.incomingfile_time).total_seconds()
        if idle_time > self.max_idle_time and not self.idle_message_sent:
            idle_message = 'Measurement {id} idle, no new images for {min}min.'.format(id=self.runfolder,
                                                                                       min=str(int(idle_time / 60)))
            enrico_bot.post_message(idle_message)
            print(idle_message)
            self.idle_message_sent = True
        elif idle_time < self.max_idle_time and self.idle_message_sent:
            self.idle_message_sent = False  # reset message status if image taking is resumed

    def main(self):
        while True:
            try:
                self.update_run_dict()  # fetch newest run info from breadboard
                self.check_idle_time()  # fire Slack message if experiment is idling
                new_images_bool = self.monitor_watchfolder()
                if new_images_bool:
                    self.match_images_to_run_id()  # this method contains all the safety checks and logic
                    # for matching run_id to images and writing image and run names to breadboard.
                time.sleep(self.refresh_time)
            except KeyboardInterrupt:
                break


if __name__ == "__main__":
    watchdog = ImageWatchdog()
    watchdog.main()
