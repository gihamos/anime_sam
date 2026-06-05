from pydantic import BaseModel,Field
from typing import Optional,Any
from models.contents import Content,Etat

class Catalogue(BaseModel):
    name:str
    synopsis: Optional[str]=None
    aperçu:Optional[str]=None
    genres: list[str] = Field(default_factory=list)
    etat:Etat=Etat.EN_COURS
    contenus:Optional[list[Content]]=None
    metadata:Optional[dict[str,Any]]=None
    