# SEOWebScraper
This is an application I made to scrape some SEO website that returns backlinks of a given website. I removed all references (hence commits are gone) to it. I am only releasing this for showcase.

To develop this, I used developer tools network page and inspector to figure out how to use the api endpoints of the SEO website.

## Features
- Scraping backlinks of a given initial website through a limited free SEO website.
- Scraping external links from a website. Either using site map or through manual crawl.
- Recursive scraping: First search backlinks, then get external links on the result, then get backlinks of found externals.
- Backlinks and external links are saved as CSV.
- In case of failure, backlink and external link dumping and reloading.
- Parallel loading of pages.
- To use the web service after exhausting its daily use, switching to a proxy to go on.
- For the same reason above, using external authorization keys.
