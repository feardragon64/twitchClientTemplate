import time

from settings import TWILIO_SID, TWILIO_AUTH, TWILIO_SENDER, TWILIO_RECEIVER
from twilio.rest import Client


class TwilioClient():

    def __init__(self):
        self.sid = TWILIO_SID
        self.auth = TWILIO_AUTH
        self.sender = TWILIO_SENDER
        self.client = Client(self.sid, self.auth)
        self.callback = None

    def set_callback(self, callback):
        self.callback = callback

    def send_text(self, message, number):
        self.client.messages.create(
            body=message,
            from_=self.sender,
            to=number,
        )

    def bork_feed_text(self):
        self.send_text('BORK FEED TIME!', TWILIO_RECEIVER)
        if self.callback is not None:
            time.sleep(2)
            self.callback('Bork feed detected. Summoning feardragon.')
