import time

import schedule

from email_report import send_report

schedule.every().friday.at("18:00").do(send_report)

while True:
    schedule.run_pending()
    time.sleep(60)
