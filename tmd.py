from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup
import urllib.request
import urllib.error
import threading
import queue
import math
import time
import sys
import re
import os

replace_dict = {
    r"\xa0": " ",  r"\xc2": " ",   "<br>": "\n",  "<wbr>": "",
     "&gt;": ">", "&#039;": "\"", "&#39;": "\"", "&#034;": "\"",
    "&#34;": "\"", "&amp;": "&", "&#038;": "&",   "&#38;": "&"
}

date_dict = {
    "jan": '01', "feb": '02', "mar": '03',
    "apr": '04', "may": '05', "jun": '06',
    "jul": '07', "aug": '08', "sep": '09',
    "oct": '10', "nov": '11', "dec": '12'
}

extension_dict = {
    ".jpg": ".jpg:orig",
    ".png": ".png:orig"
}

Lock1 = threading.Lock()
img_q = queue.Queue()
parse_q = queue.Queue()
filter_list = []

imgs_downloaded = 0
imgs_repaired = 0
scroll_iter = 0
imgs_found = 0
total_imgs = 0

head = False
keyword = False
previews = False
reply_links = False
word_filter = False
high_quality = False
twitter_folder = False


def main():
    global scroll_carriage
    global parse_carriage
    global dl_carriage
    scroll_carriage = False
    parse_carriage = True
    dl_carriage = True

    parse_arguments()

    html = get(url_entered)
    scroll_carriage = False

    threading.Thread(target=parse_carr, daemon=True).start()
    parse(html)
    parse_carriage = False

    threading.Thread(target=download_carr, daemon=True).start()
    dl_threads = [threading.Thread(target=download, daemon=True) for _ in range(32)]
    for dl_thread in dl_threads:
        dl_thread.start()
        time.sleep(0.05)
    for dl_thread in dl_threads:
        dl_thread.join()
    dl_carriage = False

    time.sleep(0.5)

    print('\n\n\nDone!\n'
          '\nImages found: ' + str(imgs_found) +
          '\nImages processed: ' + str(total_imgs) +
          '\nImages downloaded: ' + str(imgs_downloaded) +
          '\nImages repaired: ' + str(imgs_repaired) +
          '\nImages already downloaded: ' + str(total_imgs - (imgs_downloaded + imgs_repaired)))


def replace(text, dict):
    for key, val in dict.items():
        text = text.replace(key, val)
    return text


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def parse_arguments():
    global twitter_folder
    global twitter_handle
    global word_filter
    global reply_links
    global url_entered
    global previews
    global words
    global head
    global high_quality
    url_arg = False

    if len(sys.argv) < 2:
        input('No arguments given\n'
              'Press Enter to continue ')
        sys.exit()

    for index, arg in enumerate(sys.argv):
        arg = arg.strip()

        if re.search('https?://(?:www\.)?twitter\.com/\S*', arg):
            try:
                urllib.request.urlopen(arg)
                url_arg = True
                url_entered = arg
            except urllib.error.HTTPError as e:
                input('\n' +
                      str(e) + ' \n'
                      'Press Enter to continue: ')
                sys.exit()

        elif arg == '-hqr':
            high_quality = True
            reply_links = True

        elif arg == '-hq':
            high_quality = True

        elif arg == '-t':
            twitter_folder = True
            try:
                twitter_handle = sys.argv[index + 1]
            except IndexError:
                input('\n'
                      'Error: No word(s) supplied to the title "-t" argument\n'
                      'Press Enter to continue: ')
                sys.exit()

        elif arg == '-p':
            previews = True

        elif arg == '-h':
            head = True

        elif arg == '-f':
            word_filter = True
            try:
                words = sys.argv[index + 1].split('/')
            except IndexError:
                input('\n'
                      'Error: No word(s) supplied to the filter "-f" argument\n'
                      'Press Enter to continue: ')
                sys.exit()

    if not url_arg:
        input('\n'
              'Error: No URL supplied\n'
              'Press Enter to continue: ')
        sys.exit()


def get(url, waittime=2):
    global scroll_iter
    global imgs_found
    global scroll_carriage

    options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    if not head:
        options.add_argument('headless')
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(chrome_options=options)
    driver.get(url)
    cls()
    scroll_carriage = True
    threading.Thread(target=scroll_carr, daemon=True).start()

    wait = WebDriverWait(driver, waittime)

    # username = selenium.find_element_by_id("username")
    # password = selenium.find_element_by_id("password")
    #
    # username.send_keys("YourUsername")
    # password.send_keys("Pa55worD")
    #
    # selenium.find_element_by_name("submit").click()

    last_height = driver.execute_script("return document.body.scrollHeight")
    time.sleep(2)
    while True:
        err = 0

        while err < 3:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                try:
                    wait.until(EC.visibility_of_element_located(
                        (By.XPATH, "//*[@id=\"timeline\"]/div/div[2]/div[1]/div/div[2]/div/span")))
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    scroll_iter += 1
                    err = 0
                    time.sleep(waittime)
                    last_height = new_height
                except TimeoutException:
                    err += 1

            else:
                scroll_iter += 1
                err = 0
                time.sleep(waittime)
                last_height = new_height

        break

    html = driver.execute_script("return document.body.innerHTML")
    driver.quit()

    return html


