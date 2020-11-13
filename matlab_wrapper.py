# currently used on ycam

from PIL import Image
import numpy as np

try:
    from utility_functions import load_analysis_path
    analysis_paths = load_analysis_path()
    ycam_path, dualimaging_path, tripleimaging_path = [analysis_paths[key] for key in ["ycam_imaging_folder",
                                                                                       "triple_imaging_folder",
                                                                                       "dual_imaging_folder"]]
except FileNotFoundError: #stopgap until all computers which do analysis have an analysis_config.json
    ycam_path = r'C:\Users\FermiCam2\Desktop\MatlabAnalysis\Fermi1_MatlabImageAnalysis'
    dualimaging_path = r'C:\Users\Fermi1\Documents\GitHub\Fermi1_MatlabImageAnalysis'
    tripleimaging_path = r'C:\Users\Fermi1\Documents\GitHub\Fermi1_MatlabImageAnalysis'


def numpyfy_MATLABarray(matlab_array):
    return np.array(matlab_array._data).reshape(matlab_array.size, order='F')

# getAnalysisModeAnalysis takes (matlab_engine, filepath, **kwargs) and returns a dictionary translated from a MATLAB analysis struct.
# analysismode_analyzed_var_names is manually defined to include scalar values from the analysis dictionary. These are most easily written to breadboard.


ycam_analyzed_var_names = ['bareNcntAverageMarqueeBoxValues',
                           'COMX', 'COMY', 'xTFinsitu_pix', 'yTFinsitu_pix',
                           'chem_potential_kHz', 'N_condensate',
                           'xTF_afterToF', 'yTF_afterToF']


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


dual_imaging_analyzed_var_names = ['K_bareNcntAverageMarqueeBoxValues', 'Na_bareNcntAverageMarqueeBoxValues',
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
