FROM python:3.11-slim


RUN apt-get update && apt-get upgrade -y
RUN python -m pip install --upgrade pip
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["python","main.py"]