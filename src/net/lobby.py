from net.lobby_message_implementation import LobbyMessageImplementation
from net.lobby_health_check_implementation import LobbyHealthCheckImplementation
from net.lobby_leader_election_implementation import LobbyLeaderElectionImplementation

class NetLobby(LobbyMessageImplementation, LobbyHealthCheckImplementation, LobbyLeaderElectionImplementation):
    """
    Main class for creating and managing a lobby.

    The NetLobby class serves as the main entity for creating and managing a lobby. It handles
    communication between the members of the lobby. For detailed information about the lobby,
    please refer to the documentation or implementation details.
    """
    pass