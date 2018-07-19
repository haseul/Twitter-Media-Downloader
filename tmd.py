import urllib.request
import threading
import tweepy
import queue
import math
import time
import sys
import re
import os


def parse_arguments():
    global twitter_folder
    # global high_quality
    global word_filter
    # global reply_links
    global previews
    global handle
    global words

    url_arg = False
    previews = False
    word_filter = False
    twitter_folder = False

    if len(sys.argv) < 2:
        input('No arguments given\n'
              'Press Enter to continue: ')
        sys.exit()

    for index, arg in enumerate(sys.argv):
        arg = arg.strip()

        url_match = re.search('^(https?://(?:www\.)?twitter\.com/[^\s/]+)/?(?:media)?$', arg, flags=re.I)
        if url_match:
            try:
                urllib.request.urlopen(url_match.group(1))
                url_arg = True
                handle = url_match.group(1).split("/")[-1]
            except urllib.request.HTTPError as e:
                input('\n' +
                      str(e) + ' \n'
                      'Press Enter to continue: ')
                sys.exit()

        # elif arg == '-hqr':
        #     high_quality = True
        #     reply_links = True

        # elif arg == '-hq':
        #     high_quality = True

        elif arg == '-t':
            twitter_folder = True

        elif arg == '-p':
            previews = True

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
        try:
            handle = sys.argv[1]
            urllib.request.urlopen("https://twitter.com/" + handle.strip())
        except urllib.request.HTTPError:
            input('\n'
                  'Error: No Twitter user given or the Twitter user specified does not exist.\n'
                  'Press Enter to continue: ')
            sys.exit()


def parse_carriage():
    global parse_carr
    parse_carr = True
    p = 0
    while parse_carr:
        progress = int(math.ceil(p / 10))
        text = "Parsing Images" + ("." * progress)
        print(text, end="\r")
        time.sleep(0.05)
        p += 1
        if p > 30:
            p = 1


def dl_carriage():
    global dl_carr
    dl_carr = True
    p = 0
    while dl_carr:
        progress = int(math.ceil(p / 10))
        text = "Downloading Images"+ ("." * progress) + (" " * (9 - progress)) + "Images Processed: " + str(total_imgs) + (" " * (9 - len(str(total_imgs)))) + "Images Downloaded: " + str(imgs_downloaded)
        print(text, end="\r")
        time.sleep(0.05)
        p += 1
        if p > 30:
            p = 1


def main():
    global Lock1
    global dl_carr
    global parse_q
    global get_carr
    global download_q
    global parse_carr
    global date_replace

    parse_q = queue.Queue()
    download_q = queue.Queue()
    Lock1 = threading.Lock()

    global imgs_already_saved
    global imgs_downloaded
    global imgs_repaired
    global total_imgs
    global imgs_found
    global errors

    errors = 0
    total_imgs = 0
    imgs_found = 0
    imgs_repaired = 0
    imgs_downloaded = 0
    imgs_already_saved = 0

    date_replace = {
        "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
        "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
        "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
    }

    parse_arguments()

    auth = tweepy.OAuthHandler('consumer_key', 'consumer_secret')
    auth.set_access_token('access_token', 'access_token_secret')
    api = tweepy.API(auth)

    global get_tweets
    def get_tweets():
        for status in tweepy.Cursor(api.user_timeline, screen_name=handle, count=200, include_rts=False).items():
            status = status._json
            if "extended_entities" in status and "media" in status["extended_entities"] and len(
                    status["extended_entities"]["media"]) > 0:
                tweet_dict = {
                    "media": [m["media_url_https"] for m in status["extended_entities"]["media"] if
                              "https://pbs.twimg.com/media/" in m["media_url_https"]],
                    "screen_name": status["user"]["screen_name"],
                    "created_at": status["created_at"],
                    "text": status["text"]
                }
                yield tweet_dict

    print()
    threading.Thread(target=parse_carriage, daemon=True).start()
    parse()
    parse_carr = False
    print()

    print()
    threading.Thread(target=dl_carriage, daemon=True).start()
    threads = [threading.Thread(target=download, daemon=True) for _ in range(32)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    dl_carr = False
    print()
    print()

    print("\nImages Processed: " + str(total_imgs) + "/" + str(imgs_found))
    print("Images Downloaded: " + str(imgs_downloaded))
    print("Images Repaired: " + str(imgs_repaired))
    print("Images Already Saved: " + str(imgs_already_saved))
    print("Errors: " + str(errors))


def parse():
    global download_q
    global imgs_found

    for tweet in get_tweets():
        path = []
        parse_imgs = True

        if twitter_folder:
            path.append(tweet["screen_name"])

        if word_filter:
            word_found = False
            for word in words:
                if word.lower() in tweet["text"].lower():
                    word_found = True
                    break
            if not word_found:
                parse_imgs = False

        if previews:
            for word in ["프리뷰", "샘플사진", "preview"]:
                if word in tweet["text"].lower():
                    path.append("Preview")
                    break
        elif previews is False:
            for word in ["프리뷰", "샘플사진", "preview"]:
                if word in tweet["text"].lower():
                    parse_imgs = False
                    break

        if parse_imgs:
            text = tweet["text"]
            date_match = re.search('(?:\D|^)((\d\d[0-1]\d[0-3]\d|\d{6}|(?:\d{1,4}\.|\d{1,4}/|\d{1,4}:){3})[\s\n]'
                                   '.*?)(?:\n|$)', text)
            if date_match:
                date = date_match.group(2).strip()
                date_event = date_match.group(1).strip()
                date_event = re.sub('https?://\S+', '', date_event)
                date_event = re.sub('#\S*', '', date_event)
                date_event = re.sub('\n', ' ', date_event)
                for char in '\/:*?"<>|.;()[]':
                    date_event = date_event.replace(char, '')
                date_event = re.sub('\s{2,}', ' ', date_event).strip()
                path.append(date)
                path.append(date_event)
            else:
                date = tweet["created_at"].split()
                year = date[-1][-2:]
                month = date[1]
                for key, val in date_replace.items():
                    if key in month.capitalize():
                        month = month.replace(key, val)
                        break
                day= date[2]

                date = year + month + day

                path.append("Uploaded On")
                path.append(date)

            img_path = os.path.join(*path)

            for img in tweet["media"]:
                imgs_found += 1
                img_dict = {
                    "img": img.replace(".jpg", ".jpg:orig"),
                    "filename" : img.split("/")[-1],
                    "path": img_path,
                }
                download_q.put(img_dict)


def download():
    global imgs_already_saved
    global imgs_downloaded
    global imgs_repaired
    global total_imgs
    global errors

    while download_q.qsize() > 0:
        data = download_q.get()

        with Lock1:
            if not os.path.exists(data["path"]):
                    os.makedirs(os.path.join(data["path"]))

        if not os.path.exists(os.path.join(data["path"], data["filename"])):
            try:
                urllib.request.urlretrieve(data["img"], os.path.join(data["path"], data["filename"]))
                imgs_downloaded += 1
                total_imgs += 1
            except Exception:
                errors += 1
        else:
            img_data = urllib.request.urlopen(data["img"])
            with open(os.path.join(data["path"], data["filename"]), 'rb') as ims:
                img_size = len(ims.read())

            if int(img_size) != int(img_data.info()['Content-Length']):
                try:
                    urllib.request.urlretrieve(data["img"], os.path.join(data["path"], data["filename"]))
                    imgs_repaired += 1
                    total_imgs += 1
                except Exception:
                    errors += 1
            else:
                imgs_already_saved += 1
                total_imgs += 1


if __name__ == "__main__":
    main()
