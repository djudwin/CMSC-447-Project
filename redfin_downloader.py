# this file contains a webdriver to download redfin data to local machine and filter it
# using the user's inputted preferences. Still need to add http requests to get the
# parameters from the user input on the website.

import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
import glob
import fileinput

# the file paths for the webdriver parameters will need to be modified to work on other computers
download_path = os.getcwd() + "/csv_data/"
fp = webdriver.FirefoxProfile("/Library/Application Support/Firefox/Profiles/p9sqpxhh.SeleniumProfile")
fp.set_preference("browser.download.folderList", 2)
fp.set_preference("browser.download.manager.showWhenStarting", False)
fp.set_preference("browser.download.dir", download_path)
fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "text/csv")

browser = webdriver.Firefox(firefox_profile=fp)
browser.get("https://www.redfin.com")


class wait_for_page_load(object):

    def __init__(self, browser):
        self.browser = browser

    def __enter__(self):
        self.old_page = self.browser.find_element_by_tag_name('html')

    def page_has_loaded(self):
        new_page = self.browser.find_element_by_tag_name('html')
        return new_page.id != self.old_page.id

    def __exit__(self, *_):
        wait_for(self.page_has_loaded)


def wait_for(condition_function):
    start_time = time.time()
    while time.time() < start_time + 3:
        if condition_function():
            return True
        else:
            time.sleep(0.1)
    raise Exception(
        'Timeout waiting for {}'.format(condition_function.__name__)
    )


# cleans the last search data. should be called before each new search
def clean_folder():
    folder = os.getcwd() + '/csv_data'
    skip = {os.getcwd() + '/csv_data/old_fault_file.csv', os.getcwd() + '/csv_data/old_success.csv',
            os.getcwd() + '/csv_data/_fault_file.csv',
            os.getcwd() + '/csv_data/_success.csv'}
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        if file_path in skip:
            continue
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)


def collect_by_location(keys):

    if keys is None:
        print("error: please enter a location")
        return
    try:
        with wait_for_page_load(browser):
            browser.get("https://www.redfin.com")
    except:
        browser.get("https://www.redfin.com")

    elem = WebDriverWait(browser, 3).until(EC.presence_of_element_located((By.CLASS_NAME, "search-input-box")))
    elem.clear()
    elem.send_keys(keys)

    try:
        with wait_for_page_load(browser):
            browser.find_element_by_class_name("search-input-box").submit()
    except:
        pass
    # Check for an unrecognized city
    if browser.current_url == 'https://www.redfin.com/':
        print('No listings for ' + keys)
    else:
        # find download link. Throw exception for a city with no listings
        try:
            elem = WebDriverWait(browser, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, "downloadLink"))).click()
        except:
            print('No download for ' + keys)


def merge_data():
    interesting_files = glob.glob(os.getcwd() + "/csv_data/*.csv")
    skip = {os.getcwd() + '/csv_data/old_fault_file.csv', os.getcwd() + '/csv_data/old_success.csv',
            os.getcwd() + '/csv_data/_all_properties.csv', os.getcwd() + '/csv_data/_fault_file.csv',
            os.getcwd() + '/csv_data/_success.csv'}
    header_saved = False
    with open('_all_properties.csv', 'w') as fout:
        for filename in interesting_files:
            with open(filename) as fin:
                if filename in skip:
                    print("skip: " + filename)
                    continue
                print("file:" + filename)
                header = next(fin)
                if not header_saved:
                    fout.write(header)
                    header_saved = True
                for line in fin:
                    fout.write(line)

        # remove duplicate houses
        seen = set()  # set for fast O(1) amortized lookup
        for line in fileinput.FileInput('_all_properties.csv', inplace=1):
            if line in seen:
                continue  # skip duplicate

            seen.add(line)
            print(line)  # standard output is now redirected to the file


def filter_data():
    # we will need to get these parameters from the website:
    minBedrooms = 2
    minBathrooms = 1
    propertyTypes = {'Townhouse', 'Single Family Residential'}
    minHouseSize = 500
    minPropertySize = 0
    maxPrice = 40000

    properties = open('_all_properties.csv', 'r')
    filtered = open('filtered_properties.csv', 'w')
    file1 = csv.DictReader(properties, )
    file2 = csv.DictWriter(filtered, fieldnames=file1.fieldnames)
    data1 = list(file1)

    for row in data1:
        keep = True

        if row['SQUARE FEET'] and int(row['SQUARE FEET']) < minHouseSize:
            keep = False
        elif row['LOT SIZE'] and int(row['LOT SIZE']) < minPropertySize:
            keep = False
        elif row['BEDS'] and int(row['BEDS']) < minBedrooms:
            keep = False
        elif row['BATHS'] and float(row['BATHS']) < minBathrooms:
            keep = False
        elif row['PROPERTY TYPE'] not in propertyTypes:
            keep = False
        elif row['PRICE'] and float(row['PRICE']) > maxPrice:
            keep = False

        if keep:
            file2.writerow(row)


clean_folder()  # remove old csv files
collect_by_location('baltimore, MD')  # get all house listings in Baltimore MD
# collect_by_location(zip='21228')  # get all house listings in zip code 21228
# collect_by_location(school='UMBC')  # get all house listings near UMBC
merge_data()  # merge all house listings into one csv
# From here we can sift on other parameters, like # bedrooms, # bathrooms, Property Type, House Size, and Property Size
filter_data()