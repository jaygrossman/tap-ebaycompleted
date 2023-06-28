#!/usr/bin/env python3
import os
import json
import singer
from singer import utils, metadata
from singer.catalog import Catalog, CatalogEntry
from singer.schema import Schema
from bs4 import BeautifulSoup
import random
import requests
import time

REQUIRED_CONFIG_KEYS = []
LOGGER = singer.get_logger()


def get_schema():
    schema = {
        "properties": {
        "search_term": {"type": "string"},
        "title": {"type": "string"},
        "price": {"type": "string"},
        "bids": {"type": "string"},
        "buy_it_now": {"type": "boolean"},
        "condition": {"type": "string"},
        "image": {"type": "string"},
        "link": {"type": "string"},
        "ebay_id": {"type": "string"},
        "end_date": {"type": "string"},
        "has_sold": {"type": "boolean"},
        "sku": {"type": "string"}
        }
     }
    return schema

def parse_search_results_page(schema_name, search_term, sku, url):
    response = requests.get(url)
    html_content = str(response.content).replace("<!--F#f_0-->", "").replace("<!--F/-->", "").replace("<span role=heading aria-level=3>", "")
    soup = BeautifulSoup(html_content, "html.parser")

    listings = soup.find_all("li", class_="s-item s-item__pl-on-bottom")
    
    # Iterate over completed listings
    for listing in listings:

        title = listing.find("div", class_="s-item__title").text
        price = listing.find("span", class_="s-item__price").text
        try:
            condition = listing.find("span", class_="SECONDARY_INFO").text
        except:
            condition = ""
        image= listing.find("img")['src']
        link = listing.find("a", class_="s-item__link")['href']
        ebay_id = link[0:link.index("?")].replace("https://www.ebay.com/itm/", "")
        link = "https://www.ebay.com/itm/{}".format(ebay_id)
        bids = ""
        try:
            bids = listing.find("span", class_="s-item__bids s-item__bidCount").text
        except:
            bids = ""
        buy_it_now = False
        try:
            if listing.find("span", class_="s-item__dynamic s-item__buyItNowOption").text == "Buy It Now":
                buy_it_now = True
        except:
            buy_it_now = False   
        
        has_sold = False
        try:
            if listing.find("div", class_="s-item__title--tag").find("span", class_="clipped").text == "Sold Item":
                has_sold = True
                end_date=listing.find("div", class_="s-item__title--tag").find("span", class_="POSITIVE").text.replace("Sold  ", "")
            else:
                end_date = listing.find("div", class_="s-item__title--tag").find("span", class_="NEGATIVE").text.replace("Ended  ", "")
        except:
            end_date=""

        if "Shop on eBay" not in title:
            record = {
                "search_term": search_term,
                "title": title,
                "price": price,
                "bids": bids,
                "buy_it_now": buy_it_now,
                "condition": condition,
                "image": image,
                "link": link,
                "ebay_id": ebay_id,
                "end_date": end_date,
                "has_sold": has_sold,
                "sku": sku
            }

            singer.write_records(schema_name, [record])


def sync(config):
    """ Sync data from tap source """
    
    # Get Schema
    schema = get_schema()
    singer.write_schema("completed_item_schema", schema, "id")

    # Set Defaults from Config
    try:
        page_size = config['page_size']
        if page_size != 240 and page_size != 120 and page_size != 60:
            page_size = 120
    except:
        page_size = 120

    max_pages = 1
    try:
        max_pages = int(config['max_pages'])
        if max_pages > 10:
            max_pages = 10
    except:
        max_pages = 1

    try:
        min_wait = config['min_wait']
        if min_wait <2:
            min_wait = 2
        max_wait = config['max_wait']
        if max_wait <2 or max_wait>20:
            max_wait = 5
    except:
        min_wait = 2
        max_wait = 5


    use_feed = False
    search_terms = config['search_terms']

    try:
        if 'feed' in config:
            sku_field_name = 'sku'
            search_term_field_name = 'search_term'
            if 'sku_field_name' in config['feed']:
                sku_field_name = config['feed']['sku_field_name']
            if 'search_term_field_name' in config['feed']:
                search_term_field_name = config['feed']['search_term_field_name']
            var = requests.get(config['feed']['url'])
            search_terms = json.loads(var.text, strict=False)
            use_feed = True
    except:
        use_feed = False
        search_terms = config['search_terms']

    # Iterate over search terms
    for row in search_terms:
        if use_feed == True:
            search_term = row[search_term_field_name]
            sku = str(row[sku_field_name])
        else:
            search_term = row
            sku = ""
        time.sleep(random.uniform(min_wait, max_wait))
        current_page = 1
        total_pages = 1
        total_records = 0
        
        if "exclude_terms" in config:
            for exclude_term in config['exclude_terms']:
                search_term = search_term + " -" + exclude_term

        url = f"https://www.ebay.com/sch/i.html?LH_Complete=1&_sop=13&_ipg={page_size}&_nkw={search_term}"
        response = requests.get(url)
        html_content = str(response.content).replace("<!--F#f_0-->", "").replace("<!--F/-->", "").replace("<span role=heading aria-level=3>", "")
        soup = BeautifulSoup(html_content, "html.parser")
        
        try:
            total_records = soup.find("h1", class_="srp-controls__count-heading").find("span", class_="BOLD").text
            total_records = total_records.replace(",", "").replace("+", "")
            if total_records>page_size:
                total_pages = int(int(total_records)/page_size)
        except:
            total_pages = 1
        while current_page <= total_pages and current_page <= max_pages:
                parse_search_results_page("completed_item_schema", search_term, sku, "{}&_pgn={}".format(url, current_page))
                current_page=current_page+1
    
@utils.handle_top_exception(LOGGER)
def main():
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)
    if 'search_terms' not in args.config and 'feed' not in args.config:
        raise Exception("You must either define a feed or a search term in the config.")
    elif 'feed' in args.config and 'url' not in args.config['feed']:
        raise Exception("You must define a url in the feed config.")
    sync(args.config)

if __name__ == "__main__":
    main()
