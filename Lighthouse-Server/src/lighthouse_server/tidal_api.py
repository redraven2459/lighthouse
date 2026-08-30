from http.server import *
from urllib import parse
import json, subprocess, time, threading, secrets, base64, hashlib, os, time, random

import requests

import lighthouse_server.tasks as tasks
from lighthouse_server.settings import Settings
from lighthouse_server.tasks import TaskHandler, TaskStatusCode

# OAuth Handler
class TidalOAuthCallbackHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    parsed = parse.urlparse(self.path)
    if parsed.path == "/callback":
      params = parse.parse_qs(parsed.query)
      if "code" in params:
          self.server.auth_code = params["code"][0]
          self.send_response(200)
          self.send_header("Content-Type", "text/html")
          self.end_headers()
          self.wfile.write(
              b"<h1>Login complete</h1><p>You can close this window.</p>"
          )
      else:
          self.send_response(400)
          self.end_headers()
          self.wfile.write(b"Missing authorization code")

  def log_message(self, format, *args):
    # Silence server logs
    pass

class TidalOAuthServer(HTTPServer):
    def __init__(self, server_address, handler_class):
        super().__init__(server_address, handler_class)
        self.auth_code = None


class TidalAPI():
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self.settings = Settings()

        self.auth_code = None
        self.access_token = None
        self.refresh_token = None
        self.token_lock = threading.Lock()
        self.api_lock_background = threading.Lock()
        self.api_lock_foreground = threading.Lock()
        self.nextQueryTime_background = time.time()
        self.nextQueryTime_foreground = time.time()

        # Try read the access and refresh token
        try:
            with open(self.settings.tidal_api_tokens_path, "r") as file:
                data = json.load(file)
                try:
                    self.access_token = data["access_token"]
                except Exception:
                    pass
                try:
                    self.refresh_token = data["refresh_token"]
                except Exception:
                    pass
        except Exception:
            pass

    def getAccessToken(self, task_id, forceRefresh = False):
        with self.token_lock:
            if (self.access_token == None) or (forceRefresh == True):
                self._doAuth(task_id)
                data = {"access_token": self.access_token, "refresh_token": self.refresh_token}
                with open(self.settings.tidal_api_tokens_path, 'w') as file:
                    json.dump(data, file)
            return self.access_token

    @staticmethod
    def _getRandom32OctetSequenceString():
        sequence = str(secrets.randbits(8))
        for x in range(31):
            sequence = sequence + " " + str(secrets.randbits(8))
        return sequence

    @staticmethod
    def _base64urlencode(raw):
        data = (base64.b64encode(raw)).decode("ascii")
        data = data.split('=')[0]
        data = data.replace('+', '-')
        data = data.replace('/', '_')
        return data

    @staticmethod
    def _convertSequenceStringToRaw(string):
        return bytes(map(int, string.split()))

    @staticmethod
    def _getCodeChallengeInfo():
        # As per RC-7636
        string = TidalAPI._getRandom32OctetSequenceString()
        code_verifier = TidalAPI._base64urlencode(TidalAPI._convertSequenceStringToRaw(string))
        code_challenge = TidalAPI._base64urlencode(hashlib.sha256(bytes(code_verifier, 'ascii')).digest())
        return [code_verifier, code_challenge]

    @staticmethod
    def _createRequestString(client_id, redirect_url, scopes, code_challenge, state):
        request_string = "https://login.tidal.com/authorize?response_type=code"
        request_string = request_string + "&client_id=" + client_id
        request_string = request_string + "&redirect_uri=" + redirect_url
        request_string = request_string + "&scope=" + scopes
        request_string = request_string + "&code_challenge_method=S256"
        request_string = request_string + "&code_challenge=" + code_challenge
        request_string = request_string + "&state=" + state
        return request_string

    def _retrieveAuthCode(self):
        server = TidalOAuthServer(("0.0.0.0", self.settings.tidal_api_redirect_port), TidalOAuthCallbackHandler)
        while server.auth_code == None:
            server.handle_request()
        self.auth_code = server.auth_code
        return

    def _refreshAccessToken(self):
        pass

    def _doAuth(self, task_id):
        if self.settings.tidal_api_client_id == "":
            raise RuntimeError("tidal_api_client_id has not been set")
        redirect_url = "http://" + str(self.settings.tidal_api_redirect_address) + ":" + str(self.settings.tidal_api_redirect_port) + "/callback"
        redirect_url_safe = parse.quote(redirect_url, safe='')
        self.access_token = None

        if self.refresh_token == None:
            # Create code_verifier / code_challenge
            code_verifier, code_challenge = TidalAPI._getCodeChallengeInfo()

            # Complete oAuth flow to get authorization code
            request_string = self._createRequestString(self.settings.tidal_api_client_id, redirect_url_safe, self.settings.tidal_api_scopes, code_challenge, self.settings.country_code)
            threading.Thread(target=self._retrieveAuthCode, daemon=True).start()

            # Pass auth address data to API
            TaskHandler().update_task_data_field(task_id, tasks.tidal_api_auth_address, request_string)
            TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_TIDAL_API_AUTH)

            # Wait for auth_code
            while self.auth_code is None:
                time.sleep(0.5)

            # Exchange auth_code for tokens
            data = {"grant_type": "authorization_code", "client_id": self.settings.tidal_api_client_id, "code": self.auth_code, "redirect_uri": redirect_url, "code_verifier": code_verifier}
            r = requests.post("https://auth.tidal.com/v1/oauth2/token", data=data)
            self.access_token = r.json()["access_token"]
            try:
                self.refresh_token = r.json()["refresh_token"]
            except Exception:
                self.refresh_token = None
        else:
            data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token, "client_id": self.settings.tidal_api_client_id}
            r = requests.post("https://auth.tidal.com/v1/oauth2/token", data=data)
            self.access_token = r.json()["access_token"]

        # Reset auth address data for API
        TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
        TaskHandler().update_task_data_field(task_id, tasks.tidal_api_auth_address, "")
        return

    def processRequest(self, task_id, r, strict=True):
        try:
            match r.status_code:
                case 200:
                    TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
                    return True

                case 401:
                    data = r.json()
                    if data["errors"][0]["detail"] == "Expired token":
                        self.getAccessToken(task_id, forceRefresh=True)
                    else:
                        raise RuntimeError("getQuery() was provided with a response that could not be handled. The responses' status code was: " + str(r.status_code) + ". The responses' text was: " + r.text)

                case 404:
                    if strict == False:
                        return True
                    else:
                        raise RuntimeError("getQuery() was provided with a 404 response when configured with strict=True. The responses' status code was: " + str(r.status_code) + ". The responses' text was: " + r.text)

                case _:
                    raise RuntimeError("getQuery() was provided with a response that could not be handled. The responses' status code was: " + str(r.status_code) + ". The responses' text was: " + r.text)

        except Exception as e:
            raise RuntimeError("getQuery() was provided with a response that could not be interpreted. Error: " + str(e))
        return False

    def getQueryBackground(self, task_id, query, strict=True):
        TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_TIDAL_API_LOCK_BACKGROUND)
        with self.api_lock_background:
            TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
            max_retries = 3
            attempt = 0
            while attempt <= max_retries:
                # Rate limit queries
                if time.time() < self.nextQueryTime_background:
                    time.sleep(self.nextQueryTime_background - time.time())

                # Perform request
                get_headers = {"Authorization": ("Bearer " + self.getAccessToken(task_id))}
                url = "https://openapi.tidal.com/v2/" + query
                r = None
                r = requests.get(url, headers=get_headers)

                # Reset rate limit timer
                self.nextQueryTime_background = time.time() + random.uniform(3, 13)

                # Process request
                if self.processRequest(task_id, r, strict=strict):
                    return r.status_code, r.json()

                attempt = attempt + 1
                continue

    def getQueryForeground(self, task_id, query, strict=True):
        TaskHandler().update_task_status_code(task_id, TaskStatusCode.WAITING_FOR_TIDAL_API_LOCK_FOREGROUND)
        with self.api_lock_foreground:
            TaskHandler().update_task_status_code(task_id, TaskStatusCode.ACCEPTED)
            max_retries = 3
            attempt = 0
            while attempt <= max_retries:
                # Rate limit queries
                if time.time() < self.nextQueryTime_foreground:
                    time.sleep(self.nextQueryTime_foreground - time.time())

                # Perform request
                get_headers = {"Authorization": ("Bearer " + self.getAccessToken(task_id))}
                url = "https://openapi.tidal.com/v2/" + query
                r = None
                r = requests.get(url, headers=get_headers)

                # Reset rate limit timer
                self.nextQueryTime_foreground = time.time() + random.uniform(0.1, 0.3)

                # Process request
                if self.processRequest(task_id, r, strict=strict):
                    return r.status_code, r.json()

                attempt = attempt + 1
            print("Task: " + str(task_id) + " is releasing api_lock_foreground")
