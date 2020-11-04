from autotune import Tunable, Knob, Autotuner 

"""A class for testing the autotuning module.
Spoofs a tunable by just returning 0 to every tune request. Also provides, for convenience, a signal function which is just a Gaussian, peaked at the 0 
values for each of the variables and optionally with some noise. 
"""
class Spoof_Tunable(Tunable):
    import numpy as np

    def __init__(self, number_float_knobs = 2, number_int_knobs = 0, number_boolean_knobs = 0):
        self.knobs_dict = {}
        self.rng = np.random.default_rng()
        self.eval_ticker = 0
        for i in range(number_float_knobs):
            current_float_knob = Knob(Spoof_Tunable, {'knob_name':'float_knob_'+str(i + 1), 'initial_value':0.0, 
            'min_value':-np.inf, 'max_value':np.inf 'typical_increment':1.0, 'max_increment':np.inf, 'increment_waiting_time':0.0, 'value_type':'float'})
            self.knobs_dict['float_knob_'+str(i + 1)] = current_float_knob
        for i in range(number_int_knobs):
            current_int_knob = Knob(Spoof_Tunable, {'knob_name':'int_knob_'+str(i + 1), 'initial_value':0, 
            'min_value':-np.inf, 'max_value':np.inf 'typical_increment':1, 'max_increment':np.inf, 'increment_waiting_time':0.0, 'value_type':'int'})
            self.knobs_dict['int_knob'+str(i + 1)] = current_int_knob 
        for i in range(number_boolean_knobs):
            current_boolean_knob = Knob(Spoof_Tunable, {'knob_name':'boolean_knob_'+str(i + 1), 'initial_value':False, 
            'min_value': 0, 'max_value':1 'typical_increment':1, 'max_increment':np.inf, 'increment_waiting_time':0.0, 'value_type':'boolean'})
            self.knobs_dict['boolean_knob'+str(i + 1)] = current_boolean_knob 
        
    
    """Implementation of required class method. Note that it returns a shallow copy of the tuning knob dict."""
    def get_tuning_knobs():
        return self.knobs_dict.copy()

    """Implementation of required class method."""
    def tune_knob(knob_name, increment):
        if(knob_name in self.knobs_dict):
            return 0
        else:
            return -1 
    
    def get_evals():
        return self.eval_ticker 
    
    def reset_evals():
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
    
    def give_spoofed_signal(noise = 0.0, amplitude = 1.0, sigma = 1.0):
        float_knob_values = [] 
        int_knob_values = [] 
        boolean_knob_values = []
        for key in self.knobs_dict:
            if key.startswith("float"):
                float_knob_values.append(self.knobs_dict[key].get_value())
            elif key.startswith("int"):
                int_knob_values.append(self.knobs_dict[key].get_value()) 
            elif key.startswith("boolean"):
                boolean_knob_values.append(self.knob_dict[key].get_value())
        value = amplitude * np.exp(-(sum(np.square(float_knob_values)) + sum(np.square(int_knob_values)))/(2 * sigma))
        if np.any(boolean_knob_values):
            value *= -1
        if(noise > 0.0):
            value += self.rng.normal(0, noise) 
        self.eval_ticker += 1
        return value 
        

def main():


if __name__ == "__main__":
    main() 
