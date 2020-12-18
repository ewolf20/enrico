# from measurement_directory import todays_measurements, measurement_directory

# measurement_directory()
# print(todays_measurements())

# testing get_newest_run_dict(bc)
# from utility_functions import *
# import time
# bc = load_breadboard_client()
# successes = 0
# failures = []

# for i in range(3600):
#     try:
#         run_dictv1 = get_newest_run_dict(bc)
#         run_dictv2 = get_newest_run_dict_v2(bc)
#         pair = (run_dictv1['run_id'], run_dictv1['run_id'])
#         if (run_dictv1['run_id'] == run_dictv2['run_id']):
#             successes += 1
#         else:
#             failures += [pair]
#         print(pair)
#         print('successes:', successes)
#         print('failures:', len(failures))
#     except:
#         pass
#     time.sleep(1)

# breakpoint()

# from utility_functions import load_breadboard_client, get_newest_run_dict
# # import matplotlib.pyplot as plt
# # import time
# bc = load_breadboard_client()
# resp = bc._send_message('get', '/runs/360500',
#                         params={'lab': 'fermi1', 'limit': 1})
# for i in range(10):
#     print(get_newest_run_dict(bc)['run_id'])

# for i in range(100):
#     print(bc._send_message(
#         'get', '/runs/', params={'lab': 'fermi1', 'limit': 1}).status_code)
# ids = []
# failures = 0
# for i in range(1800):
#     # print(i, success, failures)
#     try:
#         #     id_nolimit = (bc._send_message(
#         #         'get', '/runs/', params={'lab': 'fermi1'}).json()['results'][0]['id'])
#         run_dict = get_newest_run_dict(bc)
#         print(run)
#         # id_withlimit = bc._send_message(
#         #     'get', '/runs/', params={'lab': 'fermi1', 'limit': 1}).json()['results'][0]['id']
#         # ids += [id_withlimit]
#         # print(ids)
#         # if id_nolimit == id_withlimit:
#         #     success += 1
#         # else:
#         #     failures += 1
#     except KeyboardInterrupt:
#         pass
#     except:
#         failures += 1
#         breakpoint()
#         raise
# # print(failures)
# plt.plot(ids)
# breakpoint()


# for i in range(10):
#     print(bc.get_runs_df_from_ids([259499, 260500],
#                                   optional_column_names=['measurement_name']))
#     time.sleep(1)

# import pandas as pd
# import datetime
# bc = load_breadboard_client()
# df = pd.read_csv('run9_EITdownlegAOM55MHz_params.csv')
# run_ids = list(df['run_id'])
# # run_ids = [259499, 260400]
# now = datetime.datetime.now()
# df = bc.get_runs_df_from_ids(run_ids)
# print(df)
# later = datetime.datetime.now()
# print(later - now)
# print(len(df), len(run_ids))
# print(df)


# resp = bc._send_message('get', '/runs/259499').json()
# print(filter_response(resp))

# breakpoint()

# import os
# dummy_path = os.getcwd()
# dummy_paths = []
# for _ in range(3):
#     dummy_paths += [dummy_path]
#     dummy_path = os.path.dirname(dummy_path)

# for path in reversed(dummy_paths):
#     print(os.path.exists(path))

# import datetime
# import time

# now = datetime.datetime.now()
# time.sleep(1)
# then = datetime.datetime.now()
# print((then - now).total_seconds())

# from measurement_directory import *
# from utility_functions import load_analysis_path
# try:
#     analysis_paths = load_analysis_path()
#     data_basepath = analysis_paths['data_basepath']
# except FileNotFoundError:
#     data_basepath = ''
#     print('analysis_config.json not found, using default settings.')
# # analysis_shorthand = {'zt': 'zcam_triple_imaging',
# #                       'zd': 'zcam_dual_imaging',
# #                       'y': 'ycam'}
# # print('analysis keys:')
# # print(analysis_shorthand)
# # analysis_key = input('Select analysis (e.g. zd for zcam_dual_imaging): ')
# # analysis_type = analysis_shorthand[analysis_key]
# # print('{analysis} selected'.format(analysis=analysis_type))
# print('existing runs: ')
# measurement_names = todays_measurements(basepath=data_basepath)
# if len(measurement_names) == 0:
#     raise ValueError('No measurements yet today.')
# for name in sorted(measurement_names):
#     if 'run' in name:
#         if 'misplaced' not in name and '.csv' not in name:
#             print(name)
#             last_output = name
# watchfolder = measurement_directory(
#     measurement_name=suggest_run_name(newrun_input='n', appendrun_input='y', basepath=data_basepath))
# print(watchfolder)

from matlab_wrapper import AnalysisSettingsUpdater

tester = AnalysisSettingsUpdater(lambda x: None, 1)
tester.update()
