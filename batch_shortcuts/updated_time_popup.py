import time
import datetime

now = datetime.datetime.now()
print('time last updated: ' + now.strftime("%a %b %d, %H:%M:%S")) #%b , %H:%M:%S
time.sleep(600)
