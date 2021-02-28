#!/usr/bin/env python3
# Use this script to schedule spams with the chatspammer.py script

import os, random, string
from datetime import date, time, datetime

progname = "chatspammer.py"
progpath = os.getcwd()+'/'+progname
basecmd = r'$(which python3) {} --message \"{{}}\" --length {{}} --process {{}} --delay {{}} 2>&1 >> /home/kali/Desktop/spam.log'.format(progpath)
baseaddcmd = '(crontab -l ; echo "{} ({}) & ({})") | crontab -'
basermcmd = 'crontab -l | grep -v {} | crontab -'

def randomstring(l):
    return ''.join([random.choice(string.ascii_letters + string.digits) for i in range(l)])


if not os.path.isfile(progpath):
    print("Can't find the spammer script, please rename it to chatspammer.py and put it in the same directory")
    exit()

msg = input("What message do you want to spam?\n> ")
try:
    day = input("What day do you want to start this spam? (YYYY-MM-DD, leave blank for today)\n> ")
    if day == "":
        day = date.today()
    else:
        day = date.fromisoformat(day)
    t = input("At what time should it start? (HH:MM)\n> ")
    t = time.fromisoformat(t.zfill(5))
    start = datetime.combine(day, t)
except ValueError:
    print("Please enter the date and time in the right format, try again")
    exit()

length = int(input("How long (in minutes) should it last?\n> "))
process = input("How many processes (threads) should it use? (default=1)\n> ")
if process == "":
    process = 1
else:
    process = int(process)
delay = input("Delay between message in second? (to slow down the spam, default=0)\n> ")
if delay == "":
    delay = 0
else:
    delay = float(delay)

print("The following message will be spammed on {} for {} minutes with {} processes:\n  {}".format(
    start.strftime("%x, %X"), length, process, msg))
confirm = input("Press enter to confirm or q to quit ")
if confirm == 'q':
    exit()

progcmd = basecmd.format(msg.replace('"', r'\\\"').replace('!', '"\'!\'"'), length, process, delay)
rmcmd = basermcmd.format(randomstring(6))
crondate = "{} {} {} {} *".format(start.minute, start.hour, start.day, start.month)
os.system(baseaddcmd.format(crondate, rmcmd, progcmd))

print("Done")
