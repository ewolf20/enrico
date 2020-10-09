from measurement_directory import *
import sys
from utility_functions import load_breadboard_client
bc = load_breadboard_client()
import os
import time
import datetime
import shutil
import warnings
# import enrico_bot
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

file_handler = logging.FileHandler('analysis_debugging.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# stream_handler = logging.StreamHandler()
# stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)


# loading takes a while, don't run this if testing
def load_matlab_engine():
    print('loading matlab engine...')
    import matlab.engine
    eng = matlab.engine.start_matlab()
    print('matlab engine loaded')
    return eng


warnings.filterwarnings(
    "ignore", "Your application has authenticated using end user credentials")
warnings.filterwarnings(
    "ignore", "Could not find appropriate MS Visual C Runtime")


def main(analysis_type, watchfolder, load_matlab=True, images_per_shot=1, save_images=True):
    refresh_time = 1  # seconds
    print("\n\n Watching this folder for changes: " + watchfolder + "\n\n")

    # loading matlab takes a while, disable if testing
    if load_matlab:
        eng = load_matlab_engine()

    # define subfunction analysis_function which outputs analysis and settings dictionaries
    # define analyzed_var_names list manually, these are the scalar values most easily parsed from Carsten's analysis MATLAB structs.
    # TODO: parse all of Carsten's MATLAB struct, not just scalar values.
    if analysis_type == 'fake analysis':
        from matlab_wrapper import fake_analysis1_var_names as analyzed_var_names
        from matlab_wrapper import fake_analysis1 as analysis_function
    elif analysis_type == 'fake analysis 2':
        from matlab_wrapper import fake_analysis2_var_names as analyzed_var_names
        from matlab_wrapper import fake_analysis2 as analysis_function
    elif analysis_type == 'ycam':
        from matlab_wrapper import getYcamAnalysis
        from matlab_wrapper import ycam_analyzed_var_names as analyzed_var_names

        def analysis_function(filepath, previous_settings=None):
            if previous_settings is None:
                matlab_dict = getYcamAnalysis(eng, filepath)
            else:
                matlab_dict = getYcamAnalysis(eng, filepath, marqueeBox=previous_settings['marqueeBox'],
                                              normBox=previous_settings['normBox'])
            analysis_dict, settings = matlab_dict['analysis'], matlab_dict['settings']
            return analysis_dict, settings
    elif analysis_type == 'zcam_dual_imaging':
        from matlab_wrapper import getDualImagingAnalysis
        from matlab_wrapper import dual_imaging_analyzed_var_names as analyzed_var_names

        def analysis_function(filepath, previous_settings=None):
            if previous_settings is None:
                matlab_dict = getDualImagingAnalysis(eng, filepath)
    #         else:
    #             matlab_dict = getMATLABanalysis(eng, filepath, marqueeBox = previous_settings['marqueeBox'],
    #                                            normBox = previous_settings['normBox'])
            analysis_dict = matlab_dict['analysis']
            settings = None
            return analysis_dict, settings
    elif analysis_type == 'zcam_triple_imaging':
        images_per_shot = 3
        from matlab_wrapper import getTripleImagingAnalysis
        from matlab_wrapper import triple_imaging_analyzed_var_names as analyzed_var_names

        def analysis_function(filepath, previous_settings=None):
            if previous_settings is None:
                matlab_dict = getTripleImagingAnalysis(eng, filepath)
    #         else:
    #             matlab_dict = getMATLABanalysis(eng, filepath, marqueeBox = previous_settings['marqueeBox'],
    #                                            normBox = previous_settings['normBox'])
            analysis_dict = matlab_dict['analysis']
            settings = None
            return analysis_dict, settings

    # wrap analysis_function
    def analyze_image(image_filename, previous_settings=None, output_previous_settings=True):
        if isinstance(image_filename, str):
            abs_image_path = os.path.join(
                os.path.abspath(watchfolder), image_filename)
        elif isinstance(image_filename, list):
            abs_image_path = [os.path.join(os.path.abspath(
                watchfolder), filename) for filename in image_filename]
        print(abs_image_path)
        logger.debug('{file} analyzing: '.format(file=image_filename))
        analysis_dict, settings = analysis_function(
            abs_image_path, previous_settings)
        if not output_previous_settings:
            settings = None  # forces user to select new marquee box for each shot
        cleaned_analysis_dict = {}
        print('\n')
        for key in analyzed_var_names:
            cleaned_analysis_dict[key] = analysis_dict[key]
            print(key, analysis_dict[key])
#             logger.debug(key, analysis_dict[key])
        print('\n')
        return cleaned_analysis_dict, settings

    previous_settings = None
    unanalyzed_files = []
    done_files = []
    unanalyzed_ids = []
    done_ids = []
    append_mode = True

    # Main Loop
    while True:
        if not os.path.exists(watchfolder):
            time.sleep(refresh_time)
            continue
        else:
            files = [filename for filename in os.listdir(watchfolder)]
            filesSPE = []
            for file in files:  # filter out non .spe files
                if '.spe' in file:
                    filesSPE.append(file)
            files = filesSPE
            run_ids = run_ids_from_filenames(files)
            fresh_ids = sorted(list(set(run_ids).difference(
                set(done_ids)).difference(set(unanalyzed_ids))))
            unanalyzed_ids += fresh_ids

            for run_id in reversed(unanalyzed_ids):  # start from top of stack
                if images_per_shot == 1:
                    file = '{run_id}_0.spe'.format(run_id=run_id)
                else:  # for triple imaging
                    file = ['{run_id}_{idx}.spe'.format(
                        run_id=run_id, idx=idx) for idx in range(images_per_shot)]
                if append_mode:
                    run_dict = bc._send_message(
                        'get', '/runs/' + str(run_id) + '/').json()
                    if set(analyzed_var_names).issubset(set(run_dict['parameters'].keys())):
                        popped_id = [unanalyzed_ids.pop()]
                        done_ids += popped_id
                        continue
                try:
                    analysis_dict, previous_settings = analyze_image(
                        file, previous_settings)
                    popped_id = [unanalyzed_ids.pop()]
                    done_ids += popped_id
                    resp = bc.append_analysis_to_run(run_id, analysis_dict)
                except:  # if MATLAB analysis fails
                    analysis_dict = {'badshot': True}
                    warning_message = str(
                        run_id) + 'could not be analyzed. Marking as bad shot.'
                    resp = bc.append_analysis_to_run(run_id, analysis_dict)
                    popped_id = [unanalyzed_ids.pop()]
                    done_ids += popped_id
                    warnings.warn(warning_message)
                    logger.warn(warning_message)
                if resp.status_code != 200:
                    logger.warning('Upload error: ' + resp.text)

                if not save_images:  # delete images and add run_ids to .txt file after analysis if in testing mode
                    if isinstance(file, str):
                        filepath = os.path.join(watchfolder, file)
                        os.remove(filepath)
                        logger.debug(
                            'save_images is False, file {file} deleted after analysis.'.format(file=filepath))
                    elif isinstance(file, list):
                        for f in file:
                            filepath = os.path.join(watchfolder, f)
                            os.remove(filepath)
                            logger.debug(
                                'save_images is False, file {file} deleted after analysis.'.format(file=filepath))
                    with open(os.path.join(watchfolder, 'run_ids.txt'), 'a') as run_ids_file:
                        run_ids_file.write(str(popped_id[0]) + '\n')
                        logger.debug('Run_id {id} added to {file}.'.format(
                            id=str(popped_id[0]), file=os.path.join(watchfolder, 'run_ids.txt')))

                print('\n')

        time.sleep(refresh_time)


if __name__ == '__main__':
    analysis_shorthand = {'zt': 'zcam_triple_imaging',
                          'zd': 'zcam_dual_imaging',
                          'y': 'ycam'}
    print('analysis keys:')
    print(analysis_shorthand)
    analysis_key = input('Select analysis (e.g. zd for zcam_dual_imaging): ')
    analysis_type = analysis_shorthand[analysis_key]
    print('{analysis} selected'.format(analysis=analysis_type))
    print('existing runs: ')
    measurement_names = todays_measurements()
    if len(measurement_names) == 0:
        raise ValueError('No measurements yet today.')
    for name in sorted(measurement_names):
        if 'run' in name:
            if 'misplaced' not in name and '.csv' not in name:
                print(name)
                last_output = name
    watchfolder = suggest_run_name(newrun_input='n', appendrun_input='y')
    save_images = True
    save_images_input = input('Keep images after analysis? [y/n]: '
                              )
    if save_images_input == 'n':
        print('entering testing mode...')
        save_images = False

    clean_notebook_path = r'D:\Fermidata1\enrico\log viewer and plotterDUPLICATEANDUSETODAY.ipynb'
    if analysis_key == 'y':
        clean_notebook_path = r'C:\Users\FermiCam2\Desktop\GitHub\enrico\log viewer and plotterDUPLICATEANDUSETODAY.ipynb'
    nb_path = os.path.join(os.path.dirname(watchfolder), 'dailynb.ipynb')

    if not os.path.exists(nb_path):
        shutil.copy(clean_notebook_path, nb_path)
        print('no daily notebook, made a duplicate from {path} now.'.format(
            path=clean_notebook_path))
    try:
        main(analysis_type, watchfolder, load_matlab=True,
             images_per_shot=1, save_images=save_images)
    except KeyboardInterrupt:
        pass
    except:
        warning_message = '{folder} analysis crashed: '.format(folder=watchfolder) + 'Error: {}. {}, line: {}'.format(sys.exc_info()[0],
                                                                                                                      sys.exc_info()[
            1],
            sys.exc_info()[2].tb_lineno)
        # enrico_bot.post_message(warning_message)

        print(warning_message)
