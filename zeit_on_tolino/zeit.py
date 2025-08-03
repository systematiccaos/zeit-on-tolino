import logging
import glob
import os
import time
import random
from pathlib import Path
from typing import Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from zeit_on_tolino.env_vars import EnvVars, MissingEnvironmentVariable
from zeit_on_tolino.web import Delay

ZEIT_LOGIN_URL = "https://epaper.zeit.de/abo/diezeit"
ZEIT_DATE_FORMAT = "%d.%m.%Y"
ZEIT_SSO_TOKEN_NAME = "zeit_sso_201501"

BUTTON_TEXT_TO_RECENT_EDITION = "ZUR AKTUELLEN AUSGABE"
BUTTON_TEXT_DOWNLOAD_EPUB = "EPUB FÜR E-READER LADEN"
BUTTON_TEXT_EPUB_DOWNLOAD_IS_PENDING = "EPUB FOLGT IN KÜRZE"

log = logging.getLogger(__name__)

def _accept_cookies(webdriver: WebDriver) -> None:
    """
    Try to accept cookies on the current page using common selectors.
    """
    cookie_selectors = [
        # Common cookie banner selectors
        "[id*='cookie'] button",
        "[class*='cookie'] button",
        "[data-testid*='cookie'] button",
        "button[id*='accept']",
        "button[class*='accept']",
        "button[aria-label*='accept']",
        "button[aria-label*='Accept']",
        ".cookie-consent button",
        ".cookie-banner button",
        ".consent-banner button",
        "#cookie-consent button",
        "#cookie-banner button",
        ".gdpr-consent button",
        ".privacy-banner button",
        "button:contains('Accept')",
        "button:contains('Akzeptieren')",
        "button:contains('Zustimmen')",
        "button:contains('OK')",
        ".cmp-intro_acceptAll",
        ".sp_choice_type_11",  # Common consent management platform
        "[title*='Accept']",
        "[title*='Akzeptieren']",
        # Specific sites
        ".fc-cta-consent",  # Funding Choices
        ".qc-cmp2-summary-buttons button",  # Quantcast
        ".didomi-continue-without-agreeing",  # Didomi
        ".message-button-accept",
        "[data-role='acceptAll']",
        "[data-cy='accept-all']"
    ]
    
    try:
        # Wait a bit for cookie banners to load
        time.sleep(1.5)
        
        for selector in cookie_selectors:
            try:
                # Try to find and click cookie accept button
                if ":contains(" in selector:
                    # Handle text-based selectors differently (need to use JavaScript for text content)
                    text = selector.split(":contains('")[1].split("')")[0]
                    buttons = webdriver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        if text.lower() in button.text.lower():
                            if button.is_displayed() and button.is_enabled():
                                button.click()
                                log.info(f"Accepted cookies using text: {text}")
                                return
                else:
                    elements = webdriver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            log.info(f"Accepted cookies using selector: {selector}")
                            return
            except Exception:
                continue
                
    except Exception as e:
        log.debug(f"Could not accept cookies: {e}")


def _simulate_browsing_history(webdriver: WebDriver, num_sites: int = 3) -> None:
    """
    Visit a few random websites to create browsing history before logging into ZEIT.
    This makes the session appear more natural.
    """
    log.info("Creating fake browsing history...")
    
    # List of innocuous websites to visit
    sites = [
        "https://www.wikipedia.org",
        "https://www.bbc.com/news",
        "https://www.reuters.com",
        "https://www.dw.com",
        "https://www.spiegel.de",
        "https://www.tagesschau.de",
        "https://www.sueddeutsche.de",
        "https://www.faz.net",
        "https://www.google.com",
        "https://www.youtube.com"
    ]
    
    # Randomly select sites to visit
    selected_sites = random.sample(sites, min(num_sites, len(sites)))
    
    for site in selected_sites:
        try:
            log.info(f"Visiting {site} for browsing history...")
            webdriver.get(site)
            
            # Accept cookies if present
            _accept_cookies(webdriver)
            
            # Random delay between 2-5 seconds to simulate reading
            delay = random.uniform(2.0, 5.0)
            time.sleep(delay)
            
            # Optionally scroll a bit to simulate user interaction
            webdriver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            log.warning(f"Could not visit {site}: {e}")
            continue
    
    log.info("Fake browsing history created")


def _simulate_zeit_browsing(webdriver: WebDriver) -> None:
    """
    Browse ZEIT website briefly before going to login page.
    This creates a more natural user journey.
    """
    log.info("Browsing ZEIT website before login...")
    
    # Visit main ZEIT page first
    webdriver.get("https://www.zeit.de")
    
    # Accept cookies on ZEIT
    _accept_cookies(webdriver)
    
    time.sleep(random.uniform(2.0, 4.0))
    
    # Scroll a bit
    webdriver.execute_script("window.scrollTo(0, document.body.scrollHeight/4);")
    time.sleep(random.uniform(1.0, 2.0))
    
    # Maybe visit an article or section
    try:
        # Look for article links
        article_links = webdriver.find_elements(By.CSS_SELECTOR, "a[href*='/zeit/']")
        if article_links:
            # Click on a random article (but don't wait too long if it's paywalled)
            random_article = random.choice(article_links[:5])  # Only consider first 5 links
            random_article.click()
            time.sleep(random.uniform(3.0, 6.0))
    except Exception as e:
        log.info(f"Could not browse ZEIT articles: {e}")
    
    log.info("ZEIT browsing simulation complete")

