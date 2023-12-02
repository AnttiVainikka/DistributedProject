from messages.messages import *
from messages.message_sender import send_message
from application.commands import *
import log

_logger = log.getLogger(__name__)

def process_message(message: BaseMessage):
    if message.header == MessageHeader.ApplicationMessage.value:
        _process_application_message(message)
    else:
        pass # TODO: 

def _process_application_message(message: ApplicationMessage):
    _logger.info(f"Received application message {type(message).__name__}: {message.__dict__}")
    if False: # TODO: Me master?
        send_message(message)
    else:
        match message.command_type:
            case CommandType.Stop.value:
                stop_media(message.media_timestamp)

            case CommandType.Resume.value:
                resume_media(message.media_timestamp)

            case CommandType.JumpToTimestamp.value:
                jump_to_timestamp(message.media_timestamp, message.destination_timestamp)
