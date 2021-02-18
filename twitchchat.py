import json
import re
import _thread as thread
import threading
import websocket


class ChatClient(threading.Thread):
    def __init__(self, username, token, on_event_fn):
        self.username = username.strip().lower()
        self.token = token
        self.stage = None
        self.on_event_fn = on_event_fn
        uri = "wss://irc-ws.chat.twitch.tv:443"
        self.ws = websocket.WebSocketApp(
            uri,
            on_message=lambda ws, msg: self.on_message(ws, msg),
            on_error=lambda ws, msg: self.on_error(ws, msg),
            on_close=lambda ws: self.on_close(ws),
            on_open=lambda ws: self.on_open(ws))

    def connect_to_chat(self):
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        print("Starting chat websocket")
        self.ws.run_forever()

    def on_open(self, ws):
        def run(*args):
            # Auth with chat as broadcaster
            self.ws.send('PASS oauth:{}'.format(self.token))
            self.ws.send('NICK {}'.format(self.username))
            threading.Timer(20.0, self.ping).start()

        thread.start_new_thread(run, ())

    def on_message(self, ws, message):
        if not self.stage:
            if ':tmi.twitch.tv 001' in message:
                self.stage = 'logged_in'
                self.ws.send('CAP REQ :twitch.tv/tags')
                self.ws.send('CAP REQ :twitch.tv/commands')
                self.ws.send('JOIN #{}'.format(self.username))
        else:
            self.parse_message(message)

    def parse_message(self, message):
        f = open('debug_chat_messages.txt', 'a+')
        f.write(message)
        f.close()

        s_message = message.split(' ')
        message_index = 0
        tags = {}

        if s_message[0] == 'PING':
            # Ignore pings
            return
        if s_message[message_index][0] == '@':
            # This message has tags
            tags_str = s_message[0][1:].split(';')
            for tag in tags_str:
                if '=' in tag:
                    kv = tag.split('=')
                    tags[kv[0]] = kv[1] if len(kv) > 1 else ''
            message_index += 1
            if tags.get('msg-id') == 'raid':
                # This is a raid message
                print("Got raid")
                raider = tags.get('msg-param-displayName', 'Someone')
                viewers = tags.get('msg-param-viewerCount', 'unknown number of')
                self.handle_raid(raider, viewers)
            elif tags.get('system-msg') is not None and 'gifting' in tags.get('system-msg'):
                print("Found sub gifts")
                # Subs being gifted
                gifter = tags.get('display-name')
                number = tags.get('system-msg').split('\s')[3]
                print(tags.get('system-msg'))
                print(number)
                print(gifter)
                if int(number) > 1:
                    # Let pubsub handle if it's just a single sub gift
                    self.handle_gifted_sub(gifter, int(number))
        message_index += 1
        if s_message[message_index] == 'PRIVMSG':
            # Found something broadcast to chat
            if s_message[0] == ':jtv!jtv@jtv.tmi.twitch.tv' and 'now hosting you' in message:
                # Channel is being hosted
                print("Got host")
                message_index += 2
                hoster = s_message[message_index][1:]
                viewers = 0
                r1 = re.search('up to (\d+) viewers', message)
                if r1 and len(r1.groups()):
                    viewers = r1.groups()[0]
                self.handle_host(hoster, viewers)
            else:
                # "Normal chat message"
                user = tags.get('display-name')
                chat_split = message.split('PRIVMSG #{} :'.format(self.username))
                chat = '' if len(chat_split) < 2 else chat_split[1]
                self.handle_chat(user, chat)

    def handle_chat(self, user, chat):
        print("{}: {}".format(user, chat))

    def handle_gifted_sub(self, gifter, number):
        print("{} gifted {} subs".format(gifter, number))
        if number >= 20:
            print("BORK FEED!")
            self.on_event_fn()

    def handle_host(self, hoster, viewers):
        print("Host from {} for {} viewers".format(hoster, viewers))

    def handle_raid(self, raiders, viewers):
        print("Raid from {} for {} viewers".format(raiders, viewers))

    def send_chat_message(self, message):
        print("Sending chat message in {}: {}".format(self.username, message))
        self.ws.send('PRIVMSG #{} :{}'.format(self.username, message))

    def on_error(self, ws, error):
        print("Chat client error")
        print(error)

    def on_close(self, ws):
        print("Chat connection closed")

    def close(self):
        self.ws.close()

    def ping(self):
        self.ws.send(json.dumps({'type': 'PING'}))
        threading.Timer(280.0, self.ping).start()
