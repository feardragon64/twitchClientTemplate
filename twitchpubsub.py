import json
import _thread as thread
import threading
import websocket


class PubSubClient(threading.Thread):
    def __init__(self, token, user_id, topics, on_event_fn):
        self.token = token
        self.user_id = user_id
        self.topics = topics
        self.on_event_fn = on_event_fn
        # Sample topics: [
        #     'channel-bits-events-v2.{}'.format(self.user_id),
        #     'channel-subscribe-events-v1.{}'.format(self.user_id),
        #     'channel-points-channel-v1.{}'.format(self.user_id)
        # ]
        uri = "wss://pubsub-edge.twitch.tv"
        self.ws = websocket.WebSocketApp(
            uri,
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, msg: self.on_error(ws, msg),
            on_close=lambda ws: self.on_close(ws),
            on_open=lambda ws: self.on_open(ws))

    def connect_to_pubsub(self):
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        print("Starting pubsub websocket")
        self.ws.run_forever()

    def on_open(self, ws):
        def run(*args):
            # Subscribe to relevant pubsub topics
            listen = {
                'type': 'LISTEN',
                'data': {
                    'topics': self.topics,
                    'auth_token': self.token
                }
            }
            print(listen)
            ws.send(json.dumps(listen))
            threading.Timer(20.0, self.ping).start()

        thread.start_new_thread(run, ())

    def handle_whisper(self, message):
        print("Got whisper")
        sender = message['tags']['display_name']
        text = message['body']
        print("Whisper sender: {}, chat: {}".format(sender, text))

    def handle_sub(self, message):
        print("Got sub")
        tier = self._determine_sub_tier(message.get('sub_plan', '?'))
        if message['context'] == 'subgift' or message['context'] == 'anonsubgift':
            # sub was gifted
            display_name = message.get('display_name', 'Anonymous')
            receiver = message['recipient_display_name']
            chat = None
            print("Gifted sub, gifter: {}, receiver: {}, {}, chat: {}", display_name, receiver, tier, chat)
        else:
            chat = message['sub_message']['message']
            display_name = message.get('display_name', 'Anonymous')
            if message['context'] == 'resub':
                # returning sub message
                months = message.get(
                    'cumulative_months',
                    message.get('streak_months', message.get('months', 'some'))
                )
                print("Resub, user: {}, months: {}, {}, chat: {}", display_name, months, tier, chat)
            else:
                # brand new sub
                print("New sub, user: {}, {}, chat: {}", display_name, tier, chat)

    def _determine_sub_tier(self, sub_plan):
        if sub_plan == 'Prime':
            return 'prime'
        return 'T{}'.format(sub_plan[0])

    def handle_bits(self, message):
        print("Got bits")
        user = message['data'].get('user_name', 'Anonymous')
        user = user if user is not None else 'Anonymous'
        bits = message['data']['bits_used']
        dollar_value = '${}'.format(int(bits) / 100)
        chat = message['data']['chat_message']
        print("Bits donator: {}, money {}, chat {}".format(user, dollar_value, chat))

    def handle_points_redeem(self, message):
        user = message['redemption']['user']['display_name']
        reward = message['redemption']['reward']['title']
        print("User {} redeemed {}".format(user, reward))
        if 'Feed the BORK' in reward:
            print("BORK FEED!")
            self.on_event_fn()

    def on_message(self, ws, message):
        f = open('debug_pubsub_messages.txt', 'a+')
        f.write(message)
        f.close()

        r = json.loads(message)
        if r.get('type') == 'PONG':
            # Not a message we need to handle
            return
        if r.get('type') == 'RESPONSE':
            if r.get('error') == 'ERR_BADAUTH':
                # Failed to auth
                print('Failed to Auth for Pub Sub')
                print(r)
                self.close()
            return

        if r.get('type') != 'MESSAGE' or r.get('type' == 'reward-redeemed'):
            # Not a message we need to handle
            print("Got a non message: {}".format(r.get('type')))
            return

        topic = r['data']['topic']
        m2 = json.loads(r['data']['message'])
        if 'whispers' in topic:
            if m2['type'] == 'whisper_received':
                self.handle_whisper(json.loads(m2['data']))
        elif 'channel-bits-events' in topic:
            self.handle_bits(m2)
        elif 'channel-subscribe-events' in topic:
            self.handle_sub(m2)
        elif 'channel-points-channel' in topic:
            self.handle_points_redeem(m2['data'])
        elif 'community-points-channel' in topic:
            self.handle_points_redeem(m2['data'])
        else:
            # Not a message we need to handle
            print(message)
            return

    def on_error(self, ws, error):
        print("Pubsub error")
        print(error)

    def on_close(self, ws):
        print("Pubsub connection closed")

    def close(self):
        self.ws.close()

    def ping(self):
        self.ws.send(json.dumps({'type': 'PING'}))
        threading.Timer(280.0, self.ping).start()
