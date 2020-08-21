import numpy as np 

def fancy_plot(x, y, fmt='', **kwargs):
    """Wraps around matplotlib.pyplot (aliased to plt) with last-point highlighting and statistics

    Plots x and y as in plt.plot, but a) averages together y-values with the same x-value and calculates and plots 
    an error bar, and b) plots the final (x,y) point in a different color than the previous ones. 

    Args:
        x: The x-data to be plotted. Assumed to be an iterable with contents of
            numeric type, including possibly np.nan
        y: The y-data to be plotted. Same assumptions on type.
        fmt: The format string. In contrast to plt.plot, it is a kwarg.
        kwargs: Any kwarg that can be passed to plt.errorbar.

    Returns:
        ErrorbarContainer, as detailed in the docs for plt.errorbar
    
    Raises:
        ValueError if x and y are not of the same length
    """


    import matplotlib.pyplot as plt
    if(len(x) != len(y)):
        raise ValueError("The input x and y arrays must be of the same length.")
    #Filter out the NaNs in either x or y while preserving order
    zipped_list = list(zip(x, y))
    nan_filter = filter(lambda v: ((not np.isnan(v[0])) and (not np.isnan(v[1]))), zipped_list)
    nan_stripped_list = list(nan_filter)
    #Pull off the last point so that it can be plotted in a different color
    if(len(nan_stripped_list) != 0):
        most_recent_xy_pair = nan_stripped_list[-1] 
        nan_stripped_list = nan_stripped_list[:len(nan_stripped_list) - 1]
    else:
        most_recent_xy_pair = None
    #Sort the NaN-stripped list to make getting statistics faster for large data
    sorted_list = sorted(nan_stripped_list, key = (lambda v: v[0]))
    #Reconstitute to x- and y- lists
    if(len(sorted_list) > 0):
        x_sorted, y_sorted = zip(*sorted_list)
        sorted_x_list = list(x_sorted) 
        sorted_y_list = list(y_sorted)
    else:
        sorted_x_list = []
        sorted_y_list = []
    #Perform statistics and condense repeated measurements
    index = 0
    final_x_list = []
    final_y_list = []
    final_error_list = []
    while(index < len(sorted_x_list)):
        current_x_value = sorted_x_list[index]
        final_x_list.append(current_x_value)
        y_list_for_current_x = []
        while(index < len(sorted_x_list) and sorted_x_list[index] == current_x_value):
            y_list_for_current_x.append(sorted_y_list[index])
            index += 1
        y_array_for_current_x = np.array(y_list_for_current_x)
        y_mean = sum(y_array_for_current_x) / float(len(y_array_for_current_x))
        final_y_list.append(y_mean)
        #Calculate the standard error of mean if possible
        if(len(y_list_for_current_x) == 1):
            final_error_list.append(np.nan)
        else:
            variance_estimate = sum(np.square(y_mean - y_array_for_current_x)) / float(len(y_array_for_current_x) - 1)
            standard_error_of_mean = np.sqrt(variance_estimate / len(y_array_for_current_x))
            final_error_list.append(standard_error_of_mean)
    #Convert all lists to np arrays
    final_x_values = np.array(final_x_list)
    final_y_values = np.array(final_y_list)
    final_error_values = np.array(final_error_list)
    #Plot the most recent point with a hardcoded but distinctive black diamond symbol
    if(most_recent_xy_pair != None):
        plt.plot(most_recent_xy_pair[0], most_recent_xy_pair[1], 'dk')
    #Plot and return the errorbar graph with the input kwargs
    return plt.errorbar(final_x_values, final_y_values, final_error_values, fmt = fmt, **kwargs)

