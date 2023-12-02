from messages.messages import *
import log

_logger = log.getLogger(__name__)

def send_message(message: BaseMessage):
    if message.header == MessageHeader.ApplicationMessage.value:
        _send_application_message(message)
    else:
        pass # TODO: ...

def _send_application_message(message: ApplicationMessage):
    _logger.debug(f"Sending application message {type(message).__name__}: {message.__dict__}")
    if False: # TODO: Me master?
        pass # TODO: Check conditions, broadcast message, etc.
    else:
        pass # TODO: Send message to master
