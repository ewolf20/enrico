from autotune import Tunable, Knob, Autotuner 
import numpy as np
"""A class for testing the autotuning module.
Spoofs a tunable by just returning 0 to every tune request. Also provides, for convenience, a signal function which is just a Gaussian, peaked at the 0 
values for each of the variables and optionally with some noise. 
"""
class Spoof_Tunable(Tunable):

    def __init__(self, number_float_knobs = 2, number_int_knobs = 0, number_boolean_knobs = 0):
        self.knobs_dict = {}
        self.rng = np.random.default_rng()
        self.eval_ticker = 0
        for i in range(number_float_knobs):
            current_float_knob = Knob(
                self, {'name':'float_knob_'+str(i + 1), 'initial_value':0.0,
                'min_value':-np.inf, 'max_value':np.inf, 'typical_increment':1.0, 'max_increment':np.inf, 'increment_wait_time':0.0, 'value_type':'float'})
            self.knobs_dict['float_knob_'+str(i + 1)] = current_float_knob
        for i in range(number_int_knobs):
            current_int_knob = Knob(
                self, {'name':'int_knob_'+str(i + 1), 'initial_value':0, 
                'min_value':-np.inf, 'max_value':np.inf, 'typical_increment':1, 'max_increment':np.inf, 'increment_wait_time':0.0, 'value_type':'int'})
            self.knobs_dict['int_knob_'+str(i + 1)] = current_int_knob 
        for i in range(number_boolean_knobs):
            current_boolean_knob = Knob(
                self, {'name':'boolean_knob_'+str(i + 1), 'initial_value':False, 
                'min_value': 0, 'max_value':1, 'typical_increment':1, 'max_increment':np.inf, 'increment_wait_time':0.0, 'value_type':'boolean'})
            self.knobs_dict['boolean_knob_'+str(i + 1)] = current_boolean_knob 
        
    
    """Implementation of required class method. Note that it returns a shallow copy of the tuning knob dict."""
    def get_tuning_knobs(self):
        return self.knobs_dict.copy()

    """Implementation of required class method."""
    def get_tuning_knobs_and_bounds():
        return_dict = {} 
        for key in self.knobs_dict:
            knob = self.knobs_dict[key] 
            return_dict[key] = (knob, knob.get_lower_bound(), knob.get_upper_bound()) 
        return return_dict 

    """Implementation of required class method."""
    def tune_knob(self, knob_name, increment):
        if(knob_name in self.knobs_dict):
            return 0
        else:
            return -1 
    
    def get_evals(self):
        return self.eval_ticker 
    
    def reset_evals(self):
        self.eval_ticker = 0 

    """Return a spoofed signal.
    Returns a spoofed signal which is Gaussian and peaked when all numeric knobs are 0.
    The signal is inverted if any boolean parameter is True. Thus, the global maximum in parameter space is 
    when all numeric knobs are 0.
    Parameters:
        noise: The standard deviation of the mean 0 noise which is added to the signal. Default is 0.0. 
        amplitude: The amplitude of the signal. Somewhat redundant with noise, but added so that number-size effects are testable.
        sigma: The standard deviation - i.e. width - of the Gaussian signal.
    Returns:
    A floating point number representing the spoofed signal at the given knob settings.
    Notes:
    It is not usual for the signal which autotuner optimizes to come from a tunable; usually it will be returned by some 
    other object or function. This is included here for convenience.
    """
    
    def give_spoofed_signal(self,noise = 0.0, amplitude = 1.0, sigma = 1.0):
        float_knob_values = [] 
        int_knob_values = [] 
        boolean_knob_values = []
        for key in self.knobs_dict:
            if key.startswith("float"):
                float_knob_values.append(self.knobs_dict[key].get_value())
            elif key.startswith("int"):
                int_knob_values.append(self.knobs_dict[key].get_value()) 
            elif key.startswith("boolean"):
                boolean_knob_values.append(self.knobs_dict[key].get_value())
        float_knob_array = np.array(float_knob_values) 
        int_knob_array = np.array(int_knob_values) 
        boolean_knob_array = np.array(boolean_knob_values) 
        value = amplitude * np.exp(-(sum(np.square(float_knob_array + np.array([1.0, -1.0]))) + sum(np.square(int_knob_array)))/(2 * sigma))
        if np.any(boolean_knob_array):
            value *= -1
        if(noise > 0.0):
            value += self.rng.normal(0, noise) 
        self.eval_ticker += 1
        return value 
        

def main():
    my_spoof_tunable = Spoof_Tunable(number_boolean_knobs = 1, number_int_knobs = 1) 
    my_knobs_dict = my_spoof_tunable.get_tuning_knobs() 
    my_autotuner = Autotuner(my_spoof_tunable.give_spoofed_signal)
    my_autotuner.add_knob(my_knobs_dict["float_knob_1"], -2.0, 2.0) 
    my_autotuner.add_knob(my_knobs_dict["float_knob_2"], -2.0, 2.0) 
    my_autotuner.add_knob(my_knobs_dict["int_knob_1"], -2, 2) 
    my_autotuner.add_knob(my_knobs_dict["boolean_knob_1"])
    temp_knob = my_autotuner.remove_knob("float_knob_1")
    my_autotuner.add_knob(my_knobs_dict["float_knob_1"], -2.0, 2.0)
    my_results = my_autotuner.brute_force_tune(20, autoset = True, number_optimal_points = 3, verbose = True) 
    for key in my_knobs_dict:
        print(key + str(" = " + str(my_knobs_dict[key].get_value())))
    print(str(my_results))



if __name__ == "__main__":
    main() 
