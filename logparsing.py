# module for misc helper functions for parsing log files, MATLAB objects etc.

def translate_stringy_list(stringy_list):
    # pd.read_csv imports listboundvariables dtype as a string, we want it in list form
    final_list = []
    stringy_list = stringy_list.split(',')
    for var in stringy_list:
        final_list.append(var.translate({ord(c): None for c in '[ ]\,\''}))
    return final_list
