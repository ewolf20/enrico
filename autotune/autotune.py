from abc import ABC, abstractmethod
import numpy as np 
from math import copysign
from time import sleep 
import warnings 


class Tunable(ABC):

    """An abstract method that will return the tuning knobs which a tunable has
    Returns:
    A dict {knob_name:knob} of the tuning knobs which a tunable has, whose keys are their names. 
    Note: This should be a SHALLOW copy of the backing dict of tuning knobs which a 
    tunable has. If it's not a copy, then pops or other mischief could break the tunable.
    If it's a deep copy, then different instances of knobs appear. This won't break the 
    flow of information from knob to tunable, but will break the flow from tunable to knob. 
    """
    @abstractmethod 
    def get_tuning_knobs():
        pass 

    """An abstract method which returns the tuning knobs, plus their maximum and minimum allowed values.
    Returns:
    A dict as above, but of the form {knob_name:(knob, knob_lower, knob_upper)}, where knob_lower
    and knob_upper are the knob-level upper and lower bounds. The method is present for convenience.
    """
    @abstractmethod 
    def get_tuning_knobs_and_bounds():
        pass 

    """An abstract method that tunes a given knob on a tunable by the specified value
    Parameters:
        knob_name: the name of the tunable knob which should be tuned 
        increment: the increment by which to return the knob 

    Returns:
        An integer status code whose specifics vary between tunables. 0 will always indicate a successful set, and errors will be negative.
    """
    @abstractmethod
    def tune_knob(self, knob_name, increment):
        pass 


#Implement a class Knob to wrap all the knobs that a tunable has; autotuner will then work on knobs, rather than tunables

class Knob():

    """Initialization method
    Parameters:
    parent_device: The device object (some subclass of tunable) to which a knob is attached
    knob_dict: A dictionary of knob parameters.
        name: The name of the knob. Required to be unique between knobs derived from same Tunable. 
        initial_value: The value of the knob at initialization, e.g. the abs. position of a motor at startup
        min_value: The minimum value to which the knob can be set.
        max_value: The maximum value to which the knob can be set
        typical_increment: the `typical amount' of change in the knob which produces some measurably different signal.
        max_increment: The maximum amount by which the knob can be incremented in one go. 
        increment_waiting_time: The time that must be waited between multiple increments of the knob.
        value_type: the type of value the knob supports. Options are `float', `int', and `boolean'.
    """
    def __init__(self, parent_device, knob_dict):
        self.name = knob_dict['name']
        self.value = knob_dict['initial_value']
        self.INITIAL_VALUE = self.value 
        self.MIN_VALUE = knob_dict['min_value']
        self.MAX_VALUE = knob_dict['max_value']
        self.TYPICAL_INCREMENT = knob_dict['typical_increment']
        self.MAX_INCREMENT = knob_dict['max_increment']
        self.INCREMENT_WAIT_TIME = knob_dict['increment_wait_time']
        self.VALUE_TYPE = knob_dict['value_type']
        self.is_locked = False
        self.device = parent_device


    """The main method for tuning a knob.
    Parameters: Tuning amount:
    The amount by which to tune the knob. If the knob is of boolean type, this value is what the knob is set to
    Returns:
    An integer result code 
        0 if the set was ok
        -1 if the set terminated because the knob was locked or the set went out of bounds
        Various codes if hardware problems arise.
    Note: 
        This method can track the values of knobs at the software level provided that the hardware obeys the following contract:
        if 0 is returned, the set was performed successfully; if a negative error code is returned, the knob has not changed.
    """
    #TODO: Must add code handling what happens when a knob fails a tune AFTER some adjustment has been made. Does it try to re-home to 
    #initial position? Does it give up? 
    def tune(self, tuning_amount):
        if(self.is_locked):
            return -1
        if(self.VALUE_TYPE == "boolean"):
            code = self.device.tune_knob(self.name, tuning_amount) 
            if(code == 0):
                self.value = tuning_amount 
            return code
        if(tuning_amount == 0):
            return 0
        if(self.value + tuning_amount > self.MAX_VALUE or self.value + tuning_amount < self.MIN_VALUE):
            return -1
        tuning_sign = round(copysign(1, tuning_amount)) 
        tuning_magnitude = abs(tuning_amount)
        while(tuning_magnitude > 0):
            increment = min(self.MAX_INCREMENT, tuning_magnitude) 
            current_code = self.device.tune_knob(self.name, tuning_sign * increment)
            if(current_code == 0):
                tuning_magnitude -= increment 
                self.value += tuning_sign * increment 
                sleep(self.INCREMENT_WAIT_TIME)
            else:
                return current_code 
        return 0 
    

    def get_value(self):
        return self.value 

    def set_value(self,target_value):
        if(self.value == target_value):
            return 0
        if(self.VALUE_TYPE == "boolean"):
            return self.tune(target_value) 
        else:
            return self.tune(target_value - self.value)
    
    def set_lock(self, lock_status):
        self.is_locked = lock_status

    def get_lock(self):
        return self.is_locked()

    def get_name(self):
        return self.name 

    def get_lower_bound(self):
        return self.MIN_VALUE 
    
    def get_upper_bound(self):
        return self.MAX_VALUE 
    
    def get_value_type(self):
        return self.VALUE_TYPE 




