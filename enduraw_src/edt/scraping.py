"""
| Module used to scrape results of 'L'Etape du Tour 2024'
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def init_driver():
    """
    Initialize a Chrome webdriver
    """

    ##Set options
    options = Options()
    options.add_argument("--headless")  # do not display webpage
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    ##Go to athlete detailed results webpage
    driver = webdriver.Chrome(options=options)

    return driver


if __name__ == "__main__":
    driver = init_driver()
