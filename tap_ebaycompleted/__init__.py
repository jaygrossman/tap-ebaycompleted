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

REQUIRED_CONFIG_KEYS = ["search_terms"]
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
        "end_date": {"type": "string"},
        "has_sold": {"boolean": "string"},
        "id": {"type": "string"}
        }
     }
    return schema

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

    # Iterate over search terms
    for search_term in config['search_terms']:
        time.sleep(random.uniform(min_wait, max_wait))
        #print("-- searching for items for search term: {}".format(search_term))
        url = f"https://www.ebay.com/sch/i.html?LH_Complete=1&_sop=13&_ipg={page_size}&_nkw={search_term}"
        response = requests.get(url)
        html_content = str(response.content).replace("<!--F#f_0-->", "").replace("<!--F/-->", "").replace("<span role=heading aria-level=3>", "")
        soup = BeautifulSoup(html_content, "html.parser")

        listings = soup.find_all("li", class_="s-item s-item__pl-on-bottom")
     
        # Iterate over completed listings
        for listing in listings:
            title = listing.find("div", class_="s-item__title").text
            price = listing.find("span", class_="s-item__price").text
            condition = listing.find("span", class_="SECONDARY_INFO").text
            image= listing.find("img")['src']
            link = listing.find("a", class_="s-item__link")['href']
            id = link[0:link.index("?")].replace("https://www.ebay.com/itm/", "")
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
                    "condition": condition,
                    "image": image,
                    "link": link,
                    "id": id,
                    "bids": bids,
                    "buy_it_now": buy_it_now,
                    "end_date": end_date,
                    "has_sold": has_sold
                }

                # The singer.write_records function takes a list as the second param, this was not obvious
                singer.write_records("completed_item_schema", [record])
                
@utils.handle_top_exception(LOGGER)
def main():
    args = utils.parse_args(REQUIRED_CONFIG_KEYS)
    sync(args.config)


if __name__ == "__main__":
    main()
