class MATLABanalyzer:
    def __init__(self, engine,
                 analysis_library_path=r'C:\Users\FermiCam2\Desktop\MatlabAnalysis\Fermi1_MatlabImageAnalysis'):
        # analysis_library_path is set for ycam PC by default
        self.eng = engine
        self.analysis_library_path = analysis_library_path
        self.eng.eval(r'cd ' + analysis_library_path, nargout=0)

    def get_analysis(self, filepath):
        analysis_dict = self.eng.getMeasNaAnalysis(filepath)
        return analysis_dict
