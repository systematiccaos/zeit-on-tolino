import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Union
import os

from selenium.webdriver import Chrome, ChromeOptions, Firefox, FirefoxOptions
from selenium.webdriver.firefox.webdriver import WebDriver

DOWNLOAD_PATH = tempfile.TemporaryDirectory().name


@dataclass
class Delay:
    small: int = 3
    medium: int = 10
    large: int = 30
    xlarge: int = 200


def get_webdriver(download_path: Union[Path, str] = DOWNLOAD_PATH) -> WebDriver:
    # options = ChromeOptions()
    if not os.path.exists(download_path):
        os.mkdir(download_path)
    options = FirefoxOptions()
    prefs = {"download.default_directory" : f"{download_path}/"}
    # options.add_experimental_option("prefs",prefs)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.dir", f"{download_path}/")
    # options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36")
    options.add_argument("--headless")
    webdriver = Firefox(options=options)
    setattr(webdriver, "download_dir_path", str(download_path))
    return webdriver
