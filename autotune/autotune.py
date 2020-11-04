from abc import ABC 

class Tunable(ABC):

    """An abstract method that will return the tuning knobs which a tunable has
    Returns:
    A dict of the tuning knobs which a tunable has, whose keys are their names. 
    Note: This should be a SHALLOW copy of the backing dict of tuning knobs which a 
    tunable has. If it's not a copy, then pops or other mischief could break the tunable.
    If it's a deep copy, then different instances of knobs appear. This won't break the 
    flow of information from knob to tunable, but will break the flow from tunable to knob. 
    """
    @abstractmethod 
    def get_tuning_knobs():
        pass 

    """An abstract method that tunes a given knob on a tunable by the specified value
    Parameters:
        knob_name: the name of the tunable knob which should be tuned 
        increment: the increment by which to return the knob 

    Returns:
        An integer status code whose specifics vary between tunables. 0 will always indicate a successful set, and errors will be negative.
    """
    @abstractmethod
    def tune_knob(knob_name, increment):
        pass 


#Implement a class Knob to wrap all the knobs that a tunable has; autotuner will then work on knobs, rather than tunables

class Knob():
    from math import copysign
    from time import sleep 

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
        self.MAX_VALUE = knob_dict['knob_max_value']
        self.TYPICAL_INCREMENT = knob_dict['typical_knob_increment']
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
    def tune(tuning_amount):
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
    

    def get_value():
        return self.value 

    def set_value(target_value):
        if(self.value == target_value):
            return 0
        if(self.VALUE_TYPE == "boolean"):
            return self.tune(target_value) 
        else:
            return self.tune(target_value - self.value)
    
    def set_lock(lock_status):
        self.is_locked = lock_status

    def get_lock():
        return self.is_locked()

    def get_name():
        return self.name 

    def get_lower_bound():
        return self.MIN_VALUE 
    
    def get_upper_bound():
        return self.MAX_VALUE 
    
    def get_value_type():
        return self.VALUE_TYPE 



