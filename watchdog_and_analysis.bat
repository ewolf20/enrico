ECHO Starting enrico...
:: activate conda environment
CALL <anaconda_dir>/Scripts/activate.bat

CD /d <enrico_dir>
START python image_watchdog.py
ECHO image_watchdog.py started in a new window
START python analysis_logger.py
ECHO analysis_logger.py started in a new window
PAUSE