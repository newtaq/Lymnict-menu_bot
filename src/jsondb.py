import json 
from typing import Any 

class jsonfile:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.open()
        
        
    def open(self):
        try:
            with open(self.filename, encoding="utf-8") as rfile:
                return json.load(rfile) 
        except FileNotFoundError:
            self.write()
            self.open()
            
    def write(self, __data: Any = None): 
        with open(self.filename, "w", encoding="utf-8") as wfile:
            try: 
                json.dump(__data, wfile)
            except Exception as ex: 
                return ex 
            else: 
                return True 
    
    def __call__(self) -> None:
        return self.open()
                
    @property
    def data(self):
        return self.open()
    
    @data.setter 
    def data(self, __data: Any):
        self.write(__data)
        
#############################

usersdb = jsonfile(r"databases\usersdb.json")
orgsdb = jsonfile(r"databases\orgsdb.json")
