from pydantic import BaseModel
from typing import Optional
from models.contents import Content

class Catalogue(BaseModel):
    name:str
    synopsis: Optional[str]
    aperçu:Optional[str]
    genres: list[str]=[]
    contenus:Optional[list[Content]]
    