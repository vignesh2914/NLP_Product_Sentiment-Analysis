import os   
import sys
from datetime import datetime, timedelta
from typing import List, Dict,Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
import pandas as pd
from urllib.parse import quote
from exception import CustomException
from logger import logging
from dotenv import load_dotenv


load_dotenv()

host = os.getenv("database_host_name")
user = os.getenv("database_user_name")
password = os.getenv("database_user_password")
database = os.getenv("database_name")


load_dotenv()

def make_url(filter_option: int, Product_keyword: str = "OptimumNutrition", product_code: str = "B0BBR11HM9", page_number: int = 1) -> str:
    try:
        formatted_product_keyword = quote(Product_keyword)
        formatted_product_code = quote(product_code)

        base_url = {
            1: f"https://www.amazon.in/{formatted_product_keyword}/product-reviews/{formatted_product_code}/ref=cm_cr_arp_d_paging_btm_next_{page_number}?ie=UTF8&reviewerType=all_reviews&pageNumber={page_number}&filterByStar=one_star",
            2: f"https://www.amazon.in/{formatted_product_keyword}/product-reviews/{formatted_product_code}/ref=cm_cr_getr_d_paging_btm_next_{page_number}?ie=UTF8&reviewerType=all_reviews&pageNumber={page_number}&filterByStar=two_star",
            3: f"https://www.amazon.in/{formatted_product_keyword}/product-reviews/{formatted_product_code}/ref=cm_cr_arp_d_paging_btm_next_{page_number}?ie=UTF8&reviewerType=all_reviews&pageNumber={page_number}&filterByStar=three_star",
            4: f"https://www.amazon.in/{formatted_product_keyword}/product-reviews/{formatted_product_code}/ref=cm_cr_getr_d_paging_btm_next_{page_number}?ie=UTF8&reviewerType=all_reviews&pageNumber={page_number}&filterByStar=four_star",
            5: f"https://www.amazon.in/{formatted_product_keyword}/product-reviews/{formatted_product_code}/ref=cm_cr_getr_d_paging_btm_next_{page_number}?ie=UTF8&reviewerType=all_reviews&pageNumber={page_number}&filterByStar=five_star",
            6: f"https://www.amazon.in/{formatted_product_keyword}/product-reviews/{formatted_product_code}/ref=cm_cr_arp_d_paging_btm_next_{page_number}?ie=UTF8&reviewerType=all_reviews&pageNumber={page_number}"
        } 
        
        if filter_option not in base_url:
            raise ValueError("Invalid filter option. Please select a value between 1 and 6.")

        url = base_url[filter_option]
        logging.info(f"Constructed URL: {url}")
        return url
    except Exception as e:
        logging.error(f"Error constructing URL: {e}")
        raise CustomException(e, sys)


def configure_driver() -> webdriver.Chrome:
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


def extract_product_data(job_element) -> dict:
    try:
        review_text = job_element.find('span', {'data-hook': 'review-body'})
        text = review_text.text.strip() if review_text else 'N/A'

        date = job_element.find('span', {'data-hook': 'review-date'})
        review_date = date.text.strip() if date else 'N/A'

        flavour_name = job_element.find('a', class_="a-size-mini a-link-normal a-color-secondary")
        flavour = flavour_name.text.strip() if flavour_name else 'N/A'

        job_data = {
            'review_text': text,
            'review_date': review_date,
            'flavour_name': flavour,
        }

        return job_data

    except Exception as e:
        logging.error(f"Error extracting review data: {e}")
        raise CustomException(e, sys)


