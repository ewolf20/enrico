:again
:: A hacky way of doing a while True loop in Windows batch language
ECHO updating time now.
START w32tm /resync
CD C:\Users\FermiCam2\Desktop\GitHub\enrico\batch_shortcuts
START python updated_time_popup.py
TIMEOUT /t 14400 /nobreak
GOTO again