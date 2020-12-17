# currently used on ycam

from PIL import Image
import numpy as np

try:
    from utility_functions import load_analysis_path
    analysis_paths = load_analysis_path()
    ycam_path, dualimaging_path, tripleimaging_path = [analysis_paths[key] for key in ["ycam_imaging_folder",
                                                                                       "triple_imaging_folder",
                                                                                       "dual_imaging_folder"]]
except FileNotFoundError:  # stopgap until all computers which do analysis have an analysis_config.json
    ycam_path = r'C:\Users\FermiCam2\Desktop\MatlabAnalysis\Fermi1_MatlabImageAnalysis'
    dualimaging_path = r'C:\Users\Fermi1\Documents\GitHub\Fermi1_MatlabImageAnalysis'
    tripleimaging_path = r'C:\Users\Fermi1\Documents\GitHub\Fermi1_MatlabImageAnalysis'


def load_matlab_engine():
    print('loading matlab engine...')
    import matlab.engine
    eng = matlab.engine.start_matlab()
    print('matlab engine loaded')
    return eng


def numpyfy_MATLABarray(matlab_array):
    return np.array(matlab_array._data).reshape(matlab_array.size, order='F')

# getAnalysisModeAnalysis takes (matlab_engine, filepath, **kwargs) and returns a dictionary translated from a MATLAB analysis struct.
# analysismode_analyzed_var_names is manually defined to include scalar values from the analysis dictionary. These are most easily written to breadboard.


ycam_analyzed_var_names = ['bareNcntAverageMarqueeBoxValues',
                           'COMX', 'COMY', 'xTFinsitu_pix', 'yTFinsitu_pix',
                           'chem_potential_kHz', 'N_condensate',
                           'xTF_afterToF', 'yTF_afterToF',
                           'meanGaussianRadius', 'meanFWHM']


def getYcamAnalysis(eng, filepath,
                    analysis_library_path=ycam_path,
                    marqueeBox=None, normBox=None, save_jpg_preview=True):
    try:
        eng.eval(r'cd ' + analysis_library_path, nargout=0)
        if marqueeBox is None and normBox is None:
            # calling MATLAB function
            matlab_dict = eng.getYcamAnalysis(filepath)
        else:
            matlab_dict = eng.getYcamAnalysis(
                filepath, 'marqueeBox', marqueeBox, 'normBox', normBox)

        if save_jpg_preview and 'ODimage' in matlab_dict:
            np_im = numpyfy_MATLABarray(matlab_dict['ODimage'])
            im = Image.fromarray(np_im)
            save_filepath = filepath.replace('.spe', '.jpeg')
            im.save(save_filepath)

        return matlab_dict
    except:
        print('matlab wrapper error')


dual_imaging_analyzed_var_names = ['K_NcntLarge', 'Na_NcntLarge', 'K_NcntSmall', 'Na_NcntSmall',
                                   'Na_COMX', 'Na_COMY']


def getDualImagingAnalysis(eng, filepath,
                           analysis_library_path=dualimaging_path,
                           marqueeBox=None, normBox=None, save_jpg_preview=True):
    try:
        eng.eval(r'cd ' + analysis_library_path, nargout=0)
        matlab_dict = eng.getDualImagingZcamAnalysis(filepath)
        # if marqueeBox is None and normBox is None:
        #     matlab_dict = eng.getMeasNaAnalysis(filepath) #calling MATLAB function getMeasNaAnalysis
        # else:
        #     matlab_dict = eng.getMeasNaAnalysis(filepath, 'marqueeBox', marqueeBox, 'normBox', normBox)

        if save_jpg_preview and 'ODimage' in matlab_dict:
            np_im = numpyfy_MATLABarray(matlab_dict['ODimage'])
            im = Image.fromarray(np_im)
            save_filepath = filepath.replace('.spe', '.jpeg')
            im.save(save_filepath)

        flatten_dict = {'analysis': {}, 'settings': {}}
        for key in matlab_dict['K_analysis']:
            flatten_dict['analysis']['K_' +
                                     key] = matlab_dict['K_analysis'][key]
        for key in matlab_dict['Na_analysis']:
            flatten_dict['analysis']['Na_' +
                                     key] = matlab_dict['Na_analysis'][key]
        # matlab struct object is passed to python as a dictionary, to be parsed in analysis_logger.py
        return flatten_dict
    except:
        analysis_keys = ['K_analysis', 'Na_analysis']
        if any([(key not in matlab_dict) for key in analysis_keys]):
            print(
                'At least one of {key} was not returned from MATLAB.'.format(key=str(analysis_keys)))
        else:
            print('MATLAB analysis finished but python wrapper failed.')


triple_imaging_analyzed_var_names = ['K1_bareNcntAverageMarqueeBoxValues', 'K2_bareNcntAverageMarqueeBoxValues', 'Na_bareNcntAverageMarqueeBoxValues',
                                     'Na_COMX', 'Na_COMY']


