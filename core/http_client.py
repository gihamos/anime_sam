import httpx

class HTTPClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10)

    async def get(self, url: str):
        response = await self.client.get(url)
        response.raise_for_status()
        return response.text

http_client = HTTPClient()