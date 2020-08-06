# currently used on ycam

from PIL import Image
import numpy as np
from random import randint
import time

matlab_analysis = False  # disable this for quicker testing using fake_analysis
if matlab_analysis:
    print('loading matlab engine...')
    import matlab.engine
    eng = matlab.engine.start_matlab()
    print('matlab engine loaded')
else:
    print('no matlab engine, debugging mode')


def numpyfy_MATLABarray(matlab_array):
    return np.array(matlab_array._data).reshape(matlab_array.size, order='F')


"""All analysis functions accept image filepath and optionally previous settings, and return a (analysis_dict, settings_dict) tuple.
Most are powered by Carsten's MATLAB code through the matlab.engine API.

Known issues: - analysis_dict is often highly nested, which is difficult to log. Current workaround, only first-level, scalar values are logged."""


def fake_analysis1(filepath, previous_settings=None):
    time.sleep(randint(0, 5))
    return {'fake analysis 1': randint(0, 42), 'fake analysis 2': randint(0, 42)}, None


def fake_analysis2(filepath, previous_settings=None):
    time.sleep(randint(0, 5))
    return {'fake analysis 3': randint(0, 42), 'fake analysis 4': randint(0, 42)}, None


def ycam_analysis(filepath, previous_settings=None):
    def get_ycam_matlab_analysis(eng, filepath,
                                 analysis_library_path=r'C:\Users\FermiCam2\Desktop\MatlabAnalysis\Fermi1_MatlabImageAnalysis',
                                 marqueeBox=None, normBox=None, save_jpg_preview=True):
        try:
            eng.eval(r'cd ' + analysis_library_path, nargout=0)
            if marqueeBox is None and normBox is None:
                # calling MATLAB function getMeasNaAnalysis
                matlab_dict = eng.getMeasNaAnalysis(filepath)
            else:
                matlab_dict = eng.getMeasNaAnalysis(
                    filepath, 'marqueeBox', marqueeBox, 'normBox', normBox)

            if save_jpg_preview and 'ODimage' in matlab_dict:
                np_im = numpyfy_MATLABarray(matlab_dict['ODimage'])
                im = Image.fromarray(np_im)
                save_filepath = filepath.replace('.spe', '.jpeg')
                im.save(save_filepath)

            return matlab_dict
        except:
            print('matlab wrapper error')

    if previous_settings is None:
        matlab_dict = get_ycam_matlab_analysis(eng, filepath)
    else:
        matlab_dict = get_ycam_matlab_analysis(eng, filepath, marqueeBox=previous_settings['marqueeBox'],
                                               normBox=previous_settings['normBox'])
    analysis_dict, settings = matlab_dict['analysis'], matlab_dict['settings']
    return analysis_dict, settings


def dual_imaging_analysis(filepath, previous_settings=None):
    def getDualImagingAnalysis(eng, filepath,
                               analysis_library_path=r'C:\Users\FermiCam2\Desktop\MatlabAnalysis\Fermi1_MatlabImageAnalysis',
                               marqueeBox=None, normBox=None, save_jpg_preview=True):
        try:
            # eng.eval(r'cd ' + analysis_library_path, nargout=0)
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
            return flatten_dict
        except:
            print('matlab wrapper error')
    if previous_settings is None:
        matlab_dict = getDualImagingAnalysis(eng, filepath)
    analysis_dict = matlab_dict['analysis']
    settings = None
    return analysis_dict, settings
