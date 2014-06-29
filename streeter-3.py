#!/Library/Frameworks/Python.framework/Versions/3.4/bin/python3
import urllib.parse
from bs4 import BeautifulSoup
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
import pprint
import feedparser
import concurrent.futures
import sqlite3
import requests
logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def send_email(content,subject):
    process = Popen(['cat','/Users/eric/Development/Apartment/gmail'], stdout=PIPE, stderr=PIPE)
    password = process.communicate()[0].decode('utf-8').strip()

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "eric.peeton@gmail.com"
    SMTP_PASSWORD = password

    EMAIL_TO = ["ea.peyton@gmail.com"]
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

aliases = {
            "st" : "street",
            "ave" : "avenue",
            "dr" : "drive",
            "pl" : "place",
            "cir" : "circle",
            "blvd" : "boulevard",
            "ct" : "court",
            "hwy" : "highway",
            "lane" : "lane",
            "rd" : "road"
          }

r = requests.get('https://docs.google.com/document/d/1KdsJkx6_rmzAtnzRSKuzviv8-vL8_dfdZcasAPeoQZg/export?format=txt')

streets = []
below_line = False
for line in r.text.split('\r\n'):
    if below_line and not line.startswith('#'):
        streets.append(line)
    if line.startswith('==='):
        below_line = True
searchTerms = []
for street in streets:
    stops = ''
    if '-' in street:
        stops = ' -' + '-'.join(['"' + stop.rstrip() + '"' for stop in street.split('-')[1:]])
    street = '"' + street.split('-')[0].rstrip() + '"' + stops
    searchTerms.append(street)
    aliasStreet = street
    for alias in aliases:
        aliasStreet = aliasStreet.replace(' ' + alias, ' ' + aliases[alias])
    if aliasStreet != street:
        searchTerms.append(aliasStreet)

searches = []
search = ""
for term in searchTerms:
    if(len(search) + len(term)) > 180:
        searches.append(search[:-1])
        search = ""
    search += term + '|'
searches.append(search[:-1])

urls = []
for search in searches:
    urls.append("http://atlanta.craigslist.org/search/apa/atl?bedrooms=3&catAbb=apa&query=" + search.replace('|', '%7C').replace(' ','%20') + "&s=0&format=rss")

conn = sqlite3.connect('/Users/eric/Development/Apartment/apartment-3.db')
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS listings(PostingID TEXT PRIMARY KEY, PostingURL TEXT, PostingTitle TEXT, Summary TEXT, PostedDate TEXT, Ask INTEGER, Bedrooms INTEGER, Latitude REAL, Longitude REAL, ImageThumb TEXT, CategoryID INTEGER)")
conn.commit()

email = ""
email_count = 0

pp = pprint.PrettyPrinter(indent=4)

##### Parse.py #####

session = requests.session()
headers = {'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,    image/webp,*/*;q=0.8',
         'Accept-Encoding':'gzip,deflate,sdch',
         'User-agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) App    leWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36',
         'Connection':'keep-alive'}
session.headers.update(headers)

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
searchJSON = session.get('http://atlanta.craigslist.org/jsonsearch/apa/atl/?zoomToPosting=&catAbb=apa&query=midtown&minAsk=&maxAsk=&bedrooms=3&housing_type=&excats=').text
search = parse_json(searchJSON)

listings = []
clusters = []
for point,result in search:
    if 'GeoCluster' in result:
        clusters.append((point,result))
    else:
        listings.append((point,result))

for point,cluster in clusters:
    clusterJSON = session.get('http://atlanta.craigslist.org' + cluster['url']).text
    #clusterJSON = open('cluster.json','r').read()
    clusterSearch = parse_json(clusterJSON)
    listings += clusterSearch

'''
for point,listing in listings:
    print(listing['PostingID'])'''

listings_s = sorted(listings, key=lambda x: distance.distance(x[0],park).miles)

p_file = open('/Users/eric/Development/Apartment/park.html','w')
logging.debug("Number of listing from JSON: " + str(len(listings_s)))
for res in listings_s:
    p_file.write('<a href=\"http://atlanta.craigslist.org%s\">%s miles</a><br />' % (res[1]['PostingURL'],distance.distance(res[0], park).miles))

p_file.close()



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

#def insert_listing(cursor, id, link, title, summary="", post_dt=""):
#    cursor.execute("INSERT INTO listings VALUES (?,?,?,?,?)", (id, link, title, summary, post_dt))
   
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

for url in urls:
    logging.info('Parsing RSS URL %s',url)
    feed = feedparser.parse(url)
    for item in feed['items']:
        ilisting = {}
        ilisting['PostingID'] = re.match('http://atlanta\.craigslist\.org/atl/apa/(\d+)\.html',item['id']).group(1)
        ilisting['PostingURL'] = item['link']
        ilisting['PostingTitle'] = item['title']
        ilisting['Summary'] = item['summary']
        ilisting['PostedDate'] = item['published']
        if not exists(cursor, ilisting['PostingID']):
            insert_listing(cursor, ilisting)
            email += create_html_link(ilisting)
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

results = open('/Users/eric/Development/Apartment/results.html','w')

results.write("""
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <link rel="stylesheet" href="http://netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css">
                </head>
                        <body>
                            <h1>BigCraig</h1>
                                <div class="container table-responsive">
                                    %s
                                </div>
                        </body>
            </html>
            """ % html.encode('utf-8'))

results.close()
