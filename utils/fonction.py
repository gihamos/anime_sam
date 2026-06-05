import re
from urllib.parse import urlparse
import httpx
import asyncio

def extract_domain(url: str) -> str:
    host = urlparse(url).netloc
    return host.replace("www.", "")


def extract_hosting_name(url: str) -> str:
    u = url.lower()

    # Vidmoly (toujours embed-xxxx.html)
    if "embed-" in u and u.endswith(".html"):
        return "Vidmoly"

    # Sibnet (toujours videoid=xxxx)
    if "videoid=" in u:
        return "Sibnet"

    # Doodstream (toujours /e/ + contient dood)
    if "/e/" in u and "dood" in u:
        return "Doodstream"

    # Vmeas (toujours /e/ mais sans dood)
    if "/e/" in u and "dood" not in u:
        return "Vmeas"

    return "Inconnu"



def extract_video_id(url: str) -> str | None:
    patterns = [
        r"embed-([a-zA-Z0-9]+)\.html",  # Vidmoly
        r"videoid=(\d+)",              # Sibnet
        r"/e/([a-zA-Z0-9]+)",          # Doodstream / Vmeas
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


async def resolve_new_domain(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        try:
            r = await client.get(url)
            final_domain = r.url.host
            return final_domain.replace("www.", "")
        except Exception:
            # fallback : domaine original
            return urlparse(url).netloc.replace("www.", "")
        

async def resolve_hosting_info(url: str) -> dict:
    hosting = extract_hosting_name(url)
    domain = await resolve_new_domain(url)
    return {
        "hosting": hosting,
        "domain": domain,
        "url": url
    }


def build_video_url(platform: str, domain: str, video_id: str) -> str:
    platform = platform.lower()

    # Vidmoly
    if platform == "vidmoly":
        return asyncio.run(resolve_new_domain( f"https://{domain}/embed-{video_id}.html"))

    # Sibnet
    if platform == "sibnet":
        return asyncio.run(resolve_new_domain(f"https://{domain}/shell.php?videoid={video_id}"))

    # Doodstream
    if platform == "doodstream":
        return asyncio.run(resolve_new_domain(f"https://{domain}/e/{video_id}"))

    # Vmeas
    if platform == "vmeas":
        return asyncio.run(resolve_new_domain(f"https://{domain}/e/{video_id}"))

    # fallback
    return f"https://{domain}/{video_id}"



