import requests
from bs4 import BeautifulSoup
import json
from geopy.point import Point
from geopy import distance
import logging

logging.basicConfig(level=logging.DEBUG)
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


bottom = 33.775563
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
searchJSON = session.get('http://atlanta.craigslist.org/jsonsearch/apa/atl/?zoomToPosting=&catAbb=apa&query=midtown&minAsk=&maxAsk=&bedrooms=2&housing_type=&excats=').text
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

p_file = open('park.html','w')
print("Length: " + str(len(listings_s)))
for res in listings_s:
    p_file.write('<a href=\"http://atlanta.craigslist.org%s\">%s miles</a><br />' % (res[1]['PostingURL'],distance.distance(res[0], park).miles))

p_file.close()
