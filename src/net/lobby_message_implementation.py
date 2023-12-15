from net.base_lobby import BaseLobby, Peer

from messages.messages import *

import log

_logger = log.getLogger(__name__)

class LobbyMessageImplementation(BaseLobby):
    """
    General Lobby Messages Implementation for the BaseLobby.

    This class extends the BaseLobby and provides the General Lobby Message implementation.
    It specifically implements the abstract methods related to lobby management, including:
    
        - _process_request_join
        - _process_request_new_member
        - _process_new_member
        - _process_member_accept
        - _process_leave
        - _process_member_left
    """
    def __init__(self):
        super().__init__()

    def _process_request_join(self, msg: RequestJoinMessage):
        """
        Process the received RequestJoinMessage within the lobby.

        This method is responsible for processing the received RequestJoinMessage within
        the lobby. When a client wants to join the lobby, it sends this message. If the
        leader receives this message, it is immediately processed. If a non-leader member
        receives it, the message is propagated to the leader for further processing.

        Parameters:
        - msg (RequestJoinMessage): The RequestJoinMessage received from a client.
        """
        if self.is_leader():
            self._process_request_new_member(RequestNewMemberMessage(self._identity, msg.name, msg.sender))
        else:
            _logger.debug(f'Forwarding new member request to leader')
            self.send_to(self._leader, RequestNewMemberMessage(self._identity, msg.name, msg.sender))

    def _process_request_new_member(self, msg: RequestNewMemberMessage):
        """
        Process the received RequestNewMemberMessage within the lobby.

        This method is specifically designed to handle the RequestNewMemberMessage, which
        can only be received by the leader. The RequestNewMemberMessage is sent by another
        lobby member when that member receives a RequestJoinMessage and propagates it to the leader.

        Parameters:
        - msg (RequestNewMemberMessage): The RequestNewMemberMessage received from another lobby member.
        """
        # Generate a unique id for the new member
        new_member_id = self._generate_random_id()

        # Broadcast the new member
        self.broadcast(NewMemberMessage(self._identity, msg.name, msg.new_member_address, new_member_id))
        
        # Add the new member
        address = msg.new_member_address.split(':')
        self._add_member(Peer(address[0], address[1], msg.name, new_member_id, False, True))
        
        # Send an acceptance message for the new member 
        self.send_to(msg.new_member_address,
                     MemberAcceptMessage(self._identity,
                                         {address: member.__dict__ for address, member in self._members.items()}))

        self._raise_event(self.EVENT_NEW_MEMBER, msg.new_member_address)
        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)

    def _process_new_member(self, msg: NewMemberMessage):
        """
        Process the received NewMemberMessage within the lobby.

        This method is responsible for handling the NewMemberMessage, which is sent by the leader
        to all members of the lobby. The purpose of this message is to notify all members that a
        new member has successfully joined the lobby.

        Parameters:
        - msg (NewMemberMessage): The NewMemberMessage received from the lobby leader.
        """
        # Leader is telling us about the new member
        _logger.debug(f'New lobby member: {msg.new_member_address}')
        address = msg.new_member_address.split(':')
        self._add_member(Peer(address[0], address[1], msg.name, msg.new_member_id, False, True))

    def _process_member_accept(self, msg: MemberAcceptMessage):
        """
        Process the received MemberAcceptMessage within the lobby.

        This method is responsible for handling the MemberAcceptMessage, which is sent to a
        client after requesting to join the lobby. The MemberAcceptMessage contains the necessary
        information for the client to initialize itself within the lobby.

        Parameters:
        - msg (MemberAcceptMessage): The MemberAcceptMessage received by a joining client.
        """
        # Update my own member list
        for ip_address, member in msg.members.items():
            member = Peer(**member)
            if ip_address != self._identity:
                self._members[ip_address] = member
                if self._members[ip_address].is_leader:
                    self._leader = ip_address
            else:
                self._me.id = member.id

        # Start health check
        self._start_health_check()

        self._raise_event(self.EVENT_MEMBERS_CHANGED, self._members, self._identity, self._leader)
        _logger.debug(f'Joined lobby, I am {self._identity}, with id {self._me.id} (leader: {self._leader})')

    def _process_leave(self, msg: LeaveMessage):
        """
        Process the received LeaveMessage within the lobby.

        This method handles the LeaveMessage, which can be initiated by either the leader or a
        member when they decide to leave the lobby. If the leader receives this message, it
        immediately removes the client from the lobby and broadcasts the leaving information to
        all remaining members. If a member receives this message from the leader, it initiates
        a leader election procedure within the lobby.

        Parameters:
        - msg (LeaveMessage): The LeaveMessage received from a client.
        """
        if msg.sender in self._members:
            _logger.debug(f'{msg.sender} has left the lobby')
            if self.is_leader():
                self._remove_member(self._members[msg.sender])
                self.broadcast(MemberLeftMessage(self._identity, msg.sender))
            elif self._leader == msg.sender:
                self._start_leader_election()

    def _process_member_left(self, msg: MemberLeftMessage):
        """
        Process the received MemberLeftMessage within the lobby.

        This method handles the MemberLeftMessage, which is received from the leader when a
        member has just left the lobby. The purpose of this message is to notify all members
        about the departure of a specific member.

        Parameters:
        - msg (MemberLeftMessage): The MemberLeftMessage received from the lobby leader.
        """
        self._remove_member(self._members[msg.member_address])