def scrape_product_data(Product_keyword: str, product_code: str, filter_option: int, time_limit: int = 60) -> List[Dict[str, str]]:
    logging.info(f"Scraping started for keyword '{Product_keyword}' with product code '{product_code}' using filter option '{filter_option}'.")

    try:
        driver = configure_driver()

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=time_limit)
        logging.info(f"Scraping started at: {start_time.time()}, will end at: {end_time.time()}")

        job_data = []
        page_number = 1

        while datetime.now() < end_time and page_number <= 10:
            url = make_url(filter_option, Product_keyword, product_code, page_number)
            logging.info(f"Scraping page {page_number}: {url}")
            
            max_retries = 2
            retries = 0
            
            while retries < max_retries:
                try:
                    driver.get(url)
                    WebDriverWait(driver, 60).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="a-page"]/div[2]/div/div[1]/div/div[1]/div[5]/div[3]'))
                    )
                    break
                except TimeoutException:
                    retries += 1
                    logging.warning(f"Timeout occurred, retrying... {retries}/{max_retries}")
                    if retries == max_retries:
                        logging.error(f"Failed to load page after {max_retries} attempts.")
                        return job_data

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            review_elements = soup.find_all('div', {'data-hook': 'review'})

            if not review_elements:
                logging.info("No more reviews found, stopping the scraping.")
                break

            for job_element in review_elements:
                job_data.append(extract_product_data(job_element))

            page_number += 1

        driver.quit()
        logging.info("Scraping completed successfully.")
        return job_data

    except Exception as e:
        logging.error(f"Error in scrape_product_data: {e}", exc_info=True)
        raise CustomException(e, sys)


def create_dataframe_of_product_data(Product_data: List[Dict[str, str]]) -> pd.DataFrame:
    try:
        if Product_data:
            column_names = ["Product_Review", "Date_Reviewed", "Flavour"]
            df = pd.DataFrame(Product_data, columns=column_names)
            logging.info("Data converted into dataframe")
            return df
        else:
            logging.info("No product data found to create dataframe.")
            return pd.DataFrame(columns=["Product_Review", "Date_Reviewed", "Flavour"])
    except Exception as e:
        error_msg = f"An error occurred while creating the dataframe: {e}"
        logging.error(error_msg)
        raise CustomException(error_msg) from e
def save_product_data_to_csv(job_data: List[Dict[str, str]], Product_keyword: str, product_code: str) -> Optional[str]:
    try:
        if job_data:
            # Directly use job_data without specifying column names again
            df = pd.DataFrame(job_data)

            folder_name = "Product_Review_data"  # Use the existing folder name
            os.makedirs(folder_name, exist_ok=True)  # Ensure the folder exists

            current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            csv_file_path = os.path.join(folder_name, f"{current_datetime}_{Product_keyword}_{product_code}.csv")

            df.to_csv(csv_file_path, index=False)
            logging.info(f"Fetched product data saved in CSV file successfully: {csv_file_path}")
            return csv_file_path
        else:
            logging.info("No recent data found to save.")
    except Exception as e:
        logging.error(f"An error occurred while saving CSV: {e}")
        raise CustomException(e, sys)
    
def save_product_data_to_csv(job_data: List[Dict[str, str]], Product_keyword: str, product_code: str, filter_option: int) -> Optional[str]:
    try:
        if job_data:
            # Directly use job_data without specifying column names again
            df = pd.DataFrame(job_data)

            folder_name = "Product_Review_data"  # Use the existing folder name
            os.makedirs(folder_name, exist_ok=True)  # Ensure the folder exists

            # Map filter option to review type
            filter_map = {
                1: "1_star",
                2: "2_star",
                3: "3_star",
                4: "4_star",
                5: "5_star",
                6: "all_reviews"
            }
            filter_name = filter_map.get(filter_option, "unknown")

            current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            csv_file_path = os.path.join(folder_name, f"{current_datetime}_{Product_keyword}_{product_code}_{filter_name}.csv")

            df.to_csv(csv_file_path, index=False)
            logging.info(f"Fetched product data saved in CSV file successfully: {csv_file_path}")
            return csv_file_path
        else:
            logging.info("No recent data found to save.")
    except Exception as e:
        logging.error(f"An error occurred while saving CSV: {e}")
        raise CustomException(e, sys)

if __name__ == "__main__":
    try:
        Product_keyword = "OptimumNutrition"
        product_code = "B0BBR11HM9"
        filter_option = 5  # Example for one-star reviews

        scraped_data = scrape_product_data(Product_keyword, product_code, filter_option)
        df = create_dataframe_of_product_data(scraped_data)
        save_product_data_to_csv(scraped_data, Product_keyword, product_code, filter_option)

    except CustomException as e:
        logging.error(f"An error occurred in the main flow: {e}")
