import qgrid
import pandas as pd
import time

df = pd.DataFrame({'col1': ['test1', 'test2'], 'col2': [3, 7]})
qgrid_widget = qgrid.show_grid(df)
display(qgrid_widget)
time.sleep(10)
qgrid_widget.get_changed_df()
