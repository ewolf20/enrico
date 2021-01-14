:again
:: A hacky way of doing a while True loop in Windows batch language
ECHO updating time now.

TIMEOUT /t 2 /nobreak
START python updated_time_popup.py
GOTO again