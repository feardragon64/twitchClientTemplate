import requests

from oauthclient import OAuthClient
from settings import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET, CHANNEL
from twitchchat import ChatClient
from twitchpubsub import PubSubClient
from twilioclient import TwilioClient


scope = 'chat:read chat:edit channel:read:redemptions communities_edit'


def main():
    """This is a sample of how to use this"""

    # Assumes twitch client redirect url is
    oauth_client = OAuthClient()
    oauth_token = oauth_client.twitch_oauth(
        TWITCH_CLIENT_ID,
        TWITCH_CLIENT_SECRET,
        'borkfeedbot',
        scope,
    )

    twilio_client = TwilioClient()

    chat_client = ChatClient(CHANNEL, oauth_token, twilio_client.bork_feed_text)
    chat_client.connect_to_chat()
    twilio_client.set_callback(chat_client.send_chat_message)

    channel_id = get_channel_id(CHANNEL)
    topics = [
        'community-points-channel-v1.{}'.format(channel_id),
    ]

    pubsub_client = PubSubClient(oauth_token, CHANNEL, topics, twilio_client.bork_feed_text)
    pubsub_client.connect_to_pubsub()


def get_channel_id(channel):
    resp = requests.get(
        'https://api.twitch.tv/kraken/users?login={}'.format(channel),
        headers={
            'Accept': 'application/vnd.twitchtv.v5+json',
            'Client-ID': TWITCH_CLIENT_ID,
            'Content-Type': 'application/json',
        }
    )
    if resp.status_code != 200:
        print("Error getting channel id")
        return 0
    return resp.json()['users'][0]['_id']


if __name__ == '__main__':
    main()
