from pydantic import BaseModel
from typing import Optional
from enum import Enum


class TypeContent(str,Enum):
    EPISODE="episode"
    SEASON="season"
    FILM="film"
    MANGA="manga"
    AUTRE="autre"
    

class Content(BaseModel):
    name:str
    type:TypeContent
    metadata:Optional[dict[str,any]]
    
class Video(BaseModel):
       videoid: Optional[str]
       videosrc:Optional[str] 
class Episode(Content):
    numepisode: Optional[int]
    data:Optional[Video]
    type:TypeContent=TypeContent.EPISODE
 
class Film(Content):  
    data:Optional[Video]
    type:TypeContent=TypeContent.FILM

class Season(Content):
    lang:Optional[list[str]]
    type: TypeContent=TypeContent.SEASON
    data: list[Episode]
 
    


class MangaImage(BaseModel):
    page:Optional[int]
    link:Optional[str]

class MangaChapitre(Content):
    images:Optional[list[MangaImage]]
    
    

class Scan(Content):
    lang:Optional[list[str]]
    Chapitres:Optional[list[MangaChapitre]]

