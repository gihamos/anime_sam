from core.http_client import http_client
from params import BASE_SAMA_URL
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options 
from typing import Optional
from utils.logger import logger
from selenium.webdriver.support import expected_conditions as EC
from services.parsers import Parser
import time

TIMEOUT=15
async def fetch_page(path: str):
    url = f"{BASE_SAMA_URL}{path}"
    return await http_client.get(url)




def creer_driver():
    options = Options()
    # masque le navigateur
    #options.add_argument("--headless=new")   # version moderne du headless
    #options.add_argument("--disable-gpu")
    #options.add_argument("--window-size=1920,1080")
    
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_argument("--start-maximized")
    return  webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()),options=options)

def search_anime(name: str) -> Optional[list[dict[str, any]]]:
    try:
        driver = creer_driver()
        wait = WebDriverWait(driver, TIMEOUT)

        driver.get(BASE_SAMA_URL)
        time.sleep(2)

        # Champ de recherche desktop
        champ_recherche = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "div.asn-desktop-search input[name='search_text']")
            )
        )

        champ_recherche.clear()
        champ_recherche.send_keys(name)
        time.sleep(1)

        # Résultats desktop
        results_container = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "#asn-result-desktop"))
        )

        cards = results_container.find_elements(By.CSS_SELECTOR, "#asn-result-mobile")
        html = results_container.get_attribute("outerHTML")
        return Parser.parse_anime_search_url_catalogue(html)

    except Exception as e:
        logger.exception("Erreur lors de la recherche du contenu")
        return None

   

if __name__ == "__main__":
    print(search_anime("naruto") )
    