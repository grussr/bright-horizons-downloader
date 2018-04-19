import os
import io
import re
import sys
import pdb
import time
import shutil
import pickle
import logging
import logging.config

from random import randrange
from getpass import getpass
from os.path import abspath, dirname, join, isfile, isdir
import datetime
from pytz import timezone

import json
import requests
import lxml.html
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.proxy import *
from pymongo import MongoClient
from PIL import Image
import piexif
from google.cloud import storage

# -----------------------------------------------------------------------------
# Logging stuff
# -----------------------------------------------------------------------------
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': "%(asctime)s %(levelname)s %(module)s::%(funcName)s: %(message)s",
            'datefmt': '%H:%M:%S'
        }
    },
    'handlers': {
        'app': {'level': 'DEBUG',
                    'class': 'ansistrm.ColorizingStreamHandler',
                    'formatter': 'standard'},
        'default': {'level': 'ERROR',
                    'class': 'ansistrm.ColorizingStreamHandler',
                    'formatter': 'standard'},
    },
    'loggers': {
        'default': {
            'handlers': ['default'], 'level': 'ERROR', 'propagate': False
        },
         'app': {
            'handlers': ['app'], 'level': 'DEBUG', 'propagate': True
        },

    },
}
logging.config.dictConfig(LOGGING_CONFIG)


# -----------------------------------------------------------------------------
# The scraper code.
# -----------------------------------------------------------------------------
class DownloadError(Exception):
    pass


