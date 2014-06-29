import json
import re
from geopy.point import Point
from geopy import distance
import logging
from subprocess import Popen, PIPE, STDOUT
from email.mime.text import MIMEText
import smtplib
import dateutil.parser
import datetime
import sqlite3
import requesocks as requests
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def send_email(content,subject):
    process = Popen(['cat','gmail'], stdout=PIPE, stderr=PIPE)
    password = process.communicate()[0].decode('utf-8').strip()

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "eric.peeton@gmail.com"
    SMTP_PASSWORD = password

    EMAIL_TO = ["ea.peyton@gmail.com","louis@raffaele.us","collincun@yahoo.com"]#,"charlesmaxwellsmith@gmail.com","patricia.samartzis@gmail.com"]
    EMAIL_FROM = "eric.peeton@gmail.com"

    DATE_FORMAT = "%d/%m/%Y"
    EMAIL_SPACE = ", "

    msg = MIMEText(content, 'html')
    msg['Subject'] = subject
    msg['To'] = EMAIL_SPACE.join(EMAIL_TO)
    msg['From'] = EMAIL_FROM
    mail = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    mail.starttls()
    mail.login(SMTP_USERNAME, SMTP_PASSWORD)
    mail.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    mail.quit()

conn = sqlite3.connect('apartment.db')
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS listings(PostingID TEXT PRIMARY KEY, PostingURL TEXT, PostingTitle TEXT, Summary TEXT, PostedDate TEXT, Ask INTEGER, Bedrooms INTEGER, Latitude REAL, Longitude REAL, ImageThumb TEXT, CategoryID INTEGER)")
conn.commit()

email = ""
email_count = 0

##### Parse.py #####

session = requests.session()
headers = {'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,    image/webp,*/*;q=0.8',
         'Accept-Encoding':'gzip,deflate,sdch',
         'User-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) App    leWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36',
         'Connection':'keep-alive'}
session.headers.update(headers)

proxies = {
	"https":"socks5://127.0.0.1:9050",
	"http":"socks5://127.0.0.1:9050"
}

session.proxies.update(proxies)

attrs = { 'class': 'row',
          'data-latitude': True,
          'data-longitude': True,
        }


bottom = 33.773
right = -84.352625
left = -84.388845
top = 33.796714

park = Point(33.774582, -84.396361)
clusters = []

def parse_json(json_string):
    results = []
    listings = json.loads(json_string)
    for listing in listings[0]:
        lat = float(listing['Latitude'])
        long_ = float(listing['Longitude'])
        if lat >= bottom and lat <= top and long_ >= left and long_ <= right:
            p = Point(lat,long_)
            results.append((p,listing))
    return results

    
#searchJSON = open('search.json','r').read()
searchJSON = session.get('http://atlanta.craigslist.org/jsonsearch/apa/atl/?zoomToPosting=&catAbb=apa&query=&minAsk=&maxAsk=&bedrooms=2&housing_type=&excats=').text
search = parse_json(searchJSON)

listings = []
clusters = []
for point,result in search:
    if 'GeoCluster' in result:
        clusters.append((point,result))
    else:
        listings.append((point,result))

for point,cluster in clusters:
    clusterJSON = session.get('http://atlanta.craigslist.org' + cluster['url'] + "&bedrooms=2").text
    #clusterJSON = open('cluster.json','r').read()
    clusterSearch = parse_json(clusterJSON)
    listings += clusterSearch

listings_s = sorted(listings, key=lambda x: distance.distance(x[0],park).miles)

logging.debug("Number of listing from JSON: " + str(len(listings_s)))



####################

def exists(cursor, id):
    logging.debug('Checking if %s exists',id)
    cursor.execute("SELECT COUNT(*) FROM listings WHERE PostingID=?", (id,))
    if cursor.fetchone()[0] == 0:
        return False
    return True

def insert_listing(cursor, values):
    logging.info('New listing found! %s - %s',values['PostingTitle'].encode('utf-8'),values['PostingURL'].encode('utf-8'))
    count = len(values)
    params = tuple(values.values())
    stmnt = "INSERT INTO listings (" + ','.join(values.keys()) + ") VALUES (" + ','.join('?'*count) + ")"
    cursor.execute(stmnt,params)

def create_html_link(listing):
    if 'Ask' in listing:
        ask = "$" + str(listing['Ask']) + " - "
    else:
        ask = ""
    return "%s<a href=\"%s\">%s</a><br /><br />" % (ask, listing['PostingURL'],listing['PostingTitle'])
    
for point,listing in listings_s:
    listing['PostingURL']= 'http://atlanta.craigslist.org%s' % (listing['PostingURL'])
    listing['PostedDate'] = datetime.datetime.fromtimestamp(int(listing['PostedDate'])).isoformat()
    if not exists(cursor, listing['PostingID']):
        insert_listing(cursor, listing)
        email += create_html_link(listing)
        email_count += 1

conn.commit()

if email_count > 0:
    send_email(email, str(email_count) + " New House Listings")

html = ""
for listing in cursor.execute("SELECT PostingTitle,PostingURL,PostedDate FROM listings ORDER BY PostedDate DESC LIMIT 1000"):
    html += "<div class=\"row\">\n"
    title = listing[0]
    link = listing[1]
    post_dt = dateutil.parser.parse(listing[2]) 
    html += "<div class=\"col-md-6\"><a href=\"%s\">%s</a></div>\n" % (link, title)
    html += "<div class=\"col-md-2\">%s</div>\n" % post_dt.strftime('%b %d')
    html += "</div>\n"

conn.close()
