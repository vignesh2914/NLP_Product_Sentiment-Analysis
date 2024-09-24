import os   
import sys
from datetime import datetime, timedelta
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import quote
from exception import CustomException
from logger import logging

def make_url(country_keyword: str, job_keyword: str, location_keyword: str, filter_option: int, page_number: int = 1) -> str:
    try:
        formatted_job_keyword = quote(job_keyword)
        formatted_location_keyword = quote(location_keyword)

        base_url = {
            1: f'https://{country_keyword}.indeed.com/jobs?q={formatted_job_keyword}&l={formatted_location_keyword}&start={page_number}',
            2: f'https://{country_keyword}.indeed.com/jobs?q={formatted_job_keyword}&l={formatted_location_keyword}&radius=7&fromage=1&start={page_number}',
            3: f'https://{country_keyword}.indeed.com/jobs?q={formatted_job_keyword}&l={formatted_location_keyword}&radius=7&fromage=3&start={page_number}',
            4: f'https://{country_keyword}.indeed.com/jobs?q={formatted_job_keyword}&l={formatted_location_keyword}&radius=7&fromage=7&start={page_number}',
            5: f'https://{country_keyword}.indeed.com/jobs?q={formatted_job_keyword}&l={formatted_location_keyword}&radius=50&fromage=14&start={page_number}'
        }

        if filter_option not in base_url:
            raise ValueError("Invalid filter option. Please select a value between 1 and 5.")

        url = base_url[filter_option]
        logging.info(f"Constructed URL: {url}")
        return url
    except Exception as e:
        logging.error(f"Error constructing URL: {e}")
        raise CustomException(e, sys)

def configure_driver() -> webdriver.Chrome:
    """
    Configures the Selenium WebDriver with the necessary options.
    :return: Configured WebDriver instance.
    """
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--log-level=3")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        chrome_driver_path = ChromeDriverManager().install()
        driver = webdriver.Chrome(service=Service(chrome_driver_path), options=options)

        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
        )

        return driver
    except Exception as e:
        logging.error(f"An error occurred while configuring the driver: {e}")
        raise CustomException(e, sys)

def extract_job_data(job_element) -> dict:
    """
    Extracts job data from a BeautifulSoup element representing a job listing.

    :param job_element: BeautifulSoup element containing the job details.
    :return: A dictionary containing the extracted job data (title, company, location, link).
    """
    try:
        title = job_element.find('h2', class_="jobTitle")
        job_title = title.text.strip() if title else 'N/A'  

        company = job_element.find('span', class_="css-63koeb eu4oa1w0")
        job_company = company.text.strip() if company else 'N/A'

        location = job_element.find('div', class_="css-1p0sjhy eu4oa1w0")
        job_location = location.text.strip() if location else 'N/A'

        job_link_tag = job_element.find('a', class_='jcs-JobTitle css-jspxzf eu4oa1w0')
        job_link = job_link_tag['href'] if job_link_tag else 'N/A'
       
        if job_link != 'N/A':
            job_link = "https://www.indeed.com" + job_link

        job_data = {
            'JobTitle': job_title,
            'CompanyName': job_company,    
            'JobLocation': job_location,
            'JobURL': job_link
        }

        return job_data

    except Exception as e:
        logging.error(f"Error extracting job data: {e}")
        raise CustomException(e, sys)

def scrape_job_data(job_keyword: str, location_keyword: str, time_limit: int = 60) -> List[Dict[str, str]]:
    """
    Scrapes job data from Naukri based on the specified job and location.

    :param job_keyword: Job title to search for.
    :param location_keyword: Location to search in.
    :param time_limit: Time limit for the scraping process.
    :return: A list of dictionaries containing job data.
    """
    logging.info(f"Scraping started for keyword '{job_keyword}' in location '{location_keyword}'.")

    try:
        driver = configure_driver()

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=time_limit)
        logging.info(f"Scraping started at: {start_time.time()}, will end at: {end_time.time()}")

        job_data = []
        page_number = 1

        while datetime.now() < end_time:
            url = make_url(job_keyword, location_keyword, page_number)
            logging.info(f"Scraping page {page_number}: {url}")
            driver.get(url)

            WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "srp-jobtuple-wrapper"))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            jobs = soup.find_all("div", class_="srp-jobtuple-wrapper")

            if not jobs:
                logging.info("No job elements found on this page. Ending scrape.")
                logging.info("No jobs found for this filter. Try using a different filter or location.")
                break  

            for job_element in jobs:
                job_data.append(extract_job_data(job_element))

            page_number += 1  

        driver.quit()
        logging.info("Scraping completed successfully.")
        return job_data

    except Exception as e:
        logging.error(f"Error in scrape_job_data: {e}", exc_info=True)
        raise CustomException(e, sys)

def main():
    try:
        print("Please select a filter option:")
        print("1: All job data (no date filter)")
        print("2: Job data from the last 24 hours")
        print("3: Job data from 3 days ago")
        print("4: Job data from 7 days ago")
        print("5: Job data from 14 days ago")
       
        filter_option = int(input("Enter your choice (1-5): "))
       
        if filter_option not in range(1, 6):
            raise ValueError("Invalid selection. Please choose a number between 1 and 5.")
       
        country_keyword = 'in'
        job_keyword = 'AI engineer'
        location_keyword = 'united states'
       
        job_data = scrape_job_data(country_keyword, job_keyword, location_keyword, filter_option)
       
        df = pd.DataFrame(job_data)
        print(df)
    except Exception as e:
        print(f"An error occurred: {e}")
 
if __name__ == "__main__":
    main()