def scroll_carr():
    i = 1

    time.sleep(1)
    print()

    while scroll_carriage:
        print('Getting Images' + ('.' * int(math.ceil(i / 10))) + (' ' * ((3 - int(math.ceil(i / 10))) + 16)) + \
               'Scrolls performed: ' + str(scroll_iter), end='\r')
        i += 1
        if i > 30:
            i = 1
        time.sleep(0.05)

    print('Finished Getting Images.' + (' ' * 9) + \
          'Scrolls performed: ' + str(scroll_iter))


def parse_carr():
    i = 1

    time.sleep(1)
    print()

    while parse_carriage:
        print('Parsing Images' + ('.' * int(math.ceil(i / 10))) + (' ' * ((3 - int(math.ceil(i / 10))) + 16)) + \
              'Images Found: ' + str(imgs_found), end='\r')
        i += 1
        if i > 30:
            i = 1
        time.sleep(0.05)

    print('Finished Parsing Images.' + (' ' * 9) + \
          'Images Found: ' + str(imgs_found))


def download_carr():
    i = 1

    time.sleep(1)
    print()

    while dl_carriage:
        print('Downloading Images' + ('.' * int(math.ceil(i / 10))) + (' ' * ((3 - int(math.ceil(i / 10))) + 12)) + \
              'Images Processed: ' + str(total_imgs) + (' ' * (12 - len(str(total_imgs)))) + 'Images Downloaded: ' +
              str(imgs_downloaded), end='\r')
        i += 1
        if i > 30:
            i = 1
        time.sleep(0.05)

    print('Finished Downloading Images.' + (' ' * 5) + 'Images Processed: ' + str(total_imgs) +
          (' ' * (12 - len(str(total_imgs)))) + 'Images Downloaded: ' + str(imgs_downloaded))


def parse(html):
    global parse_carriage
    global preview_folder
    global title
    preview_folder = ''
    title = ''

    parse_carriage = True
    soup = BeautifulSoup(html, 'html.parser')
    tweets = soup.find_all('li', class_=re.compile(".*?js-stream-item.*"))

    if twitter_folder:
        title = twitter_handle

    for tweet in tweets:
        parse_q.put(tweet)

    parse_threads = [threading.Thread(target=parse_images, daemon=True) for _ in range(16)]
    for parse_thread in parse_threads:
        parse_thread.start()
        time.sleep(0.1)
    for parse_thread in parse_threads:
        parse_thread.join()


