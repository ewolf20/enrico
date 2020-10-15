ECHO Starting enrico...
:: activate conda environment
CD /d C:\Users\Fermi1\anaconda3\Scripts
CALL activate.bat

CD /d D:\Fermidata1\enrico
START python image_watchdog.py
ECHO image_watchdog.py started in a new window
START python analysis_logger.py
ECHO analysis_logger.py started in a new window
PAUSE