import requests
import uuid
import webbrowser
import time


class OAuthClient:
    def __init__(self):
        pass

    def do_oauth(self, site, uri, client_id, client_secret, uniqueid, extra_params=None):
        callback = 'https://feardragon.com/webhook/twitchv2'
        state = uuid.uuid1()
        browser_url = '{}/authorize?client_id={}&redirect_uri={}&response_type=code&state={}'.format(uri, client_id, callback, state)
        if extra_params:
            for key in extra_params:
                print(extra_params)
                browser_url = "{}&{}={}".format(browser_url, key, extra_params[key])

        webbrowser.open(browser_url)
        time.sleep(1)

        # Try for 30 seconds
        timeout = 30
        code = None
        while code is None and timeout > 0:
            print("Checking for oauth code, state: {}".format(uniqueid))
            resp = requests.get("{}?state={}".format(callback, state))
            if resp.status_code != 200:
                timeout -= 1
                time.sleep(1)
            else:
                code = resp.json()['code']

        token = ''
        if code is not None:
            data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': callback
            }
            resp = requests.post('{}/token'.format(uri), data=data, timeout=10)
            if resp.status_code == 200:
                token = resp.json()['access_token']
                print("Oauth'd with {}".format(site))
            else:
                print("Failed to oauth with {} step 2".format(site))
        else:
            print("Failed to oauth with {} step 1".format(site))

        return token

    def check_twitch_token_expired(self, token):
        if not token:
            return True
        resp = requests.get('https://id.twitch.tv/oauth2/validate', headers={'Authorization': 'OAuth {}'.format(token)})
        if resp.status_code != 200:
            return True
        return False

    def twitch_oauth(self, client_id, client_secret, uniqueid, scope):
        params = {'scope': scope}
        self.TWITCH_OAUTH_TOKEN = self.do_oauth('twitch', 'https://id.twitch.tv/oauth2', client_id, client_secret, uniqueid, params)

        return self.TWITCH_OAUTH_TOKEN
