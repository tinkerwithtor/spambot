#!/usr/bin/env python3
# usage: dpspammer.py [-h] --title TITLE --text TEXT --amount AMOUNT
#                [--upvotes UPVOTES] [--process PROCESS]
# 
# DeepPaste spammer by hushneo
# 
# optional arguments:
#   -h, --help         show this help message and exit
#   --title TITLE      Title of the paste
#   --text TEXT        Text of the paste, or path to a txt file (not yet)
#   --amount AMOUNT    Number of pastes to spam before stopping
#   --upvotes UPVOTES  Number of upvotes to add (default: 0)
#   --process PROCESS  Number of processes to use (default: 10)

import requests, random, time, re, json, argparse, builtins, os, string
from base64 import b64encode
from multiprocessing import Process, current_process, Value

############### CONFIG ##############

URL = "http://depastedihrn3jtw.onion/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:68.0) Gecko/20100101 Firefox/68.0"
ANTI_CAPTCHA_API_KEY = "xxx"
ANTI_CAPTCHA_API_URL = "http://api.anti-captcha.com/"

#####################################

proxies = {
    'http':  'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}
changecircuitcounter = 0

md5regex = re.compile(r"MD5-HASH:<br>([^<]+)<br>")

# To display the process name when printing
def print(*args, **kwargs):
    return builtins.print("[{}]".format(current_process().name), *args, **kwargs)

def randomstring(l):
    return ''.join([random.choice(string.ascii_letters + string.digits) for i in range(l)])

# Change socks user to renew identity
def newcircuit():
    global proxies
    user = "dpspam_"+randomstring(6)
    proxies = {
        'http':  'socks5h://{}:{}@127.0.0.1:9050'.format(user, user),
        'https': 'socks5h://{}:{}@127.0.0.1:90s50'.format(user, user)
    }

def getsession():
    global changecircuitcounter
    # We use a new identity every 20 sessions, could be less or more they don't seem to care
    if changecircuitcounter <= 0:
        newcircuit()
        changecircuitcounter = 20
    changecircuitcounter -= 1
    
    s = requests.Session()
    s.proxies = proxies
    s.headers.update({'User-Agent': USER_AGENT})
    # we have to load the home page first to start the session and get the phpsessid cookie
    s.get(URL)
    return s

# Manual method for testing: open captcha.png and enter the code(doesn't work with multiprocess)
def manualsolvecaptcha(s):
    r = s.get(URL+"captcha/captcha.php")
    with open("captcha.png", "wb+") as f:
        f.write(r.content)
    return input("Enter captcha code: ")
    
# Automatic method using anti-captcha API
def solvecaptcha(s):
    r = s.get(URL+"captcha/captcha.php")
    b64 = b64encode(r.content).decode("utf-8")
    
    task = {
        'type': 'ImageToTextTask',
        'body': b64, # the captcha encoded in base64
        # The 3 next params might need to be changed in case they update their captchas
        'numeric': 1, # only digits
        'minLength': 4, # always 4 digits
        'maxLength': 4,
        'websiteURL': 'dp' # optional, to see requests on anticaptcha panel
    }
    data = {
        'clientKey': ANTI_CAPTCHA_API_KEY,
        'task': task
    }
    # Create the task
    r = requests.post(ANTI_CAPTCHA_API_URL+"createTask", proxies=proxies, data=json.dumps(data))
    resp = r.json()
    print(resp)
    if resp["errorId"] != 0:
        print("Captcha error:", resp["errorId"])
        return
    taskid = resp["taskId"]
    
    # Wait then get the result
    time.sleep(5)
    data = {"clientKey": ANTI_CAPTCHA_API_KEY, "taskId": taskid}
    while True:
        r = requests.post(ANTI_CAPTCHA_API_URL+"getTaskResult", proxies=proxies, data=json.dumps(data))
        resp = r.json()
        print(resp)
        if resp["errorId"] != 0:
            print("Captcha error:", resp["errorId"])
            return
        if resp["status"] != "ready":
            time.sleep(2)
            continue
        return resp["solution"]["text"]
        
# Create a new paste, return it's hash or None if it failed
def newpaste(title, text):
    print("Posting the new paste")
    s = getsession()
    # we need to add a random string at the end so it's not rejected for being a duplicate
    text += '\n'*30 + randomstring(6)
    captcha = manualsolvecaptcha(s)
    
    data = {
        'title': title,
        'paste': text,
        'once': 0,
        'captcha_code': captcha
    }
    try:
        r = s.post(URL+"paste.php", data=data)
    except Exception as e:
        print("Maybe server is down, waiting 15 minutes.")
        s.close()
        time.sleep(60*15)
        return
    s.close()

    md5 = md5regex.search(r.text)
    if md5:
        print("success")
        return md5.group(1)
    print("failed to post")

# Some account management functions (to upvote, comment...) 
def loadaccounts():
    accounts = []
    try:
        with open("dpaccounts.txt") as f:
            for line in f:
                a = line.strip().split(":")
                accounts.append((a[0], a[1]))
    except FileNotFoundError:
        pass
        
    print("Loaded", len(accounts), "accounts")
    return accounts

def saveaccounts(accounts):
    with open("dpaccounts.txt", "w+") as f:
        for a in accounts:
            f.write(':'.join(a)+'\n')
    print("Saved", len(accounts), "accounts")
    
def createaccount():
    print("Creating a new account")
    username = randomstring(6)
    password = randomstring(6)
    s = getsession()
    captcha = solvecaptcha(s)
    data = {
        'username': username,
        'password': password,
        'captcha_code': captcha   
    }
    r = s.post(URL+"account.php?register", data=data)

    if len(r.history) > 0 and r.history[0].status_code == 302:
        print("Success")
        return (username, password), s
    s.close()
    print(r.text)
    print("Fail")

# Login and returns the logged in session
def login(account):
    s = getsession()
    captcha = solvecaptcha(s)
    data = {
        'username': account[0],
        'password': account[1],
        'captcha_code': captcha   
    }
    r = s.post(URL+"account.php", data=data)
    return s

# Upvote the paste with hash 'md5', adding 1000 to it's score on top.php
def upvote(md5, s):
    r = s.get(URL+"show.php", params={'md5': md5, 'vote': 'up'})
    if len(r.history) > 0 and r.history[0].status_code == 302:
        print("Upvoted", md5)
        return True
    print("Upvote of", md5, "failed")
    return False

# Raise the score on top.php for each pastes in the list
def raisescore(pastes, amount):
    nbuvpoted = 0
    accounts = loadaccounts()
    while nbupvoted < amount:
        if len(accounts) > nbupvoted: # We already have an account
            a = accounts[nbupvoted]
            session = login(a)
        else: # We need to create a new one
            a, s = createaccount()
            if a:
                accounts.append(a)
            else:
                continue
        
        print("Upvoting with account", account[0])
        nbupvoted += 1
        for p in pastes:
            # We try to upvote 2 times
            if not upvote(p, session) and not upvote(p, session):
                # account is burned we can remove it
                accounts.remove(a)
                break
            time.sleep(0.5) # wait 1 sec between each pastes
    saveaccounts(accounts) # save the updated list of accounts

def spam(title, text, nbposted, nbtopost, upvotes=False, exception=False):
    print("Starting")
    pastes = []
    try:
        while nbposted.value < nbtopost:
            # Post the new paste, retry if it failed
            md5 = None
            while not md5:
                md5 = newpaste(title, text)
            pastes.append(md5)
            # Once it's posted, increase the nbposted number, shared by all processes
            with nbposted.get_lock():
                nbposted.value += 1
        # Now everything is posted, we can raise the score so they're first in /top.php
        if upvotes:
            raisescore(pastes, upvotes)
    except Exception as e: # If there is any problem, restart the spam
        print("Error, restarting:", e)
        spam(title, text, nbposted, nbtopost, upvotes, True)

def main():
    settings = args()
    title = settings.title
    if os.path.isfile(settings.text):
        with open(text) as f:
            text = f.read()
    else:
        text = settings.text
    nbposted = Value('i', 0)
    nbtopost = settings.amount
    upvotes = settings.upvotes

    for i in range(settings.process):
        p = Process(target=spam, args=(title, text, nbposted, nbtopost, upvotes))
        p.start()
        time.sleep(0.5)

def args():
    parser = argparse.ArgumentParser(description='DeepPaste spammer by hushneo')
    parser.add_argument('--title', required=True, help="Title of the paste")
    parser.add_argument('--text', required=True, 
        help="Text of the paste, or path to a txt file")
    parser.add_argument('--amount', required=True, type=int,
        help="Number of pastes to spam before stopping")
    parser.add_argument('--upvotes', default=0, type=int, 
        help="Number of upvotes to add (default: 0)")
    parser.add_argument('--process', default=10, type=int, 
        help="Number of processes to use (default: 10)")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit()
