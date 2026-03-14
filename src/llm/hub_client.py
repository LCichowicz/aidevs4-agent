from typing import Any
import requests

from src import config

class HubClient:
    def __init__(self) -> None:
        self.base_url = config.AI_DEVS_BASE_URL.rstrip("/")
        self.api_key = config.AI_DEVS_API
        self.timeout = 15


    def build_data_url(self, relative_path: str) -> str:
        normalized = relative_path.lstrip("/")
        return f"{self.base_url}/data/{self.api_key}/{normalized}"
    

    def post_json(self, relative_path:str, payload: dict[str,Any])-> Any:
        normalized = relative_path.lstrip("/")

        url = f"{self.base_url}/{normalized}"

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise RuntimeError(f"Problem with posting {relative_path} : {e}")

        if not response.ok:
            raise RuntimeError(f"Problem with posting {relative_path} : {response.status_code} | body: {response.text}")
        

        try: 
            return response.json()
        except ValueError:
            raise RuntimeError("JSON returned corrupted")


    def get_person_locations(self, name:str, surname: str):
        '''
        Returns raw JSON response from /api/location endpoint.
        '''
        payload = {
            "apikey": self.api_key,
            "name" : name,
            "surname": surname
        }

        response = self.post_json('api/location', payload)
        return response
    
    def get_access_level(self, name:str, surname:str, birth_year: int)->dict:
        '''
        Returns raw JSON response from /api/accesslevel endpoint.
        '''
        payload = {
            "apikey": self.api_key,
            "name": name,
            "surname": surname,
            "birthYear" : birth_year
        }

        response = self.post_json("api/accesslevel", payload)
        return response

    def download_text(self, relative_path:str)-> str:
        url = self.build_data_url(relative_path)
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to download {url}: {e}")
        return response.text
    
    def download_bytes(self, relative_path:str)-> bytes:
        url = self.build_data_url(relative_path)

        try:
            response =requests.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to download {url}: {e}")
        return response.content
    
    def submit(self, task:str, answer: Any)-> dict:
        url = "verify"
        payload = {
                "apikey":self.api_key,
                "task" : task,
                "answer": answer
                   }

    
        response = self.post_json(url, payload)
        return response