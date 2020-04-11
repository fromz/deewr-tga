import zeep
from zeep.wsse.username import UsernameToken
import json
import sys
import os
from deewr import qualifications, course
from woocommerce import API

wsdl = 'https://ws.staging.training.gov.au/Deewr.Tga.Webservices/TrainingComponentServiceV7.svc?wsdl'
username = 'WebService.Read'
password = 'Asdf098'

wapi_url = os.getenv('WOOCOMMERCE_API_URL')
wapi_consumer_key = os.getenv('WOOCOMMERCE_API_CONSUMER_KEY')
wapi_consumer_secret = os.getenv('WOOCOMMERCE_API_CONSUMER_SECRET')

client = zeep.Client(wsdl=wsdl, wsse=UsernameToken(username, password))
client.service.GetServerTime()

wcapi = API(
    url=wapi_url,
    consumer_key=wapi_consumer_key,
    consumer_secret=wapi_consumer_secret,
    version="wc/v3"
)

# Fetch/Cache list of qualifications
qualificationsJsonFilePath = "qualifications.json"
qualificationsIndexedByUnitPath = "qualifications-indexed-by-unit-type.json"

if not os.path.isfile(qualificationsJsonFilePath) or not os.path.isfile(qualificationsIndexedByUnitPath):
    qualifications.cache_qualifications(client, qualificationsJsonFilePath, qualificationsIndexedByUnitPath)

with open(qualificationsJsonFilePath) as f:
    qualifications = json.load(f)
with open(qualificationsIndexedByUnitPath) as f:
    qualificationsIndexedByUnitType = json.load(f)


course_fetcher = course.CourseFetcher(
    client,
    {'authorit': 'http://www.authorit.com/xml/authorit'},
    qualifications,
    qualificationsIndexedByUnitType
)

for code in sys.stdin:
    code = code.rstrip()
    try:
        course = course_fetcher.fetch_for_code(code)
    except:
        print("Exception while processing {}".format(code))
        continue

    matchingProducts = wcapi.get("products", params={"sku": code}).json()

    description = ""
    for document in course['Documents']:
        description = description + '<h1>' + document['URL'] + '</h1>'
        for book in document['Books']:
            description = description + '''
            <h1>{}</h1>
            <h2>{} - {}</h2>
            '''.format(book['PrintTitle'], book['PrintSubTitle'], book['PrintVersion'])
            for contentNode in book['ContentNodes']:
                description = description + '''
                <h3>{}</h3>
                {}
                '''.format(contentNode['PrintHeading'], contentNode['Text'])

    papi = {
        "sku": code,
        "name": course["Title"],
        "status": "draft",
        "catalog_visibility": "hidden",
        "description": description
    }
    if len(matchingProducts) == 0:
        print("Creating {} in WooCommerce".format(code))
        wcapi.post("products", data=papi)
    else:
        product = matchingProducts[0]
        print("Updating {} in WooCommerce".format(code))
        wcapi.put("products/{}".format(product['id']), data=papi).json()