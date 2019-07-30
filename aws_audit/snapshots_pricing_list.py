import boto3
import json
import pprint

from constants import (
    region_short_names,
    resources,
    aws_region
)

from connection import (
    region,
    session,
    ec2,
    pricing_client
) 

for region in aws_region:
    resources[region] = {
        "Snapshot" : {}
    }

paginator = pricing_client.get_paginator('get_products')
resp_pages = paginator.paginate(ServiceCode="AmazonEC2",
                                        Filters=[
                                            {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage Snapshot'}
                                            ])

for page in resp_pages:
    for item in page["PriceList"]:
        price_item = json.loads(item)
        
        terms = price_item["terms"]
        region = list(region_short_names.keys())[list(region_short_names.values()).index(price_item["product"]["attributes"]["location"])]
               
        if "OnDemand" in terms:
            product_sku = list(terms["OnDemand"].keys())
            pd = terms["OnDemand"][product_sku[0]]["priceDimensions"]
            
            product_price_sku = list(pd.keys())
            price = pd[product_price_sku[0]]['pricePerUnit']["USD"]

            description = pd[product_price_sku[0]]["description"]
        
            if not "OnDemand" in resources[region]["Snapshot"]:
                resources[region]["Snapshot"]["OnDemand"] = {}

            resources[region]["Snapshot"]["OnDemand"] = {
                            "Description": description,
                            "UsageType": price_item["product"]["attributes"]["usagetype"],
                            "Location": price_item["product"]["attributes"]["location"],
                            "USD": price
                            } 

#Write the result to a json file
with open('snapshots_price.json','w') as fp:
    json.dump(resources,fp)