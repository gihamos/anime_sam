from core.http_client import http_client
from params import BASE_SAMA_URL

async def fetch_page(path: str):
    url = f"{BASE_SAMA_URL}{path}"
    return await http_client.get(url)