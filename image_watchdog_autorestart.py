import subprocess
import logging
from measurement_directory import measurement_directory, todays_measurements
import enrico_bot
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')

# file_handler = logging.FileHandler(measurement_directory(
#     measurement_name='') + 'image_watchdog_autorestart_debugging.log')
# file_handler.setLevel(logging.DEBUG)
# file_handler.setFormatter(formatter)

# logger.addHandler(file_handler)
print('These names already exist: ')
print(todays_measurements())
run_idx = input('Enter run index: ')
name = input('Enter measurement_name: ')
measurement_name = 'run{idx}_{name}'.format(idx=run_idx, name=name)
n_images_per_run = input(
    'How many images arrive per shot? e.g. 3 for triple imaging ')

i = 0
while True:
    if i == 0:
        print('python image_watchdog.py {name} {n_images}'.format(name=measurement_name,
                                                                  n_images=n_images_per_run))
        p1 = subprocess.run('python image_watchdog.py {name} {n_images}'.format(name=measurement_name,
                                                                                n_images=n_images_per_run),
                            shell=True)
        enrico_bot.post_message('image_watchdog.py restarted automatically.')
        print('\n restarting')
        i += 1
    else:
        p1 = subprocess.run('python image_watchdog.py {name} {n_images}'.format(name=measurement_name + '_aftercrash',
                                                                                n_images=n_images_per_run),
                            shell=True)
