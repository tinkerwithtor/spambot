# Spambot
A collection of spammer scripts for deep web onion services.

## Prerequisites
* _Python_ version > 3.8
* _Tor_ running in the background

## Usage

### Chat Spammer
To launch the chat spambot type the following command:
```
./scheduler.py
```
or
```
python3 scheduler.py
```
Follow the interactive prompt and press enter to confirm. The more threads you spawn, the more msgs the spammer will send out; refer to your computer (processor) specs to see what is the maximum number of threads supported and beware not to cause a DOS attack to the website.

### Deep Paste Spammer
To use Deep Paste spammer, here's how

```
./dpsammer.py --title STRING --text STRING --amount STRING --upvotes NUMBER --process NUMBER_THREADS
```
or

```
python3 dpsammer.py --title STRING --text STRING --amount STRING --upvotes NUMBER --process NUMBER_THREADS
```

## Troubleshooting

If the website is down, the script will halt and wait 15 minutes. If the URL changes, just edit the corresponding string in the script.
