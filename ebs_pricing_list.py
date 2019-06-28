import boto3
import json
import pprint

us_east_1_session = boto3.Session(region_name='us-east-1')

session = boto3.Session(region_name='eu-west-2')

pricing_client = us_east_1_session.client('pricing')

ec2 = session.client('ec2')

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

volume_types = {
    "gp2": "General Purpose",
    "io1": "Provisioned IOPS",
    "sc1": "Cold HDD",
    "st1": "Throughput Optimized HDD",
    "standard": "Magnetic"
}

usage_type = {
    "region": {
        "us-east-1": {
            "gp2": {
                "UE"
            }
        }
    }
}

resources = {}
aws_region = list(region_short_names.keys())
for region in aws_region:
    resources[region] = {
        "EBS" : {}
    }

price_list = {}   
while True:
    pl = pricing_client.get_products(ServiceCode="AmazonEC2", 
                                        Filters=[
                                            {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'storage'}, 
                                            {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'Provisioned IOPS'}
                                            ])
    if "PriceList" in price_list:
            price_list["PriceList"] = price_list["PriceList"] + pl["PriceList"]
    else:
        price_list["PriceList"] = pl["PriceList"]
    try:
        NextTokenKey = pl["NextToken"]
    except KeyError:
        break

for item in price_list["PriceList"]:
    price_item = json.loads(item)
    terms = price_item["terms"]
    pprint.pprint(price_item)
    if "OnDemand" in terms:
        product_sku = list(terms["OnDemand"].keys())
        pd = terms["OnDemand"][product_sku[0]]["priceDimensions"]
        
        