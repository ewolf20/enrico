import os
import time
import datetime
import shutil
import warnings
import enrico_bot
from math import isnan
import sys
from measurement_directory import run_ids_from_filenames


class AnalysisLogger():
    """AnalysisLogger watches an ImageWatchdog runfolder and passes new (sets of) images to one of
    Carsten's MATLAB analysis functions, which return an analysis dictionary and a analysis settings dictionary.
    On successful return, the analysis dictionary is cleaned and uploaded to the appropriate
    breadboard run_id."""

    def __init__(self, analysis_mode=None, watchfolder=None, load_matlab=True,
                 save_images=True, refresh_time=0.2, save_previous_settings=True,
                 append_mode=True):
        """
        Args:
            - analysis_mode: determines which MATLAB function to perform analysis with.
            - watchfolder: new images in folder are added to the analysis stack.
            - load_matlab: can be disabled if debugging software issues, as MATLAB can take a while to load.
            - save_images: if set to False, images are discarded after analysis.
            - save_previous_settings: set to False if analysis settings, e.g. normBox, needs to be reset on each shot
            - append_mode: set to True to check breadboard for existing analysis before analyzing
        """

        # ycam, zcam double imaging, zcam triple imaging, and default images_per_shot
        if analysis_mode is None:
            analysis_shorthand = {'zt': 'zcam_triple_imaging',
                                  'zd': 'zcam_dual_imaging',
                                  'y': 'ycam'}
            print('analysis keys:')
            print(analysis_shorthand)
            analysis_mode = input(
                'Select analysis (e.g. zd for zcam_dual_imaging): ')
        analysis_modes = {'y': 1, 'zd': 1, 'zt': 3, 'testing': 1}
        if analysis_mode in analysis_modes.keys():
            self.analysis_mode = analysis_mode
            self.images_per_shot = analysis_modes[analysis_mode]
        else:
            raise ValueError(str(
                analysis_mode) + ' is not an allowed analysis mode, i.e. ' + str(analysis_modes))
        if watchfolder is None:
            self.watchfolder = self.suggest_watchfolder()
        else:
            self.watchfolder = watchfolder
        print("\n\n Watching this folder for changes: " +
              self.watchfolder + "\n\n")
        self.init_logger()
        if load_matlab:
            self.load_matlab_engine()
        self.load_matlab_wrapper()
        self.load_breadboard_client()
        if save_images is None:
            save_images_input = input('Keep images after analysis? [y/n]: '
                                      )
            if not save_images_input in ['y', 'n']:
                return ValueError('Input could not be parsed.')
            if save_images_input == 'n':
                print('entering testing mode...')
                save_images = False
        self.save_images = save_images  # TODO delete images from BECserver
        self.refresh_time = refresh_time
        self.previous_settings = None
        self.unanalyzed_ids = []
        self.done_ids = []
        self.append_mode = append_mode #check breadboard if analysis has already been done on image, e.g. if analysis is restarted
        self.save_previous_settings = save_previous_settings
        

    def init_logger(self):
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
        file_handler = logging.FileHandler('analysis_debugging.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        self.logger = logger

    def create_dailynb(self):
        """
        Copying of a clean jupyter notebook template to today's YYMMDD folder.
        """
        clean_notebook_path = os.path.join(os.path.dirname(
            __file__), 'log viewer and plotterDUPLICATEANDUSETODAY.ipynb')
        if analysis_key == 'y':
            clean_notebook_path = r'C:\Users\FermiCam2\Desktop\GitHub\enrico\log viewer and plotterDUPLICATEANDUSETODAY.ipynb'
        nb_path = os.path.join(os.path.dirname(watchfolder), 'dailynb.ipynb')

        if not os.path.exists(nb_path) and self.notebook_flag:
            shutil.copy(clean_notebook_path, nb_path)
            print('no daily notebook, made a duplicate from {path} now.'.format(
                path=clean_notebook_path))

    def load_breadboard_client(self):
        from utility_functions import load_breadboard_client
        self.bc = load_breadboard_client()

    def suggest_watchfolder(self):
        """
        Returns the newest runfolder in today's YYMMDD folder.
        """

        from utility_functions import load_analysis_path
        from measurement_directory import todays_measurements, measurement_directory, suggest_run_name
        try:
            analysis_paths = load_analysis_path()
            data_basepath = analysis_paths['data_basepath']
            self.notebook_flag = (
                analysis_paths['create_notebook_flag'] == 'True')
        except FileNotFoundError:
            data_basepath = ''
            print('analysis_config.json not found, using default settings.')
            self.notebook_flag = True
        print('existing runs: ')
        measurement_names = todays_measurements(basepath=data_basepath)
        if len(measurement_names) == 0:
            raise ValueError('No measurements yet today.')
        for name in sorted(measurement_names):
            if 'run' in name:
                if 'misplaced' not in name and '.csv' not in name:
                    print(name)
                    last_output = name
        watchfolder = measurement_directory(
            measurement_name=suggest_run_name(
                newrun_input='n', appendrun_input='y', basepath=data_basepath),
            basepath=data_basepath)
        watchfolder = os.path.abspath(watchfolder)
        return watchfolder

    def load_matlab_engine(self):
        import matlab_wrapper
        self.eng = matlab_wrapper.load_matlab_engine()

    def load_matlab_wrapper(self):
        """
        Generically maps one of Carsten's MATLAB analysis functions to self.analysis_function, based on self.analysis_mode.
        Also sets self.analyzed_var_names, keys to scalar values in analysis_dict which can be JSON serialized and uploaded to breadboard.
        """

        # key, val pairs of analysis_mode string and tuple (matlab wrapper function, analyzed variable names)
        import matlab_wrapper
        analysis_modes_dict = {
            'y': ('getYcamAnalysis', 'ycam_analyzed_var_names'),
            'zd': ('getDualImagingAnalysis', 'dual_imaging_analyzed_var_names'),
            'zt': ('getTripleImagingAnalysis', 'triple_imaging_analyzed_var_names')}
        self.matlab_func_name, self.analyzed_var_names = (getattr(
            matlab_wrapper, name) for name in analysis_modes_dict[self.analysis_mode])

        def analysis_function(filepath, previous_settings=None):
            """A generic placeholder for one of Carsten's MATLAB analysis functions.
            By passing in previous_settings, one can avoid resetting manually inputted settings, e.g. normBox.

            Returns a MATLAB analysis struct mapped to a Python dict, analysis_dict, and a settings dict compatible with the MATLAB wrapper functions.
            """
            if previous_settings is None:
                matlab_dict = self.matlab_func_name(self.eng, filepath)
            else:
                matlab_dict = self.matlab_func_name(self.eng, filepath, marqueeBox=previous_settings['marqueeBox'],
                                               normBox=previous_settings['normBox'])
            analysis_dict, settings = matlab_dict['analysis'], matlab_dict['settings']
            if not self.save_previous_settings:
                settings = None
            return analysis_dict, settings

        self.analysis_function = analysis_function

    def monitor_watchfolder(self):
        """
        Adds new images to the stack of unanalyzed_ids.
        """
        watchfolder = self.watchfolder
        if not os.path.exists(watchfolder):
            pass
        else:
            files = [filename for filename in os.listdir(watchfolder)]
            filesSPE = []
            for file in files:  # filter out non .spe files
                if '.spe' in file:
                    filesSPE.append(file)
            files = filesSPE
            run_ids = run_ids_from_filenames(files)
            fresh_ids = sorted(list(set(run_ids).difference(
                set(self.done_ids)).difference(set(self.unanalyzed_ids))))
            self.unanalyzed_ids += fresh_ids
        pass

    def analyze_newest_images(self):
        """
        Analyzes the newest run_id on the stack of unanalyzed_ids and uploads to breadboard. 
        Deletes images locally after analysis if self.save_images is False.
        """

        def analyze_image(filepath):
            """Helper function for cleaning analysis_dict to JSON serializable types
            before uploading to breadboard.
            """
            self.logger.debug('{file} analyzing: '.format(file=filepath))
            analysis_dict, settings = self.analysis_function(
                filepath, self.previous_settings)
            cleaned_analysis_dict = {}
            print('\n')
            for key in self.analyzed_var_names:
                if not isnan(analysis_dict[key]):
                    cleaned_analysis_dict[key] = analysis_dict[key]
                    print(key, analysis_dict[key])
            print('\n')
            return cleaned_analysis_dict, settings

        bc, watchfolder = self.bc, self.watchfolder
        run_id = self.unanalyzed_ids[-1]  # start from top of stack
        if self.images_per_shot == 1:
            file = os.path.join(watchfolder,
                                '{run_id}_0.spe'.format(run_id=run_id))
        else:  # for triple imaging
            file = [os.path.join(watchfolder, '{run_id}_{idx}.spe'.format(
                run_id=run_id, idx=idx)) for idx in range(images_per_shot)]
        if self.append_mode:
            run_dict = bc._send_message(
                'get', '/runs/' + str(run_id) + '/').json()
            if set(self.analyzed_var_names).issubset(set(run_dict['parameters'].keys())):
                popped_id = [self.unanalyzed_ids.pop()]
                self.done_ids += popped_id
                return None
        try:
            analysis_dict, self.previous_settings = analyze_image(
                file)
            resp = bc.append_analysis_to_run(run_id, analysis_dict)
        except:  # if MATLAB analysis fails
            analysis_dict = {'badshot': True}
            warning_message = str(
                run_id) + 'could not be analyzed. Marking as bad shot.'
            resp = bc.append_analysis_to_run(run_id, analysis_dict)
            warnings.warn(warning_message)
            self.logger.warn(warning_message)
        popped_id = [self.unanalyzed_ids.pop()]
        self.done_ids += popped_id

        if resp.status_code != 200:
            logger.warning('Upload error: ' + resp.text)

        if not self.save_images:  # delete images and add run_ids to .txt file after analysis if in testing mode
            if isinstance(file, str):
                filepath = os.path.join(self.watchfolder, file)
                os.remove(filepath)
                self.logger.debug(
                    'save_images is False, file {file} deleted after analysis.'.format(file=filepath))
            elif isinstance(file, list):
                for f in file:
                    filepath = os.path.join(self.watchfolder, f)
                    os.remove(filepath)
                    logger.debug(
                        'save_images is False, file {file} deleted after analysis.'.format(file=filepath))
            with open(os.path.join(self.watchfolder, 'run_ids.txt'), 'a') as run_ids_file:
                run_ids_file.write(str(popped_id[0]) + '\n')
                self.logger.debug('Run_id {id} added to {file}.'.format(
                    id=str(popped_id[0]), file=os.path.join(watchfolder, 'run_ids.txt')))
        print('\n')

    def main(self):
        while True:
            self.monitor_watchfolder()
            if len(self.unanalyzed_ids) > 0:
                self.analyze_newest_images()
            time.sleep(self.refresh_time)

    def export_params_csv(self):
        """
        Exports a csv file containing run_ids and Cicero list-bound variables and preliminary analysis to the BEC1server and the local MMYYDD folder.
        """
        from utility_functions import get_newest_df, load_bec1serverpath
        watchfolder = self.watchfolder
        bec1server_path = load_bec1serverpath()
        print('exporting csv... do not close window or interrupt with Ctrl-C!\n')
        df = get_newest_df(watchfolder)
        df.to_csv(os.path.join(watchfolder,
                               os.path.basename(watchfolder) + '_params.csv'))
        server_exportpath = os.path.join(os.path.join(bec1server_path, watchfolder),
                                         os.path.basename(watchfolder) + '_params.csv')
        df.to_csv(server_exportpath)
        print('done. exiting')

    def crash_messsage(self):
        warning_message = '{folder} analysis crashed: '.format(folder=watchfolder) + 'Error: {}. {}, line: {}'.format(sys.exc_info()[0],
                                                                                                                      sys.exc_info()[
            1],
            sys.exc_info()[2].tb_lineno)
        # enrico_bot.post_message(warning_message)
        print(warning_message)


if __name__ == '__main__':
    analysis_logger = AnalysisLogger()
    try:
        analysis_logger.main()
    except KeyboardInterrupt:
        analysis_logger.export_params_csv()
