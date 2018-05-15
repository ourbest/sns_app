import requests

api_url = 'http://restapi.amap.com/v3/'
api_key = 'c07b9ca722d021eea64a4e3396fc0499'


def call_lbs_api(api, **kwargs):
    return requests.get("%s%s?key=%s" % (api_url, api, api_key), kwargs).json()


def get_center(city):
    result = call_lbs_api('config/district', subdistrict=0, keywords=city)
    # result = requests.get(api_url + 'config/district?key=' + api_key + '&subdistrict=0&keywords=' + city).json()
    if result['districts']:
        return result['districts'][0]['center']
