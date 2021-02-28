#!/usr/bin/env python3
# usage: chatspammer.py [-h] --message M [--length L] [--processes P]
#
# Chat spammer by hushneo
#
# optional arguments:
#   -h, --help     show this help message and exit
#   --message M    Message to spam
#   --length L     Length of the spam in minutes (0 for infinite)
#   --delay D    Delay in seconds between messages to slow down the spam (default: no delay)
#   --processes P  Number of processes (threads) to use

from multiprocessing import Process, current_process
import requests, re, time, random, string, argparse
from datetime import datetime, timedelta

############### CONFIG ##############

URL_KISET = "http://tetatl6umgbmtv27.onion/"
URL_ABLEONION = "http://notbumpz34bgbz4yfdigxvd6vzwtxc3zpt5imukgl6bvip2nikdmdaad.onion/rchat/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:68.0) Gecko/20100101 Firefox/68.0"

#####################################

proxies = {
    'http':  'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}
changecircuitcounter = 0

# kiset regexes
idregex = re.compile(r"action='\.\?wtd=([^']+)' id='Wt-form'")
joinsignalregex = re.compile(r'name="([^"]+)" type="submit" tabindex="1"')
msgsignalregex = re.compile(r'name="([^"]+)" type="submit" tabindex="2"')
msgfieldregex = re.compile(r'name="([^"]+)" size="10" type="text"')

# ableonion regexes
ableidregex = re.compile("name=h value=([^>]+)")


def randomstring(l):
    return ''.join([random.choice(string.ascii_letters + string.digits) for i in range(l)])

# Change socks user to renew identity
def newcircuit():
    global proxies
    user = "dpspam_"+randomstring(5)
    proxies = {
        'http':  'socks5h://{}:{}@127.0.0.1:9050'.format(user, user),
        'https': 'socks5h://{}:{}@127.0.0.1:9050'.format(user, user)
    }

def getsession():
    global changecircuitcounter
    # We use a new identity every 20 sessions
    if changecircuitcounter <= 0:
        newcircuit()
        changecircuitcounter = 20
    changecircuitcounter -= 1
    
    s = requests.session()
    s.proxies = proxies
    s.headers.update({'User-Agent': USER_AGENT})
    return s

# Send message on ableonion
def sendableonion(message):
    s = getsession()
    try:
        r = s.get(URL_ABLEONION, stream=True)
    except Exception as e:
        print("[{}] Error: {}".format(current_process().name, e))
        s.close()
        return
        
    data = ""
    chatid = None
    for c in r.iter_content(decode_unicode=True):
        data += c
        if not "</form>" in data:
            continue
        # We received the id, let's extract it
        chatid = ableidregex.search(data)
        if not chatid:
            return
        chatid = chatid.group(1)
        # We extracted chatid, now we can send the message
        time.sleep(1)
        try:
            r = s.get(URL_ABLEONION, params={'m': message, 'h': chatid}, stream=True)
        except Exception as e:
            print("[{}] Couldn't send message: {}".format(current_process().name, e))
            s.close()
            return
        #print("[{}] Message sent".format(current_process().name))
        return

# Send message on kiset
def sendkiset(message):
    s = getsession()
    # We fetch a chatid and the signal needed to join it
    try:
        r = s.get(URL_KISET)
    except Exception as e:
        print("[{}] Error: {}".format(current_process().name, e))
        s.close()
        return
    chatid = idregex.search(r.text).group(1)
    signal = joinsignalregex.search(r.text).group(1)

    # We refresh the chat every second until someone join
    files = {
        'request': (None, 'page'),
        'wtd': (None, chatid), 
        signal: (None, "")
    }
    page = ""
    #print("[{}] Waiting for someone to join".format(current_process().name))
    while not "Say hello" in page:
        r = s.post(URL_KISET, params={'wtd': chatid}, files=files)
        page = r.text
        time.sleep(1)
    
    # Now we can retrieve the "send" signal and send the message 
    signal = msgsignalregex.search(page).group(1)
    msgfield = msgfieldregex.search(page).group(1)
    files = {
        'request': (None, 'page'), 
        'wtd': (None, chatid), 
        msgfield: (None, message), 
        signal: (None, "")
    }
    try:
        r = s.post(URL_KISET, files=files)
    except Exception as e:
        print("[{}] Couldn't send message: {}".format(current_process().name, e))
        s.close()
        print("Maybe server is down, waiting 15 minutes")
        time.sleep(60*15)
        return
    s.close()
    
    if message in r.text:
        pass
        #print("[{}] Message sent".format(current_process().name))
    else:
        print("[{}] Fail".format(current_process().name))


def spamableonion(message, stop, delay):
    print("[{}] Starting...".format(current_process().name))
    try:
        while (stop and datetime.now() < stop) or not stop:
            sendableonion(message)
            if delay:
                time.sleep(delay)
    except KeyboardInterrupt:
        return
    except Exception as e: # If there is any problem, restart the spam
        print("[{}] Error, restarting: {}".format(current_process().name, e))
        spamableonion(message)

def spamkiset(message, stop, delay):
    print("[{}] Starting...".format(current_process().name))
    try:
        while (stop and datetime.now() < stop) or not stop:
            sendkiset(message)
            if delay:
                time.sleep(delay)
    except KeyboardInterrupt:
        return
    except Exception as e: # If there is any problem, restart the spam
        print("[{}] Error, restarting: {}".format(current_process().name, e))
        spamkiset(message)

def main():
    settings = args()
    if settings.length != 0:
        stop = datetime.now() + timedelta(minutes=settings.length)
    else:
        stop = False
    for i in range(settings.process):
        p = Process(target=spamkiset, args=(settings.message, stop, settings.delay), name="kiset-"+str(i+1))
        p.start()
        ps = Process(target=spamableonion, args=(settings.message, stop, settings.delay), name="ableonion-"+str(i+1))
        ps.start()
        time.sleep(0.5)
    print("Everything is running, ctrl+c to stop")

def args():
    parser = argparse.ArgumentParser(description='Chat spammer by hushneo')
    parser.add_argument('--message', required=True, metavar='M', help="Message to spam")
    parser.add_argument('--length', default=0, type=int, metavar='L',
        help="Length of the spam in minutes (0 for infinite)")
    parser.add_argument('--delay', default=0, type=float, metavar='D',
        help="Delay in seconds between messages to slow down the spam (default: no delay)")
    parser.add_argument('--process', default=1, type=int, metavar='P',
        help="Number of processes (threads) to use")
    return parser.parse_args()

if __name__ == "__main__":
    main()
