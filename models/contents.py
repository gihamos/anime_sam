from pydantic import BaseModel
from typing import Optional,Any
from enum import Enum


class Etat(str,Enum):
    TERMINE=0
    EN_COURS=1
    ABONNDONNE=-1

class TypeContent(str,Enum):
    EPISODE="episode"
    SEASON="season"
    FILM="film"
    MANGA="manga"
    ANIME="anime"
    AUTRE="autre"
    

class Content(BaseModel):
    name:str
    type:TypeContent
    metadata:Optional[dict[str,Any]]=None
    
class Video(BaseModel):
    
       videoid: Optional[str]=None
       videosrc:Optional[str] =None
class Episode(Content):
    numepisode: Optional[int]
    data:Optional[list[Video]]
    type:TypeContent=TypeContent.EPISODE
 
class Film(Content):  
    data:Optional[list[Video]]
    type:TypeContent=TypeContent.FILM

class Season(Content):
    lang:Optional[list[str]]=None
    type: TypeContent=TypeContent.SEASON
    data: list[Episode]
 
    
class Anime(Content):
    type:TypeContent=TypeContent.ANIME
    seasons:Optional[list[Season]]

class MangaImage(BaseModel):
    page:Optional[int]
    link:Optional[str]

class MangaChapitre(Content):
    images:Optional[list[MangaImage]]
    
    

class Scan(Content):
    lang:Optional[list[str]]
    Chapitres:Optional[list[MangaChapitre]]

