import sys
from net.lobby import NetLobby


lobby = NetLobby()

if sys.argv[1] == 'new':
    lobby.create_lobby()
elif sys.argv[1] == 'join':
    lobby.join_lobby(sys.argv[2])

while True:
    lobby.handle_msg()