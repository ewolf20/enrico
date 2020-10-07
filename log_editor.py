breadboard_repo_path = r'D:\Fermidata1\enrico\breadboard-python-client\\'
# breadboard_repo_path = r'C:\Users\Alex\Dropbox (MIT)\lab side projects\control software\breadboard-python-client\\'
from utility_functions import load_breadboard_client
bc = load_breadboard_client()
import os
import ipywidgets as widgets
from measurement_directory import *
from ipyfilechooser import FileChooser
from IPython.display import Image
import qgrid
import pandas as pd
from numpy import nan
import json
import numpy as np
import warnings
import matplotlib.cbook
warnings.filterwarnings("ignore", category=matplotlib.cbook.mplDeprecation)


filechooser_widget = FileChooser(os.getcwd())
filechooser_widget.show_only_dirs = True
display(filechooser_widget)
table_viewer = widgets.Output(layout={'border': '1px solid black'})


def get_newest_df(watchfolder, optional_column_names=[], existing_df=None):
    run_ids = []
    files = [filename for filename in os.listdir(watchfolder)]
    files_spe = []
    for file in files:
        if '.spe' in file:
            files_spe.append(file)
        elif 'run_ids.txt' in file:
            run_ids += run_ids_from_txt(
                os.path.abspath(os.path.join(watchfolder, file)))
    if existing_df is None:
        run_ids += run_ids_from_filenames(files_spe)
        df = bc.get_runs_df_from_ids(
            run_ids, optional_column_names=optional_column_names)
    else:
        run_ids = list(set(run_ids_from_filenames(files_spe)).union(set(run_ids)).difference(
            set(list(existing_df['run_id']))))
        if len(run_ids) > 0:
            df = existing_df.append(bc.get_runs_df_from_ids(run_ids,
                                                            optional_column_names=optional_column_names),
                                    sort=False,
                                    ignore_index=True)
        else:
            df = existing_df

    def custom_sort(df):
        # takes in df and returns same df with user-interaction columns first
        #['run_id','badshot','manual_foo1','manual_foo2', 'listboundvar1', etc.]
        cols = list(df.columns)
        manual_cols = []
        for col in cols:
            if 'manual' in col:
                manual_cols += [col]
        manual_cols = sorted(manual_cols)
        user_interact_cols = ['run_id'] + ['badshot'] + manual_cols
        for col in user_interact_cols:
            cols.remove(col)
        return df[user_interact_cols + cols]

    df = custom_sort(df)
    df.sort_values(by='run_id', ascending=False, inplace=True)
    return df


def save_image_log(event, qgrid_widget):
    row_idx = int(event['index'])
    df = qgrid_widget.get_changed_df()
    df_updated_row = df.loc[row_idx]
    updated_row_dict = {}
    for key in df_updated_row.index:
        if key == 'notes':
            continue
        elif key == 'badshot':
            updated_row_dict[key] = bool(df_updated_row.loc[key])
        else:
            if np.isnan(df_updated_row.loc[key]):
                continue  # don't upload nan's to breadboard
            elif isinstance(df_updated_row.loc[key], np.integer):
                updated_row_dict[key] = int(df_updated_row.loc[key])
            elif isinstance(df_updated_row.loc[key], np.float):
                updated_row_dict[key] = float(df_updated_row.loc[key])
            else:
                updated_row_dict[key] = df_updated_row.loc[key]
    run_id = df_updated_row['run_id']
    run_dict = bc._send_message(
        'get', '/runs/' + str(run_id) + '/').json()
    run_dict['notes'] = df_updated_row['notes']
    run_dict['parameters'].update(updated_row_dict)
    payload = json.dumps(run_dict)
#     print(payload)
    resp = bc._send_message('put', '/runs/' + str(run_id) + '/', data=payload)


def load_image_log(watchfolder, optional_column_names=[]):
    try:
        existing_df = load_qgrid.loaded_qgrid.get_changed_df().dropna()
    except:
        existing_df = None
    try:
        if watchfolder != load_image_log.old_watchfolder:
            existing_df = None
            load_qgrid.loaded_qgrid.close()
    except:
        pass
    df = get_newest_df(
        watchfolder, optional_column_names=optional_column_names, existing_df=existing_df)
    load_image_log.old_watchfolder = watchfolder
    # for testing
    # df = bc.get_runs_df_from_ids([219153, 219151],
    #                              optional_column_names=optional_column_names)
    for column in optional_column_names:
        if column not in df.columns:
            df[column] = nan

    col_opts = {'editable': False}
    col_defs = {}
    for col_name in optional_column_names + ['badshot', 'notes']:
        col_defs[col_name] = {'editable': True}
    col_defs['badshot']['ColumnWidth'] = 50
    qgrid_widget = qgrid.show_grid(df, grid_options={'forceFitColumns': False, 'defaultColumnWidth': 100},
                                   column_options=col_opts, column_definitions=col_defs)
    qgrid_widget.on('cell_edited', save_image_log)
    display(qgrid_widget)
    return qgrid_widget


