def getMATLABanalysis(eng, 
                      filepath, 
					  analysis_library_path = r'C:\Users\FermiCam2\Desktop\MatlabAnalysis\Fermi1_MatlabImageAnalysis'):
					  
	try:
		eng.eval(r'cd ' + analysis_library_path, nargout = 0)
		matlab_analysis = eng.getMeasNaAnalysis(filepath) #calling MATLAB function getMeasNaAnalysis
		return matlab_analysis
	except:
		print('check if the Carsten MATLAB code is at the path specified\n')
		print('check that an images exists at the filepath given')