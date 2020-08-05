from PIL import Image
import numpy as np


def numpyfy_MATLABarray(matlab_array):
    return np.array(matlab_array._data).reshape(matlab_array.size, order='F')


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

        flatten_dict = {'analysis': {}, 'settings' = {}}
        for key in matlab_dict['K_analysis']:
            flatten_dict['analysis']['K_' +
                                     key] = matlab_dict['K_analysis'][key]
        for key in matlab_dict['Na_analysis']:
            flatten_dict['analysis']['Na_' +
                                     key] = matlab_dict['Na_analysis'][key]
        return flatten_dict
    except:
        print('matlab wrapper error')
