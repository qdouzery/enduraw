"""
| Module used to scrape results of 'L'Etape du Tour 2024'
"""

import os
import time
import polars as pl
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


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


def close_cookies(driver):
    """
    Close cookies button
    """

    button_cookies = driver.find_element(
        By.CSS_SELECTOR, "#onetrust-close-btn-container > button"
    )
    button_cookies.click()


def load_all_results(driver):
    """
    Load all results
    (only first 10 athletes are displayed when going on the webpage)
    """

    try:
        while True:
            ##Wait for new results to be loaded
            time.sleep(2)

            ##Click on "CHARGER PLUS" button
            try:
                button_load_more = driver.find_element(
                    By.CSS_SELECTOR,
                    "#root > div.app > div.app__content > div.page-body > div > div > div > div > div > div:nth-child(2) > div > div.view-more-list > div.view-more-list__footer > a",
                )
                button_load_more.click()

            ##Reach end of results
            except NoSuchElementException:
                print("All results are loaded.")
                break

    except Exception as e:
        print(f"Error: {e}")


def download_results(driver):
    """
    Download all results
    """

    ##Find all athletes
    athletes = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located(
            (
                By.CSS_SELECTOR,
                "#root > div.app > div.app__content > div.page-body > div > div > div > div > div > div:nth-child(2) > div > div.view-more-list > div:nth-child(1) > div",
            )
        )
    )

    ##Iterate through athletes
    data = []
    for athlete in athletes:
        ##Get athlete personal data
        result = athlete.find_element(By.CLASS_NAME, "event-home__rank").text  # ranking
        aux_bib = athlete.find_element(By.CLASS_NAME, "event-home__bib")
        bib = aux_bib.find_element(By.CLASS_NAME, "event-home__result").text  # bib
        url = athlete.find_element(By.TAG_NAME, "a").get_attribute(
            "href"
        )  # url of detailed results
        name = athlete.find_element(By.TAG_NAME, "a").text  # name
        aux_name = athlete.find_element(By.CLASS_NAME, "event-home__person")
        info = aux_name.find_element(
            By.CLASS_NAME, "event-home__info"
        ).text  # age & sex
        time_race = athlete.find_element(
            By.CLASS_NAME, "event-home__finish"
        ).text  # race time

        ##Aggregate data
        data.append([result, name, time_race, bib, info, url])

    ##Create a dataframe that contains all results
    df_results = pl.DataFrame(
        data, schema=["result", "name", "time", "bib", "info", "url"], orient="row"
    )

    return df_results


def preprocess_results(df_results):
    """
    Preprocessing of results:
        - Format names (lowercase + remove whitespaces)
        - Convert race time from string to time object
        - Extract age and sex from 'info' column
        - Cast result and bib into integers
    """

    ##Cast columns
    df_results_pp = df_results.with_columns(
        pl.col("result").cast(pl.Int16),
        pl.col("name").str.to_lowercase().str.replace_all(" ", "_"),
        pl.col("time").str.strip_chars("\nArrivée").str.to_time("%H:%M:%S"),
        pl.col("bib").cast(pl.Int16),
        pl.col("info").str.split(" | Âge "),
    )

    ##Extract age and sex
    df_results_pp = df_results_pp.with_columns(
        pl.col("info").list.get(0).alias("sex"),
        pl.col("info").list.get(1).cast(pl.Int8).alias("age"),
    ).drop(["info"])  # remove 'info' column

    ##Rearange columns order
    df_results_pp = df_results_pp.select(
        ["result", "name", "time", "bib", "sex", "age", "url"]
    ).sort("result")  # be sure to sort dataframe by result

    return df_results_pp


def download_splits_athlete(driver, athlete_name, url_splits_athlete):
    """
    Download detailed results (split times) of a given athlete
    """

    ##Go to athlete detailed results webpage
    driver.get(url_splits_athlete)

    ##Find detailed results
    aux_results_details = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                "#root > div.app > div.app__content > div.page-body > div > div > div > div > div > div > ul",
            )
        )
    )
    results_details = aux_results_details.find_elements(By.TAG_NAME, "li")

    ##Iterate through each splits
    data = []
    for split in results_details:
        list_info = split.text.split("\n")
        name = list_info[0]

        ##Check if it is a split (and not the start - with no info)
        if name != "Start":
            ##Get split time and total time at split
            time_split = list_info[1]
            time_total_split = list_info[3]

            ##Aggregate data
            data.append([athlete_name, name, time_split, time_total_split])

    ##Create a dataframe
    df_splits_athlete = pl.DataFrame(
        data, schema=["athlete_name", "split", "time_split", "time_total"], orient="row"
    )

    return df_splits_athlete