def load_qgrid(b):
    load_qgrid.loaded_qgrid = load_image_log(filechooser_widget.selected_path,
                                             list(optional_columns_widget.options))
    xvars_menu.options = load_qgrid.loaded_qgrid.get_changed_df().columns
    yvars_menu.options = load_qgrid.loaded_qgrid.get_changed_df().columns


load_button = widgets.Button(description='load')
load_button.on_click(load_qgrid)


def refresh_qgrid(b):
    load_qgrid.loaded_qgrid.close()
    load_qgrid(b)


refresh_button = widgets.Button(description='refresh')
refresh_button.on_click(refresh_qgrid)

# def close_qgrid(b):
#     load_qgrid.loaded_qgrid.close()

# close_button = widgets.Button(description='close')
# close_button.on_click(close_qgrid)


def export_qgrid(b):
    df = load_qgrid.loaded_qgrid.get_changed_df()
    df.to_csv(os.path.join(os.path.dirname(filechooser_widget.selected_path),
                           os.path.basename(filechooser_widget.selected_path) + '_params.csv'))


export_button = widgets.Button(description='export')
export_button.on_click(export_qgrid)
# display(widgets.HBox([load_button, refresh_button, close_button, export_button]))
display(widgets.HBox([load_button, refresh_button, export_button]))


optional_columns_widget = widgets.Select(
    options=[],
    description='manual columns',
    disabled=False,
    style={'description_width': 'initial'}
)
textbox = widgets.Text(
    value='',
    description='editable column name',
    disabled=False,
    style={'description_width': 'initial'}
)


add_column_button = widgets.Button(description='add name')


def add_column(button):
    optional_columns = list(optional_columns_widget.options)
    if len(textbox.value) > 0:
        optional_columns = list(set().union(
            ['manual_' + textbox.value], optional_columns))
    optional_columns_widget.options = optional_columns


add_column_button.on_click(add_column)
clear_column_button = widgets.Button(description='clear name')


def clear_column(button):
    optional_columns = list(optional_columns_widget.options)
    if len(optional_columns) > 0:
        optional_columns.pop(0)
    optional_columns_widget.options = optional_columns


clear_column_button.on_click(clear_column)
display(widgets.HBox([optional_columns_widget, textbox,
                      add_column_button, clear_column_button]))


# live plotting
xvars_display = widgets.Select(
    options=[],
    disabled=False,
)

yvars_display = widgets.Select(
    options=[],
    disabled=False,
)

xvars_menu = widgets.Dropdown(
    options=[], description='xvar')
yvars_menu = widgets.Dropdown(
    options=[], description='yvar')

add_plot_button = widgets.Button(description='add (xvar, yvar)')


def add_plot(button):
    xvars, yvars = list(xvars_display.options), list(yvars_display.options)
    xvars.append(xvars_menu.value), yvars.append(yvars_menu.value)
    xvars_display.options, yvars_display.options = xvars, yvars


add_plot_button.on_click(add_plot)
clear_plot_button = widgets.Button(description='clear')


def clear_plot(button):
    xvars, yvars = list(xvars_display.options), list(yvars_display.options)
    xvars.pop(), yvars.pop()
    xvars_display.options, yvars_display.options = xvars, yvars


clear_plot_button.on_click(clear_plot)

VBox_x = widgets.VBox([xvars_menu, xvars_display])
VBox_y = widgets.VBox([yvars_menu, yvars_display])
VBox_buttons = widgets.VBox([add_plot_button, clear_plot_button])
live_plot_HBox = widgets.HBox(
    [VBox_x, VBox_y, VBox_buttons])

# TODO create image preview widget
# image_viewer = widgets.Output(layout={'border': '1px solid black'})
# def show_selected_image(event, qgrid_widget):
#     image_viewer.clear_output()
#     row_idx = int(event['new'][0])
#     df = pd.read_csv(filename)
#     raw_image_filename = df.loc[row_idx, 'filename0']
#     filepath = measurement_dir + '\\' + raw_image_filename.replace('.spe', '.jpg')
#     with image_viewer:
#         if os.path.exists(filepath) and '.jpg' in filepath:
#             pil_img = Image(filepath)
#             display(pil_img)
#         else:
#             display('no jpg preview at ' + filepath)