class Autotuner():
    import numpy as np 

    """Initialization method.
    Parameters:
    signal_function: A function which, when called, returns the signal which autotuner is trying to MAXIMIZE. Any averaging/conditioning of this signal is
        done at the level of this function or lower. If a signal should be minimized, invert it before it gets here. 
    (OPTIONAL) Knobs_dict: A dict of tuples (knob, lower, upper) which give the knobs the autotuner can tune along with lower and upper bounds. Default None.
    """
    #TODO: Should add support for passing a dict with just knobs, where the lower and upper bounds are then furnished by the minimum and maximum 
    #values which are allowed for the knob.


    def __init__(self, signal_function, averages = 1, knobs_and_bounds_dict = None):
        self.signal_function = signal_function 
        self.knob_and_bound_dict = {}
        if(knobs_and_bounds_dict != None):
            for key in knobs_and_bounds_dict:
                self.knob_and_bound_dict[key] = list([knobs_and_bounds_dict[key]]) 
    
    def add_knob(knob, lower_bound = -np.inf, upper_bound = np.inf):
        new_knob_key = knob.get_name() 
        if new_knob_key in self.knob_and_bound_dict:
            raise ValueError("The autotuner already has a knob with the same name. To adjust bounds, call adjust_knob_bound")
        self.knob_and_bound_dict[new_knob_key] = [knob, knob., upper_bound] 
    
    "Removes the knob with name knob_name from the autotuner via pop"
    def remove_knob(knob_name):
        return self.knob_and_bound_dict.pop(knob_name)
    
    """Brute-force searches a region of knob parameter space.
    Divides knob parameter space into a grid of points, evaluates the signal at each point, and returns the parameters
    where it is MAXIMIZED.
    Parameters:
    Either a positive integer or a dict of iterables.
    If an integer c is passed, manually creates a grid which contains c different values for each knob, evenly spaced
    between the lower and upper bounds, subject to the requirement that each knobs' datatype is respected. Mainly for convenience.
    If a dict of iterables (e.g. lists), the dict is used to create a grid to be scanned over. If any knob's name does not appear in the dict, 
    it is left at its current value. This is the primary mode of operation when brute_force_tune is used in other 
    
    Returns:
    A tuple (0, valuedict) if the set occurred correctly; valuedict contains the optimal values found for each knob, with keys the knob names.
    A tuple (errorcode, None) if the set did not occur correctly. Error codes are all negative integers."""

    def brute_force_tune(*args):
        #Hacky way to check which input type we are given
        if(len(args) == 0):
            full_space_array_dict = get_full_space_array_dict()
            knob_list, search_array_list = make_searchgrid_from_array_dict(full_space_array_dict) 
        else:
            try:
                #If it's a dictionary, it'll be iterable
                for key in args[0]:
                    break
                knob_list, search_array_list = make_searchgrid_from_array_dict(args[0]) 
            except TypeError:
                #If it's an integer, it won't be
                full_space_array_dict = get_full_space_array_dict(number_points = args[0]) 
                knob_list, search_array_list = make_searchgrid_from_array_dict(full_space_array_dict) 
        maximum_signal = -np.inf 
        optimal_knob_values_list = None 
        #The first index of search_array_list is the knobs; the second index is the values to which to set them.
        for j in range(len(search_array_list[0])):
            for knob, knob_set_value in zip(knob_list, search_array_list[:][j]):
                set_code = knob.set_value(knob_set_value) 
                if(set_code < 0):
                    return (set_code, None) 
                else:
                    current_signal = self.signal_function() 
                    if(current_signal > maximum_signal):
                        maximum_signal = current_signal 
                        optimal_knob_values_list = search_array_list[:][j] 
        optimal_values_dict = {} 
        for knob, value in zip(knob_list, optimal_knob_values):
            optimal_values_dict[knob.get_name()] = value 
        return (0, optimal_values_dict) 

        



    """A helper function that makes a grid used by brute force tune
    Given a dict of iterables with the values which knobs should take on, assembles it into a meshgrid form. 
    Parameters:
    A dict of numeric (or boolean) iterables. Keys are the names of the knobs whose values it specifies.
    Returns:
    A tuple ([knobs], [knob_arrays]). The first element is an ordered list of knobs which are to be tweaked. The second 
    element is a list of numpy arrays, in the same order as the knobs, which represents the values that the knobs should be given for the search.
    The numpy arrays are, specifically, flattened outputs of np.meshgrid for each knob."""

    def make_searchgrid_from_array_dict(arrays_dict):
        ordered_knob_list = [] 
        knob_values_list = []
        for key in arrays_dict:
            ordered_knob_list.append(self.knob_and_bound_dict[key][0])
            knob_values_list.append(arrays_dict[key]) 
        meshgrid_output = np.meshgrid(*knob_values_list)
        knob_meshgrid_arrays_list = [] 
        for meshgrid in meshgrid_output:
            knob_meshgrid_arrays_list.append(meshgrid.flatten()) 
        return (ordered_knob_list, knob_meshgrid_arrays_list) 


    """Gives a dict of array-like values that covers the whole parameter space.
    Given a number of points, returns a dict which contains arrays of values to be given to each of the knobs
    that will cover all of parameter space, as determined by the bounds which autotune has for the knobs.
    Parameters:
    number_points: The number of points in each of the arrays. If a knob does not support that number of points
    -i.e. if 5 points are stipulated for a boolean knob or an int knob bounded by 1 and 4 - the number of points
    is silently rounded down to make sense.
    Returns:
    A dict of arrays of values for each knob which, if stitched together, cover the whole space. Should be passed to 
    make_searchgrid_from_array_dict in order to get a searchgrid suitable for scanning.
    Notes:
    If only one point is specified, booleans default to False, while numeric knobs default to the average of their upper and lower bounds,
    rounded for ints. This deviates from default behavior for np.linspace."""

    #TODO: Correct for the edge case where this breaks if either the upper or the lower bound passed to autotuner for a param are infinity
    #Not really a bug - you can't brute force scan over infinite parameter space - but should do something so that it can be used for convenience.
    def get_full_space_array_dict(number_points = 5):
        array_dict = {} 
        for key in self.knob_and_bound_dict:
            current_number_points = number_points
            current_knob = self.knob_and_bound_dict[key] 
            if(current_knob.get_value_type() == "boolean"):
                current_number_points = min(current_number_points, 2) 
                if(current_number_points == 1):
                    array_dict[key] = [False] 
                else:
                    array_dict[key] = [False, True]
            elif(current_knob.get_value_type() == "int"):
                current_knob_lower_bound = self.knob_and_bound_dict[key][1] 
                current_knob_upper_bound = self.knob_and_bound_dict[key][2]
                current_number_points = min(current_number_points, current_knob_upper_bound - current_knob_lower_bound + 1) 
                if(current_number_points == 1):
                    array_dict[key] = [int(np.round(1.0/2 * (current_knob_lower_bound + current_knob_upper_bound)))]
                else:
                    key_array = np.unique(np.round(np.linspace(current_knob_lower_bound, current_knob_upper_bound, current_number_points)))
                    key_array = key_array.astype(int) 
                    array_dict[key] = [key_array] 
            elif(current_knob_get_value_type() == "float"):
                current_knob_lower_bound = self.knob_and_bound_dict[key][1]
                current_knob_upper_bound = self.knob_and_bound_dict[key][2] 
                if(current_number_points == 1):
                    array_dict[key] = [1.0/2 * (current_knob_upper_bound + current_knob_lower_bound)] 
                else:
                    array_dict[key] = np.linspace(current_knob_lower_bound, current_knob_upper_bound, number_points)
        return array_dict 


                


        





        

        

        

    



