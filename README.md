# EpicMusicPlayer
This is a prototype peer-to-peer, synchronized music player. You can create a lobby, and
others (who have your IP address) can join.

## Requirements
* Python 3.10 with Tkinter support
* VLC client libraries (from e.g. system VLC installation)
* A shared network, with no firewall or NAT box blocking incoming and outgoing messages

You'll also need several Python libraries. They can be installed with pip:
```
pip install -r requirements.txt
```
Remember to use pip for correct version of Python!

## Usage
The application should be launched from root of this repository:

```
python src/main.py
```

After that, the GUI should open. Once you have entered a nickname
(any name, really), you can either host your own lobby or join an existing one.

For local testing, add `l` as the command-line argument. This repository
includes a few (royalty-free) music samples.