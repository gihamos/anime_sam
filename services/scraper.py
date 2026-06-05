from core.http_client import http_client
from params import BASE_SAMA_URL
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options 
from typing import Optional,Any
from utils.logger import logger
from selenium.webdriver.support import expected_conditions as EC
from services.parsers import Parser
from models.catalogue import Catalogue
from models.contents import TypeContent
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

def search_anime(name: str) -> Optional[list[dict[str, Any]]]:
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
        time.sleep(1)
        driver.quit()
        return Parser.parse_anime_search_url_catalogue(html)

    except Exception as e:
        logger.exception("Erreur lors de la recherche du contenu")
        return None



def getcatalogue(catalogue_url_sama:str)->Optional[Catalogue]:
    try:
        # comment: 
        driver = creer_driver()
        wait = WebDriverWait(driver, TIMEOUT)
        driver.get(catalogue_url_sama)
        time.sleep(2)
        
        if driver.title in "Accès Introuvable.":
            return None
        data=driver.find_element(By.CSS_SELECTOR,"#sousBlocMiddle")
        html=data.get_attribute("outerHTML")
    
        driver.quit()
        
        catalogue=Parser.parse_catalogue(html)
        
        #obtenir les saisons
        
                
        
        
        return catalogue
        
    except Exception as e:
        logger.exception("Erreur lors de la recherche du contenu")
        return None
    # end try



import asyncio
from playwright.async_api import async_playwright

async def extract_all_episodes(url_saison: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Charger la saison UNE SEULE FOIS
        await page.goto(url_saison, timeout=60000)

        # Nombre d'épisodes
        options = await page.locator("#selectEpisodes option").all_text_contents()
        total = len(options)
        print(f"Total épisodes : {total}")

        results = {}

        for ep in range(1,7 ): #remplacer second paramètre par total + 1
            print(f"Épisode {ep}...")

            # Sélectionner l’épisode
            await page.select_option("#selectEpisodes", label=f"Episode {ep}")
            await page.wait_for_timeout(150)

            # Récupérer les noms des lecteurs
            lecteurs = await page.locator("#selectLecteurs option").all_text_contents()

            ep_data = []

            for i, lecteur_nom in enumerate(lecteurs):
                # Sélectionner le lecteur
                await page.select_option("#selectLecteurs", index=i)
                await page.wait_for_timeout(150)

                # Lire l’URL embed du player
                player_url = await page.locator("#playerDF").get_attribute("src")

                ep_data.append({
                    "lecteur": lecteur_nom.strip(),
                    "player_url": player_url
                })

            results[ep] = ep_data

        await browser.close()
        return results


def run_scraper():
    url = "https://anime-sama.to/catalogue/naruto/saison1/vostfr/"
    data = asyncio.run(extract_all_episodes(url))
    print(data)













if __name__ == "__main__":
    print(getcatalogue("https://anime-sama.to/catalogue/dragon-ball/") )
    #run_scraper()
    #from utils.fonction import build_video_url
    #print(build_video_url("Sibnet", "video.sibnet.to", "4963284"))


    