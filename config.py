import grequests
from twocaptcha import *
import requests

# URLs
RECAPTCHA_PAGE_URL = ""
GET_TOKEN_URL = "%RECAPTCHA_TOKEN%"
BACKLINKS_REQ_URL = ""
BACKLINKS_TASK_URL = ""
BACKLINKS_OVERVIEW_URL = "%DOMAIN%"
SITEMAP_REQ_URL = "https://%DOMAIN%/sitemap.xml"
INDEX_REQ_URL = "http://%DOMAIN%/"
TWOCAPTCHA_REQ_URL = "http://2captcha.com/in.php?key=%TWOCAPTCHA_KEY%&method=userrecaptcha&googlekey=%SITEKEY%&pageurl=%SITEURL%&json=1"
TWOCAPTCHA_RES_URL = "http://2captcha.com/res.php?key=%TWOCAPTCHA_KEY%&action=get&id=%ID%"

# Configuration
TWOCAPTCHA_KEY = ""
TWOCAPTCHA_REQ_URL = TWOCAPTCHA_REQ_URL.replace("%TWOCAPTCHA_KEY%", TWOCAPTCHA_KEY)
TWOCAPTCHA_RES_URL = TWOCAPTCHA_RES_URL.replace("%TWOCAPTCHA_KEY%", TWOCAPTCHA_KEY)
SITEKEY = ""
WEBREQUEST_TIMEOUT = 5              # Timeout for Externals Mapper
EM_MAX_EXCEPTION_COUNT = 2          # After how many exceptions shall external mapper skip a domain?
EM_MAX_TIME_FOR_DOMAIN = 30         # After how many seconds shall a domain be skipped for external link search?
BQ_NOT_YET_READY_WAIT_SECS = 10     # How much shall NotYetReady error handler wait before querying again?

solver = TwoCaptcha(TWOCAPTCHA_KEY)

HEADERS = requests.utils.default_headers()
HEADERS.update({
    "User-Agent": "Firefox",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-GPC": "1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache"
})

HEADERS_BACKLINKS = {
    "User-Agent": "Firefox",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Authorization": "empty",                        # This field is updated in getBacklinks method
    "Connection": "keep-alive",
    "Sec-GPC": "1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache"
}

BACKLINK_TASK_DATA = {"domain":"domain","mode":"domain","order_by":"domain_inlink_rank","one_per_domain": True}

# If all the values of a domain are greater than these, then discard it.
BACKLINK_DOMAIN_FILTER = {
    "domainAuthority": 90,
    "backlinks": 1000000,
    "refDomains": 1000000,
    "domainTraffic": 1000000
}

