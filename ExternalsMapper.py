#!/usr/bin/env python
# -*- coding: utf-8 -*-
import threading
import time
from config import *
import twocaptcha
import os, re
from bs4 import BeautifulSoup
import json
from DomainData import DomainData
from functools import *
from urllib import parse
import urllib
from Export import Export
import lxml
from Utils import *

class TooManyExceptionsError(Exception):
    def __init__(self):
        Exception.__init__(self)

class ExternalsMapper(threading.Thread):
    """
    Searches external links for given domains and saves found data.
    data: is a set of DomainData having external link information
    domains: is a set of domains to search external links on
    onBacklinkSearchDomainFound: is a callback that is called when new external links are found.
    If not set, domains are printed instead.
    exLinkLimit: When -1, there is no limit. Otherwise when 'exLinkLimit' many external link found or
    when our resources are exhausted, external link search for that domain finishes.
    exportFileName: Name of the csv file which has external links info
    
    errorCallback: Currently called only when an unexpected error occurred and the state has to be saved.
    """
    
    FIELDNAMES = ["of_domain", "url_to"]
    MAX_EXCEPTION_COUNT = EM_MAX_EXCEPTION_COUNT
    
    def __init__(self, domains, exLinkLimit, exportFileName):
        threading.Thread.__init__(self)
        self.domains = set(domains)
        self.data = set()
        self._processedDomains = set()
        self.onBacklinkSearchDomainFound = print
        self.errorCallback = print
        self.exLinkLimit = exLinkLimit
        self.exporter = Export(exportFileName, ExternalsMapper.FIELDNAMES)
        self.exceptionCount = 0
        self._stopSignalReceived = False
    
    def stop(self):
        self._stopSignalReceived = True

    def setOnBacklinkSearchDomainFoundCallback(self, callback):
        self.onBacklinkSearchDomainFound = callback
    
    def onExternalSearchDomainFound(self, domains):
        self.feed(domains)

    def setErrorCallback(self, callback):
        self.errorCallback = callback

    def run(self):
        try:
            while not self._stopSignalReceived:
                toBeProcessed = self.domains.difference(self._processedDomains)
                if len(toBeProcessed) == 0:
                    print("ExternalsMapper is waiting for input")
                    time.sleep(5)
                    continue
                #newBacklinkSearchDomains = []
                for domain in toBeProcessed:
                    domainExternals = self.getExternalLinks(domain)
                    #self.data.add(DomainData(domain, [], domainExternals))
                    for exlink in domainExternals:
                        self.exporter.writerow({"of_domain": domain, "url_to": exlink})
                    if len(domainExternals) != 0:
                        searchDomains = list(map(lambda x: parse.urlparse(x).netloc, domainExternals))
                        self.onBacklinkSearchDomainFound(searchDomains)
                    self._processedDomains.add(domain)                          # They are now processed
                #self.onBacklinkSearchDomainFound(newBacklinkSearchDomains)
        except Exception as ex:
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

    def feed(self, domains):
        """
        Adds domains to be queried
        """
        print("ExternalsMapper is fed")
        self.domains = self.domains.union(domains)

    def getExternalLinksWithSitemap(self, domain):
        """
        Returns a set of external links
        or None if no sitemap
        """
        url = SITEMAP_REQ_URL.replace("%DOMAIN%", domain)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=WEBREQUEST_TIMEOUT)
        except requests.exceptions.ConnectionError as ex:
            print("DEBUG: Url '%s' caused connection error" % url)
            return None
        except requests.exceptions.ReadTimeout as ex:
            print("Url '%s' caused read time out" % url)
            return None
        if resp.status_code != 200:
            # Not found
            return None
        internalLinks = set()
        try:
            soup = BeautifulSoup(resp.text.encode("utf8"), "lxml")
        except:
            print("ERROR WITH BeautifulSoup -------------- ABORT DOMAIN: ", domain)
            return None
        for loc in soup.find_all("loc"):
            internalLinks.add(loc.text)
        externalLinks = set()
        # Process each internal link for external links
        internalLinks = list(filter(lambda l: "text/html" in self.getContentType(self.convertToAbsoluteLink(url, l)), internalLinks))
        rs = (grequests.get(il, headers=HEADERS, timeout=WEBREQUEST_TIMEOUT) for il in internalLinks)
        try:
            self.exceptionCount = 0
            startTime = time.time()
            for resp in grequests.imap(rs, exception_handler=self.exception_handler):
                elapsed = time.time() - startTime
                if elapsed > EM_MAX_TIME_FOR_DOMAIN:
                    # This domain has exceeded its time span
                    print("Domain '%s' has exceeded its time span of %s with its total time %s"%(domain, EM_MAX_TIME_FOR_DOMAIN, elapsed))
                    print("Skipping domain")
                    return externalLinks
                try:
                    html = BeautifulSoup(resp.text.encode("utf8"), "html.parser")
                except:
                    print("ERROR WITH BeautifulSoup -------------- SKIP")
                    continue
                # Iterate over all inlinks
                for link in html.findAll('a'):
                    target = link.get("href")
                    if target == None:
                        continue
                    if ExternalsMapper.classifyLink(target, domain) == True:
                        externalLinks.add(target)
                        if len(externalLinks) == self.exLinkLimit:
                            return externalLinks
        except TooManyExceptionsError:
                print("Domain %s caused too many errors while searching for its external links. Skipping." % domain)
        return externalLinks
    
    def getContentType(self, url):
        try:
            r = urllib.request.urlopen(url, timeout=WEBREQUEST_TIMEOUT)
        except Exception as ex:
            # Assume it is html
            print("DEBUG: Urllib content type check failed. Assuming it is html. Url: ", url)
            print("Details:")
            print(ex)
            return "text/html"
        try:
            return r.info()["content-type"]
        except KeyError:
            return ""

    def convertToAbsoluteLink(self, domainUrl, link):
        """If the link is relative, converts it to absolute link"""
        # Make sure there are no spaces in the link
        link = link.replace(" ", "")
        parsed = parse.urlparse(link)
        if parsed.netloc == "":
            if domainUrl[-1] == "/" and link[0] == "/":
                return domainUrl + link[1:]
            return domainUrl+link
        else:
            return link
            
    def getExternalLinksWithIndex(self, domain):
        """
        Start from index page and scan internal links and repeat
        On internal pages, scan external links and return them as a set
        """
        url = INDEX_REQ_URL.replace("%DOMAIN%", domain)
        exlinks = set()
        inlinks = set([url])
        traversed = []
        startTime = time.time()
        while True:
            toBeTraversed = inlinks.difference(traversed)   
            if len(toBeTraversed) == 0:
                break
            #print("toBeTraversed: ", toBeTraversed)
            toBeTraversed = list(filter(lambda l: "text/html" in self.getContentType(self.convertToAbsoluteLink(url, l)), toBeTraversed))
            rs = (grequests.get(il, headers=HEADERS, timeout=WEBREQUEST_TIMEOUT) for il in toBeTraversed)
            try:
                self.exceptionCount = 0
                for resp in grequests.imap(rs, exception_handler=self.exception_handler):
                    elapsed = time.time() - startTime
                    if elapsed > EM_MAX_TIME_FOR_DOMAIN:
                        # This domain has exceeded its time span
                        print("Domain '%s' has exceeded its time span of %s with its total time %s"%(domain, EM_MAX_TIME_FOR_DOMAIN, elapsed))
                        print("Skipping domain")
                        return exlinks
                    try:
                        html = BeautifulSoup(resp.text.encode("utf8"), "html.parser")
                    except Exception as ex:
                        print("ERROR WITH BeautifulSoup -------------- Skipping url '%s'"%resp.url)
                        print("Details:")
                        printException(ex)
                        continue
                    # Iterate over all inlinks
                    for link in html.findAll('a'):
                        target = link.get("href")
                        if target == None:
                            continue
                        linkClass = ExternalsMapper.classifyLink(target, domain)
                        if linkClass == False:
                            inlinks.add(target)
                        elif linkClass == True:
                            exlinks.add(target)
                            #print(str(len(exlinks)), str(self.exLinkLimit))
                            if len(exlinks) == self.exLinkLimit:
                                return exlinks
                traversed.extend(toBeTraversed)
            except TooManyExceptionsError:
                print("Domain %s caused too many errors while searching its external links. Skipping." % domain)
                return exlinks
        return exlinks

    def getExternalLinks(self, domain):
        """
        Returns a set of external links of a domain
        """
        print("External links of domain %s is being looked up"%domain)
        results = self.getExternalLinksWithSitemap(domain)
        if results != None:
            return results
        return self.getExternalLinksWithIndex(domain)
    
    def exception_handler(self, req="", ex="No detail is given."):
        self.exceptionCount += 1
        print("Exception in request with grequests. Skipping this request. Details:")
        print(ex)
        if self.exceptionCount == ExternalsMapper.MAX_EXCEPTION_COUNT:
            # Let 'getExternalLinksWithIndex' handle this.
            raise TooManyExceptionsError()
    
    @staticmethod
    def classifyLink(link, domain):
        """
        Returns
        True: Exlink
        False: Inlink
        None: Not a proper link
        """
        obj = parse.urlparse(link)
        linkDomain = obj.netloc
        path = obj.path
        if path == "" and linkDomain == "":
            return None
        elif path != "" and (linkDomain == "" or linkDomain == domain):
            #print("inlink: ", link)
            return False
        else:
            #print("exlink: ", link)
            return True