class Autotuner():
    """Initialization method.
    Parameters:
    signal_function: A function which, when called, returns the signal which autotuner is trying to MAXIMIZE. Any averaging/conditioning of this signal is
        done at the level of this function or lower. If a signal should be minimized, invert it before it gets here. 
    (OPTIONAL) Knobs_dict: A dict of tuples {knob_name:(knob, lower, upper)} containing knobs autotuner should tune and their bounds.
    Note: Knobs can also be added post-initialization with add_knob()
    """

    def __init__(self, signal_function, knobs_and_bounds_dict = None):
        self.signal_function = signal_function 
        self.knob_and_bound_dict = {}
        if(knobs_and_bounds_dict != None):
            for key in knobs_and_bounds_dict:
                #Star syntax unpacks iterable
                self.add_knob(*(knobs_and_bounds_dict[key]))
    
    def add_knob(self, knob, lower_bound = -np.inf, upper_bound = np.inf):
        new_knob_key = knob.get_name() 
        if new_knob_key in self.knob_and_bound_dict:
            raise ValueError("The autotuner already has a knob with the same name. To adjust bounds, call adjust_knob_bound")
        if(knob.get_value_type() == "boolean"):
            self.knob_and_bound_dict[new_knob_key] = [knob, False, True] 
        else:
            if(upper_bound > knob.get_upper_bound()):
                warnings.warn("Upper bound defaulted to knob maximum.")
            upper_bound = min(upper_bound, knob.get_upper_bound()) 
            if(lower_bound < knob.get_lower_bound()):
                warnings.warn("Lower bound defaulted to knob minimum.")
            lower_bound = max(lower_bound, knob.get_lower_bound()) 
            self.knob_and_bound_dict[new_knob_key] = [knob, lower_bound, upper_bound]
    
    "Removes and returns the knob with name knob_name from the autotuner via pop"
    def remove_knob(self, knob_name):
        return self.knob_and_bound_dict.pop(knob_name)[0]

    "Changes the knob bound."
    def change_knob_bound(self, knob_name, lower_bound, upper_bound):
        knob_list = self.knob_and_bound_dict[knob_name]
        knob = knob_list[0]
        if(lower_bound < knob.get_lower_bound()):
            warnings.warn("Lower bound defaulted to knob minimum")
        lower_bound = max(lower_bound, knob.get_lower_bound())
        if(upper_bound > knob.get_upper_bound()):
            warnings.warn("Upper bound defaulted to knob maximum")
        upper_bound = min(upper_bound, knob.get_upper_bound())
        knob_list[1] = lower_bound
        knob_list[2] = upper_bound

    """Brute-force searches a region of knob parameter space.
    Divides knob parameter space into a grid of points, evaluates the signal at each point, and returns the parameters
    where it is MAXIMIZED.

    Parameters:
    args[0]: Either a positive integer or a dict of iterables.
    If an integer c is passed, manually creates a grid which contains c different values for each knob, evenly spaced
    between the lower and upper bounds, subject to the requirement that each knobs' datatype is respected. Mainly for convenience.
    If a dict of iterables (e.g. lists), the dict is used to create a grid to be scanned over. If any knob's name does not appear in the dict, 
    it is left at its current value. This is the primary mode of operation when brute_force_tune is used in other methods
    autoset: Whether the tuner should, after completion, automatically set the knobs to the most optimal value it found. Default is false. 
    number_optimal_points: The number of optimal points to return: if this is 3, brute force search returns the three best points it found. 
    simple_output: Whether to simplify the output in the case where number_optimal_points = 1. Default false. 
    verbose: if True, the last i and j values looped over are appended to the end of the returned tuple. Useful for debugging.
    
    Returns:
    A tuple (0, [(signal1, valuedict1), (signal2, valuedict2), ... (signalN, valuedictN)]) 
        if the search occurred correctly; valuedict contains the optimal values found for each knob, with keys the knob names.
        The value dicts are in order of most to least optimal parameters, i.e. decreasing signal.
        If number_optimal_points == 1 and simple_output, then returns instead (0, signal1, valuedict1) for convenience.
    A tuple (errorcode, [(signal1, valuedict1), (signal2, valuedict2), ... (signalM, valuedictM)]) if the set did not occur correctly;
    the list is the best values found before the crash and may be empty. 
    
    Notes:
    Brute force search makes no stability promises if it finds two points with the same signal value."""

    def brute_force_tune(self, *args, autoset = False, number_optimal_points = 1, simple_output = False, verbose = False):
        #Hacky way to check which input type we are given
        if(len(args) == 0):
            full_space_array_dict = self.get_full_space_array_dict()
            knob_list, search_array = self._make_searchgrid_from_array_dict(full_space_array_dict) 
        else:
            try:
                #If it's a dictionary, it'll be iterable
                for key in args[0]:
                    break
                knob_list, search_array = self._make_searchgrid_from_array_dict(args[0]) 
            except TypeError:
                #If it's an integer, it won't be
                full_space_array_dict = self.get_full_space_array_dict(number_points = args[0]) 
                knob_list, search_array = self._make_searchgrid_from_array_dict(full_space_array_dict) 
        signal_and_j_list = []
        #The first index of search_array_list is the knob; the second index is the value to which to set it.
        #That is, to iterate over values, you should iterate over the second index first
        for j in range(len(search_array[0])):
            for knob, knob_set_value, i in zip(knob_list, search_array[:,j], range(len(knob_list))):
                set_code = knob.set_value(knob_set_value) 
                if(set_code < 0):
                    best_signal_and_value_dict_list = self._brute_force_tune_signal_and_j_list_helper(signal_and_j_list, search_array, knob_list, number_optimal_points)
                    if(verbose):
                        return (set_code, best_signal_and_value_dict_list, i, j) 
                    else:
                        return (set_code, best_signal_and_value_dict_list)
            current_signal = self.signal_function() 
            signal_and_j_list.append((current_signal, j)) 
        best_signal_and_value_dict_list = self._brute_force_tune_signal_and_j_list_helper(signal_and_j_list, search_array, knob_list, number_optimal_points)
        if(autoset):
            best_value_dict = best_signal_and_value_dict_list[0][1] 
            for knob in knob_list:
                optimal_knob_value = best_value_dict[knob.get_name()] 
                knob.set_value(optimal_knob_value) 
        if(verbose):
            return (0, best_signal_and_value_dict_list, len(search_array) - 1, len(search_array[0]) - 1) 
        else:
            return (0, best_signal_and_value_dict_list)

    """A helper function for brute_force_tune which, given a list of signals and j values, returns a trimmed list of (signal, valuedict) tuples"""
    @staticmethod
    def _brute_force_tune_signal_and_j_list_helper(signal_and_j_list, search_array, knob_list, number_optimal_points):
        sorted_signal_and_j_list = sorted(signal_and_j_list, key = (lambda v: v[0]), reverse = True)
        best_signal_and_j_list = sorted_signal_and_j_list[:number_optimal_points] 
        best_signal_and_value_dict_list = [] 
        for signal_and_j_tuple in best_signal_and_j_list:
            values_dict = {} 
            signal_value = signal_and_j_tuple[0] 
            values_array = search_array[:, signal_and_j_tuple[1]] 
            for knob, value in zip(knob_list, values_array):
                values_dict[knob.get_name()] = value 
            best_signal_and_value_dict_list.append((signal_value, values_dict)) 
        return best_signal_and_value_dict_list 




    """A helper function that makes a grid used by brute force tune
    Given a dict of iterables with the values which knobs should take on, assembles it into a meshgrid form. 
    Parameters:
    A dict of numeric (or boolean) iterables. Keys are the names of the knobs whose values it specifies.
    Returns:
    A tuple ([knobs], [knob_arrays]). The first element is an ordered list of knobs which are to be tweaked. The second 
    element is a 2D numpy array; the first index is mapped to the knobs in the same order as the knob list, while the second index 
    is the value to which the knob should be set for the search.
    The column arrays are, specifically, flattened outputs of np.meshgrid for each knob.
    Note: This will break, hard, if you try to pass in anything but numeric (or boolean) types in the arrays."""

    def _make_searchgrid_from_array_dict(self, arrays_dict):
        if(arrays_dict == None):
            return (None, None) 
        if(len(arrays_dict) == 0):
            return ([], np.empty((0, 0))) 
        ordered_knob_list = [] 
        knob_values_list = []
        for key in arrays_dict:
            ordered_knob_list.append(self.knob_and_bound_dict[key][0])
            knob_values_list.append(arrays_dict[key]) 
        meshgrid_output = np.meshgrid(*knob_values_list)
        knob_searchgrid_array = np.empty((len(ordered_knob_list), len(meshgrid_output[0].flatten())))
        for meshgrid, i in zip(meshgrid_output, range(len(meshgrid_output))):
            knob_searchgrid_array[i] = meshgrid.flatten()
        return (ordered_knob_list, knob_searchgrid_array) 


    """Gives a dict of array-like values that covers the whole parameter space.
    Given a number of points, returns a dict which contains arrays of values to be given to each of the knobs
    that will cover all of parameter space, as determined by the bounds which autotune has for the knobs.
    Parameters:
    number_points: The number of points in each of the arrays. If a knob does not support that number of points
    -i.e. if 5 points are stipulated for a boolean knob or an int knob bounded by 1 and 4 - the number of points
    is silently rounded down to make sense.
    Returns:
    A dict of np arrays of values for each knob which, if stitched together, cover the whole space. Should be passed to 
    make_searchgrid_from_array_dict in order to get a searchgrid suitable for scanning.
    Notes:
    If only one point is specified, booleans default to False, while numeric knobs default to the average of their upper and lower bounds,
    rounded for ints. This deviates from default behavior for np.linspace."""

    #TODO: Correct for the edge case where this breaks if either the upper or the lower bound passed to autotuner for a param are infinity
    #Not really a bug - you can't brute force scan over infinite parameter space - but should do something so that it can be used for convenience.
    def get_full_space_array_dict(self, number_points = 5):
        array_dict = {} 
        for key in self.knob_and_bound_dict:
            current_number_points = number_points
            current_knob = self.knob_and_bound_dict[key][0] 
            if(current_knob.get_value_type() == "boolean"):
                current_number_points = min(current_number_points, 2) 
                if(current_number_points == 1):
                    array_dict[key] = np.array([False])
                else:
                    array_dict[key] = np.array([False, True])
            elif(current_knob.get_value_type() == "int"):
                current_knob_lower_bound = self.knob_and_bound_dict[key][1] 
                current_knob_upper_bound = self.knob_and_bound_dict[key][2]
                current_number_points = min(current_number_points, current_knob_upper_bound - current_knob_lower_bound + 1) 
                if(current_number_points == 1):
                    array_dict[key] = np.array([int(np.round(1.0/2 * (current_knob_lower_bound + current_knob_upper_bound)))])
                else:
                    key_array = np.unique(np.round(np.linspace(current_knob_lower_bound, current_knob_upper_bound, current_number_points)))
                    key_array = key_array.astype(int) 
                    array_dict[key] = key_array 
            elif(current_knob.get_value_type() == "float"):
                current_knob_lower_bound = self.knob_and_bound_dict[key][1]
                current_knob_upper_bound = self.knob_and_bound_dict[key][2] 
                if(current_number_points == 1):
                    array_dict[key] = np.array([1.0/2 * (current_knob_upper_bound + current_knob_lower_bound)])
                else:
                    array_dict[key] = np.linspace(current_knob_lower_bound, current_knob_upper_bound, number_points)
        return array_dict 


    """A helper function for iterated brute force search that creates an array_dict centered on a specified point
    Given a dict containing the knob values which specify a certain point in parameter space, creates an array dict 
    that can be used to construct a searchgrid centered on that point which is smaller than a previous searchgrid.

    Parameters:
    point_values_dict: A dict {knob_name: knob_value} of knob values at the point about which we expand.
    point_spacing_dict: A dict {knob_name: knob_interval_width} of desired spacings between points in the new array_dict.
        Essentially, the new array_dict contains evenly spaced values in the interval [-knob_interval_width + knob_value, knob_interval_width + knob_value] 
    new_array_number_points: The number of points for each knob in the array_dict. Same silent rounding as in get_full_space_array_dict.
    expand_booleans: If True, the new array_dict will always contain [False, True] for any boolean input, provided new_array_number_points > 1.
        If False, the new array_dict will only contain the boolean value in point_values_dict. Default True.
    
    Returns:
        An array_dict as in get_full_space_array_dict, centered on the point specified by point_values_dict, with the given spacing, and respecting 
        the knob bounds. 
    """

    
    def get_array_dict_about_point(self, point_values_dict, point_interval_width_dict, new_array_number_points, expand_booleans = True):
        returned_array_dict = {}
        for key in point_values_dict:
            point_value = point_values_dict[key]
            point_interval_width = point_interval_width_dict[key] 
            point_knob, point_lower_bound, point_upper_bound = self.knob_and_bound_dict[key] 
            if(point_knob.get_value_type() == "boolean"):
                if(expand_booleans):
                    returned_array_dict[key] = np.array([False, True]) 
                else:
                    returned_array_dict[key] = np.array([point_value])
            elif(point_knob.get_value_type() == "int"):
                point_interval_width_rounded = int(np.round(point_interval_width)) 
                point_interval_upper_bound = int(np.round(min(point_value + point_interval_width_rounded, point_upper_bound)))
                point_interval_lower_bound = int(np.round(max(point_value - point_interval_width_rounded, point_lower_bound)))
                number_points = min(new_array_number_points, point_interval_upper_bound - point_interval_lower_bound + 1)
                if(number_points == 1):
                    returned_array_dict[key] = np.array([point_value]) 
                else:
                    point_array = np.unique(np.round(np.linspace(point_interval_lower_bound, point_interval_upper_bound, number_points))) 
                    point_array = point_array.astype(int) 
                    returned_array_dict[key] = point_array 
            elif(point_knob.get_value_type() == "float"):
                point_interval_upper_bound = min(point_value + point_interval_width, point_upper_bound) 
                point_interval_lower_bound = max(point_value - point_interval_width, point_lower_bound)
                returned_array_dict[key] = np.linspace(point_interval_lower_bound, point_interval_upper_bound, new_array_number_points) 
        return returned_array_dict






    """An iterated brute force search that successively narrows the search window.
    Executes a brute force search on the entire parameter space, then shrinks the parameter space to extend only
    around points with the highest signal and iterates. 
    Parameters:
        number_points: the number of points (in each parameter) to use in a given brute force scan
        depth: the number of times to conduct a brute force search-shrink cycle.
        explored_points: The number of points about which to conduct a brute force search when going to 
        a subsequent iteration. If 3, a brute force search would be conducted about the 3 best points from 
        the previous iteration.
        autoset: If true, the knobs are automatically set to the best values when the function terminates.
    Returns:
        A tuple (0, valuedict) if the set occurred correctly; valuedict contains the optimal values found for each knob, with keys the knob names.
        A tuple (errorcode, None) if the set did not occur correctly. Error codes are all negative integers.
    Notes: The present implementation will fail to converge if points_in_brute_force_grid is 3 or less. """
    #TODO: Consider adding support for searching less than the entire parameter space
    #TODO: Integrate the verbose and simple output flags 
    def iterated_brute_force_tune(
                self, points_in_brute_force_grid = 5, depth = 3, explored_points_per_level = 1,
                number_optimal_points = 1, autoset = False):
        current_array_dict_list = [self.get_full_space_array_dict(points_in_brute_force_grid)]
        for i in range(depth):
            current_spacing_dict_list = [] 
            for current_array_dict in current_array_dict_list:
                current_spacing_dict = {}
                for key in current_array_dict:
                    current_array = current_array_dict[key]
                    if(len(current_array) == 1):
                        current_spacing_dict[key] = 0
                    else:
                        if(self.knob_and_bound_dict[key][0].get_value_type() == "boolean"):
                            #Booleans aren't handled right by subtraction, but value is never used
                            current_spacing_dict[key] = 0
                        else:
                            current_spacing_dict[key] = abs(current_array[1] - current_array[0]) 
                current_spacing_dict_list.append(current_spacing_dict) 
            brute_force_tune_signal_and_values_tuple_list = []
            #This list contains the point spacings from the array that generated each optimal value. Needed for expanding. 
            brute_force_tune_spacing_dict_list = []
            for array_dict, spacing_dict in zip(current_array_dict_list, current_spacing_dict_list):
                brute_force_tune_results = self.brute_force_tune(array_dict, number_optimal_points = max(explored_points_per_level, number_optimal_points))
                brute_force_tune_signal_and_values_tuple_list.extend(brute_force_tune_results[1]) 
                brute_force_tune_spacing_dict_list.extend([spacing_dict] * len(brute_force_tune_results[1])) 
                #If an error code came back, just return the best points you have
                if(brute_force_tune_results[0] != 0):
                    sorted_brute_force_tune_signal_and_values_tuple_list = sorted(brute_force_tune_signal_and_values_tuple_list,
                                                                                key = (lambda v: v[0]), reverse = True)
                    trimmed_brute_force_tune_signal_and_values_tuple_list = sorted_brute_force_tune_signal_and_values_tuple_list[:number_optimal_points] 
                    return (brute_force_tune_results[0], trimmed_brute_force_tune_signal_and_values_tuple_list)
            #Having completed one iteration, find the best points and corresponding spacings 
            signal_and_values_tuples_and_spacings_list = list(zip(brute_force_tune_signal_and_values_tuple_list, brute_force_tune_spacing_dict_list)) 
            sorted_signal_and_values_tuples_and_spacings_list = sorted(signal_and_values_tuples_and_spacings_list, 
                                                                        key = (lambda v: v[0][0]), reverse = True)
            trimmed_signal_and_values_tuples_and_spacings_list = sorted_signal_and_values_tuples_and_spacings_list[:explored_points_per_level]
            if(i < depth - 1): 
                current_array_dict_list = [] 
                for signal_and_values_tuple_and_spacing in trimmed_signal_and_values_tuples_and_spacings_list:
                    values_dict = signal_and_values_tuple_and_spacing[0][1] 
                    spacing_dict = signal_and_values_tuple_and_spacing[1] 
                    array_dict = self.get_array_dict_about_point(values_dict, spacing_dict, points_in_brute_force_grid)
                    current_array_dict_list.append(array_dict) 
        #Re-trim the last sorted list of signal and values tuples
        final_sorted_signal_and_values_tuple_list = sorted(brute_force_tune_signal_and_values_tuple_list, key = (lambda v: v[0]), reverse = True) 
        final_trimmed_signal_and_values_tuple_list = final_sorted_signal_and_values_tuple_list[:number_optimal_points] 
        if(autoset):
            best_values_dict = final_trimmed_signal_and_values_tuple_list[0][1] 
            for key in best_values_dict:
                knob = self.knob_and_bound_dict[key][0] 
                knob.set_value(best_values_dict[key]) 
        return (0, final_trimmed_signal_and_values_tuple_list) 
        


                
             
            
                
                






                


        





        

        

        

    



