import boto3
import json
import pprint

us_east_1_session = boto3.Session(region_name='us-east-1')

session = boto3.Session(region_name='eu-west-2')

pricing_client = us_east_1_session.client('pricing')
resources = {}


region_short_names = {
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "eu-central-1": "EU (Frankfurt)",
    "eu-west-1": "EU (Ireland)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-northeast-2": "Asia Pacific (Seoul)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "us-east-2": "US East (Ohio)",
    "eu-north-1": "EU (Stockholm)",
    "eu-west-3": "EU (Paris)",
    "us-west-1": "US West (N. California)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "us-east-1": "US East (N. Virginia)",
    "eu-west-2": "EU (London)",
    "sa-east-1": "South America (Sao Paulo)",
    "us-west-2": "US West (Oregon)",
    "ca-central-1": "Canada (Central)",
    "ap-east-1": "Ap East",
    "us-gov": "AWS GovCloud (US)",
    "asia-pacific": "Asia Pacific (Hong Kong)",
    "us-gov-east": "AWS GovCloud (US-East)",
    "asia-pacific-ol": "Asia Pacific (Osaka-Local)"
}

resources = {}
aws_region = list(region_short_names.keys())
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

with open('snapshots_price.json','w') as fp:
    json.dump(resources,fp)