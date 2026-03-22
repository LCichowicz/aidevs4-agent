import requests
from src import config




class ZmailClient:
    def __init__(self) -> None:
        self.mail_url   = f"{config.AI_DEVS_BASE_URL.rstrip('/')}/api/zmail"
        self.api_key    = config.AI_DEVS_API
        self.timeout    = 15


    def _post(self, payload: dict)-> dict:
        

        try:
            response = requests.post(self.mail_url, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise RuntimeError(f"HTTP request failed: {e}") from e
        
        if not response.ok:
            raise RuntimeError(f"Problem with posting  : {response.status_code} | body: {response.text}")
        

        try:
            return response.json()
        except ValueError:
            raise RuntimeError(f"Response is not valid JSON. Raw body: {response.text[:300]}")


    def help(self, page: int=1) -> dict:
        payload = {
            "apikey" : self.api_key,
            "action" : "help",
            "page"   : page
        }

        response = self._post(payload)
        return response
    

    def get_inbox(self, page: int= 1, perPage: int = 20) -> dict :
        payload = {
            "apikey" : self.api_key,
            "action" : "getInbox",
            "page"   : page,
            "perPage": perPage
        }
            
        response = self._post(payload)
        return response
    
    def search(self, query: str, page: int=1, perPage: int = 20)-> dict:
        payload = {
            "apikey": self.api_key,
            "action": "search",
            "query": query,
            "page": page,
            "perPage": perPage,
        }
        
        return self._post(payload)
    
    def get_thread(self, thread_id: int)-> dict:
        payload = {
            "apikey": self.api_key,
            "action": "getThread",
            "threadID": thread_id,
        }
        response = self._post(payload)
        return response
    
    def get_messages(self, ids)-> dict:
        payload = {
            "apikey": self.api_key,
            "action": "getMessages",
            "ids": ids,
        }     

        response = self._post(payload)
        return response
    
    def reset(self) -> dict:
        payload = {
            "apikey": self.api_key,
            "action": "reset",
        }
        response = self._post(payload)
        return response