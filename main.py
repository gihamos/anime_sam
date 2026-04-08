from fastapi import FastAPI
from utils.logger import logger


logger.info(msg="Demarage de l'application")


app = FastAPI(
    title="anime sama API",
    version="1.0",
)

@app.get("/")
def home():
    return {"message": "api fonctionnel"}







