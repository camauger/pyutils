import time

import schedule

schedule.every().friday.at("18:00").do(send_report)

while True:
    schedule.run_pending()
    time.sleep(60)
