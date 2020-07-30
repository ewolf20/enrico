def getMATLABanalysis(eng, 
                      filepath, 
					  analysis_library_path = r'C:\Users\FermiCam2\Desktop\MatlabAnalysis\Fermi1_MatlabImageAnalysis',
                     marqueeBox = None, normBox = None):
					  
	try:
		eng.eval(r'cd ' + analysis_library_path, nargout = 0)
		if marqueeBox is None and normBox is None:
            matlab_dict = eng.getMeasNaAnalysis(filepath) #calling MATLAB function getMeasNaAnalysis
        else:
            matlab_dict = eng.getMeasNaAnalysis(filepath, 'marqueeBox', marqueeBox, 'normBox', normBox)
		return matlab_analysis
	except:
		print('check if the Carsten MATLAB code is at the path specified\n')
		print('check that an images exists at the filepath given')
		
		