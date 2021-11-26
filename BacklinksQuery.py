#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import time
from config import *
import twocaptcha
import os, re
import json
from DomainData import DomainData
from functools import *
from urllib import parse
from Export import Export

CRAWL_ALREADY_DONE = "Crawl already done"
CRAWL_STARTED = "Crawl started"
CRAWL_IN_PROGRESS = "Crawl in progress"

class TokenError(Exception):
    """
    Raised when token is not useful, ie. exhausted.
    """
    def __init__(self):
        Exception.__init__(self)

class InternalServerError(Exception):
    """
    Raised when XXX gives 500.
    """
    def __init__(self):
        Exception.__init__(self)

class NotYetReady(Exception):
    """
    Raised when domain backlink task is not completed yet.
    """
    def __init__(self):
        Exception.__init__(self)

class BacklinksQuery(threading.Thread):
    """
    Queries backlinks for given domains and saves found data.
    data: is a set of DomainData having backlink information
    domains: is a set of domains to query on XXX
    reportNoFollowLinks: When True, 'onExternalSearchDomainFound' is called with no follow links. 
    Regardless of what this value is, 'data' always has no follow link data if they exist.
    exportFileName: Name of the csv file which has backlinks info
    proxies: Each used once for token request. Can be empty.
    tokens: Debug feature. Prerequested tokens goes here. Can be empty.
    
    onExternalSearchDomainFound: is a callback that is called when backlinks information arrives. 
    If it is not set, than these values are printed.
    errorCallback: Currently called only when an unexpected error occurred and the state has to be saved.
    """
    HEADERS = {"of_domain": "of_domain", "url_from": "url_from", "url_to": "url_to", "title": "title", "anchor": "anchor", "nofollow": "nofollow", "inlink_rank": "page_rank", "domain_inlink_rank": "domain_rank", "first_seen": "first_seen", "last_visited": "last_visited", "date_lost": "date_lost"}
    
    def __init__(self, domains, reportNoFollowLinks, exportFileName, proxies, tokens):
        threading.Thread.__init__(self)
        self.proxies = proxies
        self.tokens = tokens
        self.domains = set(domains)
        self._processedDomains = set()
        self.data = set()
        self.onExternalSearchDomainFound = print
        self.errorCallback = print
        self.reportNoFollowLinks = reportNoFollowLinks
        self.exporter = Export(exportFileName, BacklinksQuery.HEADERS)
        self._stopSignalReceived = False
    
    def stop(self):
        self._stopSignalReceived = True
    
    def __del__(self):
        self.exporter.close()

    def setOnExternalSearchDomainFoundCallback(self, callback):
        self.onExternalSearchDomainFound = callback

    def setErrorCallback(self, callback):
        self.errorCallback = callback

    def onBacklinkSearchDomainFound(self, domains):
        self.feed(domains)

    def feed(self, domains):
        """
        Adds domains to be queried
        """
        print("BacklinksQuery is fed")
        self.domains = self.domains.union(domains)

    def _checkDomainValiditySafe(self, domain):
        """
        Handles internal server error and token error.
        """
        try:
            return self.checkDomainValidity(domain)
        except InternalServerError:
            print("Checking domain validity gave InternalServerError. Waiting 10 seconds and trying again.")
            time.sleep(10)
            return self._checkDomainValiditySafe(domain)
        except TokenError:
            if not self._renewTokenSafely():
                raise TokenError()
            return self._checkDomainValiditySafe(domain)

    def _renewTokenSafely(self):
        try:
            self.authToken = str(self.getAuthorizationToken())
            HEADERS_BACKLINKS["Authorization"] = self.authToken
            return True
        except TokenError:
            print("Token Request has failed. Abort.")
            return False

    def run(self):
        if not self._renewTokenSafely():
            # If cannot renew, return
            return
        print("Auth Token: ", self.authToken)
        try:
            while not self._stopSignalReceived:
                toBeProcessed = self.domains.difference(self._processedDomains)
                if len(toBeProcessed) == 0:
                    print("BacklinksQuery is waiting for input")
                    time.sleep(5)
                    continue
                newExternalSearchDomains = []
                for domain in toBeProcessed:
                    shallStartTask = True
                    shallStartTask = self._startTaskIfNeededSafe(shallStartTask, domain)
                    if (not self._checkDomainValiditySafe(domain)):
                            print("Domain '%s' is filtered out." % domain)
                            continue
                    print("BacklinksQuery is looking up for %s"%domain)
                    domainBacklinks = self.getBacklinksSafe(domain, shallStartTask)
                    if domainBacklinks == None:
                        # Invalid domain, skip
                        print("Domain '%s' is being skipped."%domain)
                        continue
                    for bl in domainBacklinks:
                        bl["of_domain"] = domain
                        self.exporter.writerow(bl)                                      # Save to csv
                        if not self.reportNoFollowLinks and bl["nofollow"]:
                            continue
                        fromDomain = parse.urlparse(str(bl["url_from"])).netloc
                        newExternalSearchDomains.append(fromDomain)
                self._processedDomains = self._processedDomains.union(toBeProcessed)    # They are now processed
                if len(newExternalSearchDomains) != 0:
                    self.onExternalSearchDomainFound(newExternalSearchDomains)
        except Exception as ex:     # getBacklinksSafe may raise TokenError
            self.errorCallback(ex)

    def saveState(self, fileName):
        ext = {"domains": list(self.domains), "_processedDomains": list(self._processedDomains)}
        with open(fileName, 'w') as f:
            json.dump(ext, f)

    def loadState(self, fileName):
        with open(fileName, 'r') as f:
            state = json.load(f)
            self.domains = set(state["domains"])
            self._processedDomains = set(state["_processedDomains"])

    def _startTaskIfNeeded(self, shallStartTask, domain):
        """
        Starts the task if we need to start it
        It returns updated shallStartTask flag
        """
        if shallStartTask:
            if self.startBacklinkTask(domain) in [CRAWL_ALREADY_DONE, CRAWL_STARTED, CRAWL_IN_PROGRESS]:
                shallStartTask = False
            else:
                time.sleep(2)
        return shallStartTask
    
    def _startTaskIfNeededSafe(self, shallStartTask, domain):
        """
        Handles TokenError and InternalServerError
        """
        try:
            return self._startTaskIfNeeded(shallStartTask, domain)
        except TokenError:
            if not self._renewTokenSafely():
                raise TokenError()
        except InternalServerError:
            print("_startTaskIfNeeded gave InternalServerError. Waiting 10 seconds and trying again.")
            time.sleep(10)
            return self._startTaskIfNeededSafe(shallStartTask, domain)

    def getBacklinksSafe(self, domain, shallStartTask):
        """
        shallStartTask: If task is already done, do not start the task again.
        
        Safe, as in handles most exceptions that may occur.
        However, if token is exhausted and cannot be renewed, raises TokenError.
        
        Returns None if domain related error is found.
        Otherwise, it queries backlinks and handles TokenError, InternalServerError, NotYetReady appropriately.
        """
        domainBacklinks = None
        try:
            shallStartTask = self._startTaskIfNeededSafe(shallStartTask, domain)
            domainBacklinks = BacklinksQuery.getBacklinks(domain, self.authToken)
        except TokenError:
            try:
                self.authToken = self.getAuthorizationToken()     # Token has exceeded its capacity. Renew it.
                HEADERS_BACKLINKS["Authorization"] = self.authToken
                shallStartTask = self._startTaskIfNeededSafe(shallStartTask, domain)
                domainBacklinks = BacklinksQuery.getBacklinks(domain, self.authToken)
            except TokenError:
                # We renewed the token yet it is still not useful. Abort. 
                self.errorCallback("BacklinksQuery could not get a valid token. Abort.")
                raise TokenError()
            except InternalServerError:
                print("XXX has given InternalServerError. Retrying in 10 seconds.")
                time.sleep(10)
                return self.getBacklinksSafe(domain, True)
            except NotYetReady:
                print("NotYetReady error received. Waiting for %s seconds and retrying without restarting task." % BQ_NOT_YET_READY_WAIT_SECS)
                time.sleep(BQ_NOT_YET_READY_WAIT_SECS)
                try:
                    #shallStartTask = self._startTaskIfNeeded(True, domain)
                    domainBacklinks = self.getBacklinksSafe(domain, False)
                except NotYetReady:
                    print("ERROR: A second NotYetReady error is received for domain '%s'. Skipping.", domain)
        except InternalServerError:
            print("XXX has given InternalServerError. Retrying in 10 seconds.")
            time.sleep(10)
            shallStartTask = self._startTaskIfNeededSafe(shallStartTask, domain)
            return self.getBacklinksSafe(domain, True)
        except NotYetReady:
            print("NotYetReady error received. Waiting for %s seconds and retrying without restarting task." % BQ_NOT_YET_READY_WAIT_SECS)
            time.sleep(BQ_NOT_YET_READY_WAIT_SECS)
            try:
                #shallStartTask = self._startTaskIfNeeded(True, domain)
                domainBacklinks = self.getBacklinksSafe(domain, False)
            except NotYetReady:
                print("ERROR: A second NotYetReady error is received. Skipping.")
        return domainBacklinks

    def startBacklinkTask(self, domain):
        """
        Starts backlink task. This allows getting backlink overview and backlink queries.
        In turn that allows checkDomainValidity method.
        
        Returns
        CRAWL_ALREADY_DONE, CRAWL_STARTED, CRAWL_IN_PROGRESS: Do not start the task for this domain again
        True: Returned 200
        Otherwise raises relevant exception
        """
        BACKLINK_TASK_DATA["domain"] = domain
        resp = requests.post(BACKLINKS_TASK_URL, headers=HEADERS_BACKLINKS, json=BACKLINK_TASK_DATA)
        print("DEBUG Domain: '%s', Task Response: " % domain, resp.text)
        obj = json.loads(resp.text)
        try:
            # Returns one of
            # CRAWL_ALREADY_DONE, CRAWL_STARTED, CRAWL_IN_PROGRESS
            return obj["status"]
        except KeyError:
            pass
        if resp.status_code == 200:
            return True
        elif resp.status_code == 429:
            print("DEBUG: Token expired at startBacklinkTask call")
            raise TokenError()
        else:
            print("ERROR: Task start request returned status code %s. Details:" % resp.status_code)
            print(resp.text)
            raise Exception()
        

    def getBacklinkOverview(self, domain):
        """
        Requires backlink task to have been started.
        
        Returns
        {"domainAuthority": 1, "backlinks": 2, "refDomains": 3, "refDomainsGovEdu": 4, "follow": 5, "noFollow": 6, "domainTraffic": 7}
        """
        url = BACKLINKS_OVERVIEW_URL.replace("%DOMAIN%", domain)
        resp = requests.get(url, headers=HEADERS_BACKLINKS)
        if resp.status_code == 200:
            obj = json.loads(resp.text)
            return obj
        elif resp.status_code == 500 or resp.status_code == 502:
            raise InternalServerError()
        else:
            print("ERROR: Overview request returned status code %s. Details:" % resp.status_code)
            print(resp.text)
            raise Exception()

    def checkDomainValidity(self, domain):
        """
        Uses getBacklinkOverview. Thus it requires backlink task to have been started.
        """
        overview = self.getBacklinkOverview(domain)
        if overview["domainAuthority"] < BACKLINK_DOMAIN_FILTER["domainAuthority"]:
            return True
        if overview["backlinks"] < BACKLINK_DOMAIN_FILTER["backlinks"]:
            return True
        if overview["refDomains"] < BACKLINK_DOMAIN_FILTER["refDomains"]:
            return True
        if overview["domainTraffic"] < BACKLINK_DOMAIN_FILTER["domainTraffic"]:
            return True
        return False

    def getAuthorizationToken(self):
        # If we have tokens supplied, use them for debugging purposes.
        if len(self.tokens) != 0:
            print("DEBUG: Using user supplied token")
            return self.tokens.pop()
        print("Requesting recaptcha token")
        recaptcha_token = BacklinksQuery.requestReCaptchaV2Token()
        print("Requesting authorization token")
        if len(self.proxies) != 0:
            proxy = self.proxies.pop()
            print("Using proxy for token request: ", proxy)
            return BacklinksQuery.requestAuthorizationToken(recaptcha_token, proxy)
        else:
            print("Requesting token via our IP")
            return BacklinksQuery.requestAuthorizationToken(recaptcha_token)
    
    @staticmethod
    def requestAuthorizationToken(recaptcha_token, proxy=None):
        """
        Requests bearer authorization token
        Optionally you can provide a proxy
        """
        url = GET_TOKEN_URL.replace("%RECAPTCHA_TOKEN%", recaptcha_token)
        if proxy != None:
            resp = requests.get(url, headers=HEADERS, proxies=proxy)
        else:
            resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 403:
            # It is a web token
            obj = json.loads(resp.text)
            regexp = re.compile("The token (.+?) is already registered.")
            print ("Web token found")
            return "Bearer " + regexp.search(obj["description"]).group(1)
        elif resp.status_code == 500:
            raise InternalServerError()
        elif resp.status_code != 200:
            print("""Requesting authorization token resulted in status code %s."""%resp.status_code)
            print("Response: ", str(resp.text.encode("utf8")))
            raise TokenError()
        obj = json.loads(resp.text)
        bearerToken = "Bearer " + obj["token"]
        return bearerToken

    @staticmethod
    def getBacklinks(domain, authToken):
        """
        Queries XXX for backlinks
        Throws TokenError if an error related to token is found.
        Returns None if an error related to requested domain was found.
        
        Requires backlink task to have been started.
        """
        url = BACKLINKS_REQ_URL.replace("%DOMAIN%", domain)
        HEADERS_BACKLINKS["Authorization"] = authToken
        resp = requests.get(url, headers=HEADERS_BACKLINKS)
        if resp.status_code == 400:
            obj = json.loads(resp.text)
            if obj["description"] == "Task was not started":
                print("ERROR: Task has not started found. Retrying.")
                raise NotYetReady()
            print("""Querying backlinks for domain "%s" resulted in status code %s."""%(domain, resp.status_code))
            print("Details: ", resp.text)
            print("Assuming this is related to domain, this domain is being skipped.")
            return None
        elif resp.status_code == 429:
            print("""Querying backlinks for domain "%s" resulted in status code %s."""%(domain, resp.status_code))
            print("Assuming TOO_MANY_REQUEST error, aborting.")
            raise TokenError()
        if resp.status_code != 200:
            print("""Querying backlinks for domain "%s" resulted in status code %s."""%(domain, resp.status_code))
            print("More information:")
            print(str(resp.text.encode("utf8")))
            raise TokenError()
        result = json.loads(resp.text)
        try:
            l = result["backlinks"]
            if len(l) != 0:
                return l
            elif result["done"] == False:
                # We need to request the task to be started and
                # query again
                print("NotYetReady error is thrown")
                raise NotYetReady()
            return l
        except NotYetReady as ex:
            raise ex
        except:
            # Old way
            print("DEBUG: Backlinks returned by the old way. Details:")
            print(result)
            return result

    @staticmethod
    def requestReCaptchaV2Token(attempt=0):
        try:
            res = solver.recaptcha(sitekey=SITEKEY, url=RECAPTCHA_PAGE_URL)
            print("Captcha solved at attempt ", str(attempt))
            print("Recaptcha response: ", res)
            return res["code"]
        except ValidationException as e:
	        print("ValidationException: ", e)
        except twocaptcha.api.NetworkException as e:
	        print("NetworkException: ", e)
        except twocaptcha.api.ApiException as e:
            print("ApiException: ", e)
        except twocaptcha.api.TimeoutException as e:
            # captcha is not solved yet
            print("Timeout Exception: ", e)
            print("Sleeping for 5 seconds and trying again.")
            time.sleep(5)
            return requestReCaptchaV2Token(attempt+1)
        return ""
