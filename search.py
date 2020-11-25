import csv
import time
import re
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup


queries = []
with open("queries.csv", "r") as f:
    reader = csv.DictReader(f, delimiter=";")
    for line in reader:
        queries.append(line)


CSV_COLUMNS = ["name", "address", "phone", "site", "email"]
URL = "https://google.com/maps/search/{}+{}?hl=en"
WEBSITE_URL = "https://www.{}"
WEBSITE_URL_UNSAFE = "http://www.{}"
TIMEOUT = 30

options = webdriver.ChromeOptions()
options.add_argument("--lang=en")
options.add_argument('--headless')
options.add_argument('--ignore-certificate-errors')


def get_previous_results(csv_file):
    results = {}
    try:
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f, delimiter=";")
            for line in reader:
                results[line["name"]] = line

        print("{} past entries found.".format(len(results)))
    except IOError:
        print("0 past entries found.")

    return results


def write_item(data, csv_file):
    try:
        with open(csv_file, "a") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";")
            writer.writerow(data)
    except IOError:
        print("Error saving csv file.")


def get_email(site):
    possible_emails = []
    try:
        email_driver = webdriver.Chrome("./bin/chromedriver", options=options)
        contact_pages = []
        try:
            email_driver.get(WEBSITE_URL_UNSAFE.format(site))
            contact_pages.append(WEBSITE_URL_UNSAFE.format(site))
        except Exception:
            email_driver.get(WEBSITE_URL.format(site))
            contact_pages.append(WEBSITE_URL.format(site))
        time.sleep(10)
        response = BeautifulSoup(email_driver.page_source, "html.parser")
        for p in response.find_all("a", href=lambda href: href and "contact" in href):
            contact_pages.append(p["href"])

        for page in contact_pages:
            if page != WEBSITE_URL.format(site) or page != WEBSITE_URL_UNSAFE.format(site):
                try:
                    email_driver.get(page)
                except Exception:
                    email_driver.get('{}/{}'.format(contact_pages[0], page))
                response = BeautifulSoup(email_driver.page_source, "html.parser")

            emails = re.findall(r"\w+@\w+\.{1}\w+", str(response.text))
            for e in emails:
                if e not in possible_emails:
                    possible_emails.append(e.lower().replace('phone', ''))

            for e in response.find_all("a", href=lambda href: href and "mailto:" in href):
                email = e["href"].split(":")[1]
                email = email.split("?")[0]
                if email not in possible_emails:
                    possible_emails.append(email)

        email_driver.quit()
    except Exception:
        traceback.print_exc()
        print('Error')

    return ", ".join(possible_emails)


for q in queries:
    print("Starting scraping...")
    location = q["location"]
    business = q["business"]
    category = q["category"]

    if category:
        category = category.split(",")

    print(
        "Searching for {} nearby {} with keyword(s) {}".format(
            q["business"], q["location"], q["category"]
        )
    )

    location = location.replace(" ", "+")
    business = business.replace(" ", "+")
    driver = webdriver.Chrome("./bin/chromedriver", options=options)
    driver.get(URL.format(location, business))
    time.sleep(5)

    csv_file = "{}.csv".format(
        "{}_nearby_{}".format(q["business"], q["location"]).replace(" ", "_")
    )
    results = get_previous_results(csv_file)

    if not results:
        print("Creating CSV file as {}".format(csv_file))
        with open(csv_file, "a") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS, delimiter=";")

            if csvfile.tell() == 0:
                writer.writeheader()

    try:
        WebDriverWait(driver, 5).until(
            EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[@class='widget-consent-frame']"))
        )
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[id='introAgreeButton']"))
        ).click()
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "div[id='introAgreeButton']"))
        ).click()
        driver.switch_to_default_content()
    except Exception:
        pass

    while True:
        response = BeautifulSoup(driver.page_source, "html.parser")
        places = response.find_all("div", class_="section-result")

        for place in places:
            name = (
                place.find("h3", class_="section-result-title")
                .find("span")
                .text.strip()
            )

            place_button = WebDriverWait(driver, TIMEOUT).until(
                EC.visibility_of_element_located(
                    (By.XPATH, '//div[@aria-label="{}"]'.format(name))
                )
            )
            place_button.click()

            if category:
                place_category = WebDriverWait(driver, TIMEOUT).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[jsaction="pane.rating.category"]')
                    )
                )
                place_category = place_category.text.strip()

                has_category = False
                for c in category:
                    if c.lower() in place_category.lower():
                        has_category = True
                        break

                if not has_category:
                    print("Skipped {} as it is a {}.".format(name, place_category))
                    back_button = WebDriverWait(driver, TIMEOUT).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                "//button[@class='section-back-to-list-button blue-link noprint']",
                            )
                        )
                    )
                    back_button.click()
                    continue

            try:
                address = WebDriverWait(driver, TIMEOUT).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[data-item-id="address"]')
                    )
                )
                address = (
                    address.get_attribute("aria-label")
                    .split(":")[1]
                    .replace(",", "")
                    .strip()
                )

                r = results.get(name)
                if r and r.get("address") == address:
                    print("Skipped duplicate -> {}".format(name))
                    back_button = WebDriverWait(driver, TIMEOUT).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                "//button[@class='section-back-to-list-button blue-link noprint']",
                            )
                        )
                    )
                    back_button.click()
                    continue
            except Exception:
                address = ""

            try:
                phone = WebDriverWait(driver, TIMEOUT).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[data-item-id^="phone:tel:"]')
                    )
                )
                phone = phone.get_attribute("data-item-id").split(":")[2].strip()
            except Exception:
                phone = ""

            try:
                site = WebDriverWait(driver, TIMEOUT).until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, 'button[aria-label^="Website:"]')
                    )
                )
                site = site.get_attribute("aria-label").split(":")[1].strip()
            except Exception:
                site = ""

            email = ""
            if site:
                email = get_email(site)

            data = {
                "name": name,
                "address": address,
                "phone": phone,
                "site": site,
                "email": email,
            }
            print("Scraped -> {}.".format(data))
            write_item(data, csv_file)
            print("Stored.")

            back_button = WebDriverWait(driver, TIMEOUT).until(
                EC.visibility_of_element_located(
                    (
                        By.XPATH,
                        "//button[@class='section-back-to-list-button blue-link noprint']",
                    )
                )
            )
            back_button.click()
            time.sleep(5)

        try:
            next_button = WebDriverWait(driver, TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[@jsaction='pane.paginationSection.nextPage']")
                )
            )
            next_button.click()
            time.sleep(10)

        except Exception:
            break

    driver.quit()