def getTripleImagingAnalysis(eng, filepaths,
                             analysis_library_path=tripleimaging_path,
                             marqueeBox=None, normBox=None, save_jpg_preview=True):
    try:
        eng.eval(r'cd ' + analysis_library_path, nargout=0)
        matlab_dict = eng.getTripleImagingZcamAnalysis(filepaths[0],
                                                       filepaths[1], filepaths[2])
        # if marqueeBox is None and normBox is None:
        #     matlab_dict = eng.getMeasNaAnalysis(filepath) #calling MATLAB function getMeasNaAnalysis
        # else:
        #     matlab_dict = eng.getMeasNaAnalysis(filepath, 'marqueeBox', marqueeBox, 'normBox', normBox)

        if save_jpg_preview and 'ODimage' in matlab_dict:
            np_im = numpyfy_MATLABarray(matlab_dict['ODimage'])
            im = Image.fromarray(np_im)
            save_filepath = filepath.replace('.spe', '.jpeg')
            im.save(save_filepath)

        flatten_dict = {'analysis': {}, 'settings': {}}
        for key in matlab_dict['K1_analysis']:
            flatten_dict['analysis']['K1_' +
                                     key] = matlab_dict['K1_analysis'][key]
        for key in matlab_dict['K2_analysis']:
            flatten_dict['analysis']['K2_' +
                                     key] = matlab_dict['K2_analysis'][key]
        for key in matlab_dict['Na_analysis']:
            flatten_dict['analysis']['Na_' +
                                     key] = matlab_dict['Na_analysis'][key]
        # matlab struct object is passed to python as a dictionary, to be parsed in analysis_logger.py
        return flatten_dict
    except:
        analysis_keys = ['K1_analysis', 'K2_analysis', 'Na_analysis']
        if any([(key not in matlab_dict) for key in analysis_keys]):
            print(
                'At least one of {key} was not returned from MATLAB.'.format(key=str(analysis_keys)))
        else:
            print('MATLAB analysis finished but python wrapper failed.')

class AnalysisSettingsUpdater:

    # A class for updating MATLAB analysis settings by passing the most recent image(s) to a matlab function that requires manual user input
    # to set various settings (e.g. the normBox coordinates).

    def __init__(self, wrapped_matlab_func, images_per_shot):
        """
        Initialize the object with wrapped_matlab_func, which passes a tuple of filepath(s) (or a single filepath string) to a MATLAB engine and analysis function, and the number
        of images (and hence filepaths) to be retrieved for wrapped_matlab_func (e.g. 3 for triple imaging).
        """
        self.matlab_func = wrapped_matlab_func
        self.images_per_shot = images_per_shot
        self.eng = load_matlab_engine()

    def update(self):
        """
        Update matlab analysis settings config file.
        """
        from measurement_directory import measurement_directory, suggest_run_name, run_ids_from_filenames
        import os

        def get_last_filepaths():
            # returns either one path string or a list of paths
            watchfolder = measurement_directory(measurement_name=suggest_run_name(newrun_input='n',
                                                                                  appendrun_input='y'))
            files = [filename for filename in os.listdir(watchfolder)]
            filesSPE = []
            for file in files:  # filter out non .spe files
                if '.spe' in file:
                    filesSPE.append(file)
            files = filesSPE
            run_ids = sorted(run_ids_from_filenames(files))
            paths = [os.path.join(watchfolder, str(run_ids[-1]) + '_{idx}.spe'.format(idx=str(i)))
                     for i in range(self.images_per_shot)]
            if len(paths) == 1:
                return paths[0]
            return paths

        paths = get_last_filepaths()
        print('Updating analysis settings using: ')
        print(paths)
        self.matlab_func(self.eng, paths)

        # allow user to run update again
        done = input('Done calibrating analysis settings? [y/n]: ')
        if done == 'n':
            self.update()


def update_dual_imaging_settings(eng, filepath, analysis_library_path=dualimaging_path):
    # wrapper for executing MATLAB function
    eng.eval(r'cd ' + analysis_library_path, nargout=0)
    eng.INSERTMATLABFUNCTIONHERE(filepath)  # TODO


def update_triple_imaging_settings(eng, filepaths, analysis_library_path=tripleimaging_path):
    # wrapper for executing MATLAB function
    eng.eval(r'cd ' + analysis_library_path, nargout=0)
    eng.INSERTMATLABFUNCTIONHERE(
        filepaths[0], filepaths[1], filepaths[2])  # TODO


##################################################################################################################################


fake_analysis1_var_names = ['fake analysis 1', 'fake analysis 2']


def fake_analysis1(filepath, previous_settings=None):
    from random import randint
    time.sleep(randint(0, 2))
    return {'fake analysis 1': randint(0, 42), 'fake analysis 2': randint(0, 42)}, None


fake_analysis2_var_names = ['fake analysis 3', 'fake analysis 4']


def fake_analysis2(filepath, previous_settings=None):
    from random import randint
    time.sleep(randint(0, 5))
    return {'fake analysis 3': randint(0, 42), 'fake analysis 4': randint(0, 42)}, None
