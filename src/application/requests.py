from messages.messages import *
from messages.message_sender import send_message

def request_stop(current_timestamp: int):
    send_message(StopMessage(current_timestamp))

def request_resume(current_timestamp: int):
    send_message(ResumeMessage(current_timestamp))

def request_jump_to_timestamp(current_timestamp: int, destination_timestamp: int):
    send_message(JumpToTimestampMessage(current_timestamp, destination_timestamp))
