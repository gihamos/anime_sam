from pydantic import BaseModel
from typing import Optional
from enum import Enum


class TypeContent(str,Enum):
    EPISODE="episode"
    SEASON="season"
    MANGA="manga"
    AUTRE="autre"
    




class Content(BaseModel):
    name:str
    type:TypeContent
    metadata:Optional[dict[str,any]]
    
    
class Episode(Content):
    numero: Optional[int]
    link: Optional[str]
    type:TypeContent=TypeContent.EPISODE
    

class Season(Content):
    lang:Optional[list[str]]
    type: TypeContent=TypeContent.SEASON
    data: list[Episode]
 
    


class Image(BaseModel):
    page:Optional[int]
    link:Optional[str]

class Chapitre(Content):
    images:Optional[list[Image]]
    
    

class Scan(Content):
    lang:Optional[list[str]]
    Chapitres:Optional[list[Chapitre]]