def parse_images():
    global imgs_found
    global preview_folder

    while parse_q.qsize() > 0:
        tweet = parse_q.get()
        tweet_id = tweet['data-item-id']
        parse_imgs = True
        word_found = False

        tweet_soup = BeautifulSoup(str(tweet), 'html.parser')
        tweet_path = tweet_soup.find('div', class_=re.compile(".*?tweet js-stream-tweet.*"))['data-permalink-path']
        tweet_screen_name = tweet_soup.find('div', class_=re.compile(".*?tweet js-stream-tweet.*"))['data-screen-name']
        image_container = tweet_soup.find('div', class_="AdaptiveMedia-container")

        if image_container is not None and len(image_container) > 0:
            text = str(tweet_soup.find('div', class_="js-tweet-text-container"))

            text = ''.join(re.findall(re.compile('>([^<]+)(?:<|$)'), text))

            if word_filter:
                for word in words:
                    if word.lower() in text.lower():
                        word_found = True
                        break
                if word_found is not True:
                    parse_imgs = False

            if previews:
                for word in ["프리뷰", "샘플사진", "preview"]:
                    if word in text.lower():
                        preview_folder = 'Preview'
                        break
            elif previews is False:
                for word in ["프리뷰", "샘플사진", "preview"]:
                    if word in text.lower():
                        parse_imgs = False
                        break

            if parse_imgs:
                links_found = re.findall('(https?://\S*)', text, flags=re.I)
                for link_found in links_found:
                    text = text.replace(' ' + link_found, '\n')
                    text = text.replace(link_found + ' ', '\n')
                    text = text.replace(link_found, '\n')

                try:
                    date_full = re.findall('(?:\D|^)((\d\d[0-1]\d[0-3]\d\s|\d{6}\s|\D(?:\d{1,4}\.|\d{1,4}/|\d{1,4}:){3})[^\r\n]*)', text)[0]
                    date = date_full[1].strip()
                    date_event = date_full[0].strip()
                    for char in '\/:*?"<>|.;()[]':
                        date_event = date_event.replace(char, '')
                    date_event = re.sub('#\S*', '', date_event)
                    date_event = re.sub('\s{2,}', ' ', date_event)
                    date_event = os.path.join(title, date, replace(date_event, replace_dict).strip(), preview_folder)
                except IndexError:
                    date_full = tweet_soup.find('small', class_="time").find('a', href=re.compile('/.*?/status/\d+'))[
                        "title"]
                    date_event = date_full.split('-')[1].strip().split(' ')
                    day = date_event[0]
                    month = date_event[1].lower()
                    for key, val in date_dict.items():
                        month = month.replace(key, val)
                    year = date_event[2][-2:]
                    if len(day) < 2:
                        date_event = year + month + '0' + day
                    elif len(day) > 1:
                        date_event = year + month + day
                    date_event = os.path.join(title, "Uploaded On", date_event, preview_folder)

                images = tweet_soup.find_all('img')
                for image in images:
                    if re.search('/media/.*?\.(?:jpg|png)', image['src']):
                        img = replace(image['src'], extension_dict)
                        filename = image['src'].split('/')[-1]
                        filename = urllib.request.url2pathname(filename.encode('latin1').decode('utf8'))
                        info_dict = {
                            "img": img,
                            "date": date_event.strip(),
                            "filename": filename.strip()
                        }
                        imgs_found += 1
                        img_q.put(info_dict)

                if high_quality:
                    if reply_links:
                        opened_tweet = urllib.request.urlopen('https://twitter.com' + tweet_path).read().decode('utf-8')
                        opened_tweet_soup = BeautifulSoup(opened_tweet, 'html.parser')

                        replies = str(opened_tweet_soup.find('div', class_=re.compile(".*?replies-to.*")))
                        replies_soup = BeautifulSoup(replies, 'html.parser')

                        reply_tweets = replies_soup.find_all('li', class_=re.compile(".*?js-stream-item.*"))
                        for reply_tweet in reply_tweets:
                            reply_soup = BeautifulSoup(str(reply_tweet), 'html.parser')
                            reply_screen_name = reply_soup.find('div', class_=re.compile(".*?tweet js-stream-tweet.*"))['data-screen-name']
                            if reply_screen_name == tweet_screen_name:
                                reply_text = str(reply_soup.find('div', class_="js-tweet-text-container"))
                                reply_text_parsed = re.findall(re.compile('>([^<]+)(?:<|$)'), reply_text)
                                reply_text = ''
                                for reply_chars in reply_text_parsed:
                                    reply_text += reply_chars
                                for reply_link in re.findall('(https?://\S*)', reply_text, flags=re.I):
                                    links_found.append(reply_link)

                    def get_hq_links():
                        for link in links_found:
                            try:
                                link_data = urllib.request.urlopen(link)
                                if "image" in link_data.info()["Content-Type"] and 'twitter' not in link.split('/')[0].lower():
                                    yield (link, link_data)
                            except urllib.error.HTTPError:
                                pass

                    for hq_img in get_hq_links():
                        try:
                            filename_found = hq_img[1].info()["Content-Disposition"].split('filename="')[1].split('"')[0]
                            if len(filename_found) > 0:
                                filename = filename_found
                            else:
                                filename = hq_img[0].split('/')[-1]
                        except Exception:
                            filename = hq_img[0].split('/')[-1]

                        img = hq_img[0].replace('tistory.com/image/', 'tistory.com/original/')
                        date = os.path.join(date_event.strip(), "HQ")
                        filename = urllib.request.url2pathname(filename.encode('latin1').decode('utf8'))
                        info_dict = {
                            "img": img,
                            "date": date,
                            "filename": filename.strip()
                        }
                        imgs_found += 1
                        img_q.put(info_dict)



def download():
    global total_imgs
    global imgs_repaired
    global imgs_downloaded
    global dl_carriage
    dl_carriage = True

    while img_q.qsize() > 0:
        data = img_q.get()

        if data is None:
            break
        with Lock1:
            if not os.path.exists(data["date"]):
                    os.makedirs(os.path.join(data["date"]))

        if not os.path.exists(os.path.join(data["date"], data["filename"])):
            urllib.request.urlretrieve(data["img"], os.path.join(data["date"], data["filename"]))
            imgs_downloaded += 1
            total_imgs += 1
        else:
            img_data = urllib.request.urlopen(data["img"])
            with open(os.path.join(data["date"], data["filename"]), 'rb') as ims:
                img_size = len(ims.read())

            if int(img_size) != int(img_data.info()['Content-Length']):
                urllib.request.urlretrieve(data["img"], os.path.join(data["date"], data["filename"]))
                imgs_repaired += 1
                total_imgs += 1
            else:
                total_imgs += 1

if __name__ == '__main__':
    main()