def preprocess_splits_athlete(df_splits_athlete):
    """
    Preprocessing of splits:
        - Deal with missing values
        - Convert split times from string to time objects
    """

    ##Deal with missing informations
    df_splits_athlete_pp = df_splits_athlete.with_columns(
        pl.when(pl.col("time_split") == "--")
        .then(None)
        .otherwise(pl.col("time_split"))
        .alias("time_split"),
        pl.when(pl.col("time_total") == "--")
        .then(None)
        .otherwise(pl.col("time_total"))
        .alias("time_total"),
    )

    ##Convert times into time objects
    df_splits_athlete_pp = df_splits_athlete_pp.with_columns(
        pl.col("time_split").str.to_time("%H:%M:%S"),
        pl.col("time_total").str.to_time("%H:%M:%S"),
    )

    return df_splits_athlete_pp


def scraping_results(url_results: str, year: int):
    """
    General function to srape results of 'L'Etape du Tour' of a given results
    2 different type of results downloaded, from 'Active Results' website (https://resultscui.active.com):
        - Global results, with the rank of each athlete, its finish time, and further informations (bib, age, sex)
        - Detailed results of each athlete, with the different split times

    Example:
        - Global results from following webpage: https://resultscui.active.com/events/LÉtapeduTourdeFrance2024
        - Detailed results of athlete 'x' from following webpage: https://resultscui.active.com/participants/46156576?pn=23b943ac226659bfa270f20580da7037483fdfa90701b259d8b0009dbe912e8c

    Args:
        - URL of the results of considered edition
        - Year of considered edition

    Returns:
        - 1 dataframe containing global results (format: 1 row per athlete)
        - y dataframes (for y finishers), each containing split times of an athlete

    Limitations:
        - Some split times are not provided (e.g. winner of 2024 edition)
        - "Fast and dirty" names formatting -> some special characters are still present (e.g. '@'), but it is not very important
        as we do not care about the identity of athletes here
    """

    ##### RESULTS
    # -------

    ##Go to results webpage
    driver = init_driver()
    driver.get(url_results)
    close_cookies(driver)  # close cookies

    ##Load all results
    load_all_results(driver)

    ##Download all results
    df_results = download_results(driver)
    driver.quit()  # quit driver

    ##Preprocess results
    df_results_pp = preprocess_results(df_results)

    ##Save results
    df_results_pp.write_parquet(
        f"/Users/qdouzery/Desktop/enduraw/data/edt-{year}_results/df_results.parquet"
    )

    ##### SPLITS
    # -------

    ##Come back to results page as initialization
    driver = init_driver()
    driver.get(url_results)
    close_cookies(driver)  # close cookies

    ##Iterate through athletes
    for r in range(len(df_results_pp)):
        ##Get athlete name and url of splits
        athlete_name = df_results["name"].item(r)
        url_splits_athlete = df_results["url"].item(r)

        ##Check we did not have downloaed athlete's detailed results yet
        if not (
            os.path.isfile(
                f"/Users/qdouzery/Desktop/enduraw/data/edt-{year}_results/splits/df_splits_{athlete_name.replace('_', '-')}.parquet"
            )
        ):
            ##Download athlete's splits
            df_splits_athlete = download_splits_athlete(
                driver, athlete_name, url_splits_athlete
            )

            ##preprocess athlete's splits
            df_splits_athlete_pp = preprocess_splits_athlete(df_splits_athlete)

            ##Save splits
            df_splits_athlete_pp.write_parquet(
                f"/Users/qdouzery/Desktop/enduraw/data/edt-{year}_results/splits/df_splits_{athlete_name.replace('_', '-')}.parquet"
            )
            print(f"Splits of {athlete_name} downloaded.")

    ##Quit driver
    driver.quit()


if __name__ == "__main__":
    ##Set results URL and year
    url_results = "https://resultscui.active.com/events/L%C3%89tapeduTourdeFrance2024"
    year = 2024

    ##Scrape results
    scraping_results(url_results, year)