class Client:
    MONGO_URL = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/test_db')
    COOKIE_FILE = "state/cookies.pkl"
    TIMESTAMP_FILE = "state/timestamp"
    ROOT_URL = "https://www.tadpoles.com/"
    HOME_URL = "https://www.tadpoles.com/parents"
    LIST_BASE_URL = ROOT_URL+"remote/v1/events?direction=range"
    MIN_SLEEP = 1
    MAX_SLEEP = 3
    NUM_DAYS = int(os.getenv("NUM_DAYS","45"))
    DAY_RANGE = datetime.timedelta(days=NUM_DAYS)
    BUCKET_NAME = os.getenv("AWS_BUCKET_NAME","tadpoles")
    GS_CLIENT = storage.Client()
    BUCKET = GS_CLIENT.get_bucket(BUCKET_NAME)

    def __init__(self):
        self.init_logging()

    def init_logging(self):
        logger = logging.getLogger('app')
        self.info = logger.info
        self.debug = logger.debug
        self.warning = logger.warning
        self.critical = logger.critical
        self.exception = logger.exception

    def __enter__(self):
        options = Options()
        options.add_argument("--headless")

        fp = webdriver.FirefoxProfile()

        self.info("Starting browser")
        self.br = self.browser = webdriver.Firefox(firefox_options=options,firefox_profile=fp)
        self.br.implicitly_wait(10)
        return self

    def __exit__(self, *args):
        self.info("Shutting down browser")
        self.browser.quit()

    def sleep(self, minsleep=None, maxsleep=None):
        _min = minsleep or self.MIN_SLEEP
        _max = maxsleep or self.MAX_SLEEP
        duration = randrange(_min * 100, _max * 100) / 100.0
        self.debug('Sleeping %r' % duration)
        time.sleep(duration)

    def navigate_url(self, url):
        self.info("Navigating to %r", url)
        self.br.get(url)

    def dump_to_db(self, item_type, data):
        client = MongoClient(self.MONGO_URL)
        try:
            db = client.get_default_database().settings
            db.replace_one({'type':item_type},{'type': item_type, 'value': data},True)
        except Exception as exc:
            self.exception(exc)

    def load_from_db(self, item_type):
        client = MongoClient(self.MONGO_URL)
        try:
            db = client.get_default_database().settings
            value = db.find_one({'type':item_type})
            if value is not None:
                return (db.find_one({'type':item_type}))['value']
        except Exception as exc:
            self.exception(exc)
        return None

    def load_cookies_db(self):
        self.info("Loading cookies from db.")
        self.cookies = self.load_from_db('cookie')
        if self.cookies is None:
            raise FileNotFoundError ("cookie not found in db")
        self.cookies = pickle.loads(self.cookies)

    def dump_cookies_db(self):
        self.info("Dumping cookies to db.")
        self.dump_to_db ('cookie', pickle.dumps(self.br.get_cookies()))

    def dump_screenshot_db(self):
        self.info("Dumping screenshot to db.")
        self.dump_to_db ('screenshot', self.br.get_screenshot_as_png())

    def add_cookies_to_browser(self):
        self.info("Adding the cookies to the browser.")
        for cookie in self.cookies:
            if self.br.current_url.strip('/').endswith(cookie['domain']):
                self.br.add_cookie(cookie)

    def requestify_cookies(self):
        # Cookies in the form reqeusts expects.
        self.info("Transforming the cookies for requests lib.")
        self.req_cookies = {}
        for s_cookie in self.cookies:
            self.req_cookies[s_cookie["name"]] = s_cookie["value"]

    def switch_windows(self):
        '''Switch to the other window.'''
        self.info("Switching windows.")
        all_windows = set(self.br.window_handles)
        self.info(all_windows)
        try:
            current_window = set([self.br.current_window_handle])
            self.info(current_window)
            other_window = (all_windows - current_window).pop()
            self.br.switch_to.window(other_window)
        except:
            current_window = self.br.window_handles[0]
            self.br.switch_to.window(current_window)
            
        self.info(current_window)

    def dump_timestamp_db(self, timestamp):
        self.info("Dumping Timestamp to db.")
        self.dump_to_db ('timestamp', pickle.dumps(timestamp))

    def load_timestamp_db(self):
        self.info("Loading Timestamp from db.")
        self.full_sync = False
        start_time = self.load_from_db('timestamp')
        if start_time is None:
            start_time = datetime.datetime.now()
            self.full_sync = True
        else:
            start_time = pickle.loads(start_time)
        return start_time
        
    def get_api(self):
        end_time = datetime.datetime.now()
        start_time = self.load_timestamp_db()

        while True:
            if self.full_sync:
                start_time=end_time-self.DAY_RANGE

            start_time_val=int(time.mktime(start_time.timetuple()))

            start_string="&earliest_event_time="+str(start_time_val)
            end_string="&latest_event_time="+str(int(time.mktime(end_time.timetuple())))

            num_events="&num_events=300&client=dashboard"

            url = self.LIST_BASE_URL+start_string+end_string+num_events
            self.info(url)
            try:
                resp = requests.get(url,cookies=self.req_cookies)
                if resp.status_code != 200:
                    msg = 'Error (%r) downloading %r'
                    raise DownloadError(msg % (resp.status_code, url))

                jsonData = json.loads(resp.text)

                if len(jsonData['events']) == 0:
                    break
                for event in jsonData['events']:
                    if len(event['attachments']) > 0:
                        for attachment in event['new_attachments']:
                            self.save_image_api(attachment['key'],event['event_time'],attachment['mime_type'])
                
                if not self.full_sync:
                    break
                end_time=start_time
            except Exception as exc:
               self.exception(exc)
               self.dump_timestamp_db(start_time)
               return
        self.dump_timestamp_db(end_time)                 

    def do_login(self):
        # Navigate to login page.
        self.info("Navigating to login page.")
        self.br.find_element_by_id("login-button").click()
        self.br.find_element_by_xpath("//div[@data-bind = 'click: chooseParent']").click()
        self.br.find_element_by_xpath("//img[@data-bind = 'click:loginGoogle']").click()

        # Focus on the google auth popup.
        self.switch_windows()

        # Enter email.
        email = self.br.find_element_by_id("identifierId")
        #email.click()
        email.send_keys(input("Enter email: "))
        #email.submit()
        self.br.find_element_by_id("identifierNext").click()
        self.sleep()

        # Enter password.
        #self.info(self.br.current_url)
        #self.br.find_element_by_css_selector("input[type='password'][name='password']").send_keys(getpass("Enter password:")).submit();

        passwd = self.br.find_element_by_css_selector("input[type='password'][name='password']")
        passwd.send_keys(getpass("Enter password:"))
        #passwd.submit()
        self.br.find_element_by_id("passwordNext").click()
        
        # Enter 2FA pin.
        #Epin = self.br.find_element_by_id("idvPreregisteredPhonePin")
        #pin.send_keys(getpass("Enter google verification code: "))
        #pin.submit()

        self.br.save_screenshot("state/after_login.png")
        self.dump_screenshot_db()
        # Click "approve".
        self.info("Sleeping 2 seconds.")
        self.sleep(minsleep=10,maxsleep=15)
        self.info("Clicking 'approve' button.")
        #self.br.find_element_by_id("submit_approve_access").click()
        
        # Switch back to tadpoles.
        self.switch_windows()
        
    def write_exif(self, response, timestamp):
        response.raw.decode_content = True
        try:
            #image = Image.open(response.raw)
            image = response.raw
            #Load Exif Info & Modify
            try:
                exif_dict = piexif.load(image.info["exif"])
                zeroth_ifd = piexif.load(image.info["0th"])
                
            except:
                if exif_dict = None:
                    exif_dict = {}
                if zeroth_ifd = None:
                    zeroth_ifd = {}
                self.debug("Failed loading exif data")
                        
            #if image.mode in ('RGBA', 'LA'):
            #    image = image.convert("RGB")
                
            #w, h = image.size
            zeroth_ifd[piexif.ImageIFD.Make] = u"Tadpoles"
            #,
            #  piexif.ImageIFD.XResolution: (w, 1),
            #  piexif.ImageIFD.YResolution: (h, 1),
            
            eastern = timezone('America/New_York')
            date_taken = datetime.datetime.fromtimestamp(timestamp,eastern)
            exif_ifd[piexif.ExifIFD.DateTimeOriginal] = date_taken.strftime('%Y:%m:%d %H:%M:%S%z')

            exif_dict["0th"] = zeroth_ifd
            exif_dict["Exif"] = exif_ifd
            
            #Dump to new object and return
            exif_bytes = piexif.dump(exif_dict)
            output_image = io.BytesIO()
            piexif.insert(exif_bytes,image, output_image)
            #image.save(output_image, format="JPEG", exif=exif_bytes, subsampling=0, quality=95, progressive=True)
            return output_image
        except Exception as exc:
            self.debug("Failed to process exif data")
            self.exception(exc)
            return image
        
    def write_s3(self,file, filename, mime_type, rewind=False):
        blob = self.BUCKET.blob(filename)
        blob.upload_from_file(file, rewind=rewind,content_type=mime_type)

    def save_image_api(self, key, timestamp, mime_type):
        year = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y')
        month = datetime.datetime.utcfromtimestamp(timestamp).strftime('%b')

        url = self.ROOT_URL + "remote/v1/attachment?key="+key+"&download=true"

        #Download file
        resp = requests.get(url, cookies=self.req_cookies, stream=True)
        if resp.status_code != 200:
            msg = 'Error (%r) downloading %r'
            raise DownloadError(msg % (resp.status_code, url))

        filename_parts = ['/',year, month, resp.headers['Content-Disposition'].split("filename=")[1]]
        filename = join(*filename_parts)
        
        if mime_type == 'image/jpeg':
            self.debug("Writing image" + filename)
            file = self.write_exif(resp, timestamp)
            self.write_s3(file,filename, mime_type)
        else:
            self.debug("Writing video" + filename)
            self.write_s3(resp.raw,filename, mime_type)

    def download_images(self):
        '''Login to tadpoles.com and download all user's images.
        '''
        try:
            self.load_cookies_db()
        except FileNotFoundError:
           self.navigate_url(self.ROOT_URL)
           self.do_login()
           self.dump_cookies_db()
           self.load_cookies_db()

        # Get the cookies ready for requests lib.
        self.requestify_cookies()

        self.get_api()
    
    def main(self):
        with self as client:
            try:
                client.download_images()
            except Exception as exc:
                self.exception(exc)

def download_images():
    Client().main()

if __name__ == "__main__":
    download_images()