def _set_token_cookie(webdriver: WebDriver):
    token = os.environ[EnvVars.ZEIT_SSO_TOKEN]
    cookie_name = ZEIT_SSO_TOKEN_NAME
    domain = ".zeit.de"
    webdriver.add_cookie({"name": cookie_name, "value": token, "domain": domain})

def _get_credentials() -> Tuple[str, str]:
    try:
        username = os.environ[EnvVars.ZEIT_PREMIUM_USER]
        password = os.environ[EnvVars.ZEIT_PREMIUM_PASSWORD]
        return username, password
    except KeyError:
        raise MissingEnvironmentVariable(
            f"Ensure to export your ZEIT username and password as environment variables "
            f"'{EnvVars.ZEIT_PREMIUM_USER}' and '{EnvVars.ZEIT_PREMIUM_PASSWORD}'. For "
            "Github Actions, use repository secrets."
        )


def _login(webdriver: WebDriver) -> None:
    _simulate_browsing_history(webdriver, num_sites=random.randint(2, 10))
        
    # Browse ZEIT specifically before login
    _simulate_zeit_browsing(webdriver)
    username, password = _get_credentials()
    webdriver.get(ZEIT_LOGIN_URL)

    username_field = webdriver.find_element(By.ID, "username")
    username_field.send_keys(username)
    password_field = webdriver.find_element(By.ID, "password")
    password_field.send_keys(password)
    
    # Wait for Friendly Captcha to complete and login button to be enabled
    def captcha_and_button_ready(driver):
        try:
            # Check if Friendly Captcha is present and completed
            captcha_completed = False
            try:
                # Look for Friendly Captcha widget
                captcha_widget = driver.find_element(By.CSS_SELECTOR, ".frc-captcha")
                captcha_state = captcha_widget.get_attribute("data-state") or captcha_widget.get_attribute("class")
                log.info(f"Friendly Captcha state: {captcha_state}")
                
                # Captcha is completed when state is "completed" or similar
                captcha_completed = ("completed" in str(captcha_state).lower() or 
                                   "solved" in str(captcha_state).lower() or
                                   "success" in str(captcha_state).lower())
                
                if not captcha_completed:
                    log.info("Waiting for Friendly Captcha to complete...")
                    return False
                    
            except Exception:
                # If no captcha found, assume it's not required or already completed
                log.info("No Friendly Captcha found, proceeding...")
                captcha_completed = True
            
            # Check login button state
            button = driver.find_element(By.ID, "kc-login")
            is_present = button is not None
            is_displayed = button.is_displayed()
            is_enabled = button.is_enabled()
            not_disabled = button.get_attribute("disabled") is None
            
            button_ready = is_present and is_displayed and is_enabled and not_disabled
            
            log.info(f"Captcha completed: {captcha_completed}, Button ready: {button_ready}")
            
            return captcha_completed and button_ready
            
        except Exception as e:
            log.info(f"Error checking captcha/button state: {e}")
            return False
    
    # Wait for both captcha completion and login button to be ready (2 minutes timeout)
    log.info("Waiting for Friendly Captcha to complete and login button to be enabled...")
    WebDriverWait(webdriver, 60).until(captcha_and_button_ready)
    
    # Now click the button
    login_button = webdriver.find_element(By.ID, "kc-login")
    login_button.click()
    log.info("Login button clicked after captcha completion")

    time.sleep(60)

    # Check if login failed by looking at URL
    if "anmelden" in webdriver.current_url:
        raise RuntimeError("Failed to login, check your login credentials.")

    # Wait for successful login - look for elements that appear after login
    WebDriverWait(webdriver, Delay.large).until(EC.presence_of_element_located((By.CLASS_NAME, "page-section-header")))

def _get_latest_downloaded_file_path(download_dir: str) -> Path:
    download_dir_files = glob.glob(f"{download_dir}/*")
    latest_file = max(download_dir_files, key=os.path.getctime)
    return Path(latest_file)


def wait_for_downloads(path):
    time.sleep(Delay.small)
    start = time.time()
    while any([filename.endswith(".part") for filename in os.listdir(path)]):
        now = time.time()
        if now > start + Delay.large:
            raise TimeoutError(f"Did not manage to download file within {Delay.large} seconds.")
        else:
            log.info(f"waiting for download to be finished...")
            time.sleep(2)


def download_e_paper(webdriver: WebDriver) -> str:
    # _login(webdriver)
    webdriver.get(ZEIT_LOGIN_URL)
    time.sleep(Delay.small)
    _set_token_cookie(webdriver=webdriver)
    webdriver.get(ZEIT_LOGIN_URL)


    time.sleep(Delay.small)
    for link in webdriver.find_elements(By.TAG_NAME, "a"):
        if link.text == BUTTON_TEXT_TO_RECENT_EDITION:
            link.click()
            break

    if BUTTON_TEXT_EPUB_DOWNLOAD_IS_PENDING in webdriver.page_source:
        raise RuntimeError("New ZEIT release is available, however, EPUB version is not. Retry again later.")
    log.info('looking for download button')
    time.sleep(Delay.small)
    for link in webdriver.find_elements(By.TAG_NAME, "a"):
        log.info(f"found button: {link.text}")
        if link.text == BUTTON_TEXT_DOWNLOAD_EPUB:
            log.info("clicking download button now...")
            link.click()
            break

    wait_for_downloads(webdriver.download_dir_path)
    e_paper_path = _get_latest_downloaded_file_path(webdriver.download_dir_path)

    if not e_paper_path.is_file():
        raise RuntimeError("Could not download e paper, check your login credentials.")

    return e_paper_path
