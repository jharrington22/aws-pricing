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


volume_types = {
    "gp2": "General Purpose",
    "io1": "Provisioned IOPS",
    "sc1": "Cold HDD",
    "st1": "Throughput Optimized HDD",
    "standard": "Magnetic"
}

for region in aws_region:
    resources[region] = {
        "EBS" : {}
    }

price_list = {}  
tokens = []
token_count = 0

paginator = pricing_client.get_paginator('get_products')
resp_pages = paginator.paginate(ServiceCode="AmazonEC2")
                                        # Filters=[
                                        #     {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'storage'}
                                        #     ])

# with open('ebs_pricing_file.json', 'w') as ebs_file:
#     ebs_file.write(json.dumps(price_list["PriceList"]))

for page in resp_pages:
    for item in page["PriceList"]:
        price_item = json.loads(item)
        terms = price_item["terms"]
        
        
        if "volumeType" in price_item["product"]["attributes"]:
            volume_type = list(volume_types.keys())[list(volume_types.values()).index(price_item["product"]["attributes"]["volumeType"])]
            region = list(region_short_names.keys())[list(region_short_names.values()).index(price_item["product"]["attributes"]["location"])]
            
            if "OnDemand" in terms:
                product_sku = list(terms["OnDemand"].keys())
                pd = terms["OnDemand"][product_sku[0]]["priceDimensions"]
                
                product_price_sku = list(pd.keys())
                price = pd[product_price_sku[0]]['pricePerUnit']["USD"]

                description = pd[product_price_sku[0]]["description"]
            
                if not volume_type in resources[region]["EBS"]:
                    resources[region]["EBS"][volume_type] = {}
                if not "OnDemand" in resources[region]["EBS"][volume_type]:
                    resources[region]["EBS"][volume_type]["OnDemand"] = {}

                resources[region]["EBS"][volume_type]["OnDemand"] = {
                                "Description": description,
                                "UsageType": price_item["product"]["attributes"]["usagetype"],
                                "Location": price_item["product"]["attributes"]["location"],
                                "Max Volume Size": price_item["product"]["attributes"]["maxVolumeSize"],
                                "USD": price
                                } 

#Write the result to a json file
with open("ebs_pricing_list.json", "w+") as fp:
    json.dump(resources,fp)