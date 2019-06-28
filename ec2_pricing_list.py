import boto3
import json
import pprint 
import re
import sys
import pdb


# with open('plist.txt') as fp:
#     price_list =json.load(fp)
not_instance_type = []


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
region = boto3.Session(region_name='us-east-1')
session = boto3.Session(region_name='eu-west-2')
ec2 = session.client('ec2')
pricing = region.client('pricing')

aws_region = list(region_short_names.keys())
for region in aws_region:
    resources[region] = {
        "EC2" : {}
    }


price_list = {}
NextTokenKey = ""
while True:
    pl = pricing.get_products(
    ServiceCode='AmazonEC2',
    Filters=[
        {'Type':'TERM_MATCH', 'Field':'operatingSystem', 'Value':'Linux'}
        # {'Type':'TERM_MATCH', 'Field':'location', 'Value':region_short_names[aws_region_value]}
    ],
    NextToken=NextTokenKey
        )
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
    region = list(region_short_names.keys())[list(region_short_names.values()).index(price_item["product"]["attributes"]["location"])] 
    terms = price_item["terms"]
    # if "instanceType" not in price_item["product"]["attributes"]:
    #     not_instance_type.append(price_item)
    #     next
    # else:
    #     instance_type = price_item["product"]["attributes"]["instanceType"]
    if 'CPU Credits' not in price_item["product"]["productFamily"]:
        instance_type = price_item["product"]["attributes"]["instanceType"]
        if "OnDemand" in terms:
            product_sku = terms["OnDemand"].keys()
            product_sku = list(terms["OnDemand"].keys())
            pd = terms["OnDemand"][product_sku[0]]["priceDimensions"]
    

            product_price_sku = pd.keys()
            product_price_sku = list(pd.keys())
            price = pd[product_price_sku[0]]['pricePerUnit']["USD"]
    

            description = pd[product_price_sku[0]]["description"]
    
            if not instance_type in resources[region]["EC2"]:
                resources[region]["EC2"][instance_type] = {}
            if not "OnDemand" in resources[region]["EC2"][instance_type]:
                resources[region]["EC2"][instance_type]["OnDemand"] = {}

            usageType = price_item["product"]["attributes"]["usagetype"]
            if re.search(".*BoxUsage:{}".format(instance_type),usageType):
                resources[region]["EC2"][instance_type]["OnDemand"] = {
                        "Description": description,
                        "UsageType": price_item["product"]["attributes"]["usagetype"],
                        "Location": price_item["product"]["attributes"]["location"],
                        "Operating System": price_item["product"]["attributes"]["operatingSystem"],
                        "USD": price
                        } 
        if "Reserved" in terms:
            product_sku = terms["Reserved"].keys()
            product_sku = list(terms["Reserved"].keys())
            pd = terms["Reserved"][product_sku[0]]["priceDimensions"]

            product_price_sku = pd.keys()
            product_price_sku = list(pd.keys())
            Unit =  pd[product_price_sku[0]]['unit']
            price = pd[product_price_sku[0]]['pricePerUnit']["USD"]

            for reserved_sku in terms["Reserved"].keys():
                term_attributes = terms["Reserved"][reserved_sku]["termAttributes"]
                price_dimensions = terms["Reserved"][reserved_sku]["priceDimensions"]
                ri_purchase_option = term_attributes["PurchaseOption"] 


                if not instance_type in resources[region]["EC2"]:
                    resources[region]["EC2"][instance_type] = {}

                if not "Reserved" in resources[region]["EC2"][instance_type]:
                    resources[region]["EC2"][instance_type]["Reserved"] = {}

                if not ri_purchase_option in resources[region]["EC2"][instance_type]["Reserved"]:
                    resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option] = {}

                if term_attributes["OfferingClass"] == "standard" and term_attributes["LeaseContractLength"] == "1yr":
                    if ri_purchase_option == "Partial Upfront":
                        resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option] = {
                            "QuantityRateCode": "",
                            "HrsRateCode": "",
                            "Offering_Class": term_attributes["OfferingClass"],
                            "PurchaseOption": ri_purchase_option,
                            "HrsUSD": "",
                            "UpfrontFeeUSD": ""
                        }
                        for price_dimension in price_dimensions:
                            if price_dimensions[price_dimension]["unit"] == "Quantity":
                                resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["UpfrontFeeUSD"] = price_dimensions[price_dimension]['pricePerUnit']["USD"]
                                resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["QuantityRateCode"] = price_dimensions[price_dimension]['rateCode']
                            if price_dimensions[price_dimension]["unit"]  == "Hrs":
                                resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["HrsUSD"] = price_dimensions[price_dimension]['pricePerUnit']["USD"]
                                resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["HrsRateCode"] = price_dimensions[price_dimension]['rateCode']
                    
                    if ri_purchase_option == "All Upfront":
                        resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option] = {
                            "QuantityRateCode": "",
                            "HrsRateCode": "",
                            "Offering_Class": term_attributes["OfferingClass"],
                            "PurchaseOption": ri_purchase_option,
                            "HrsUSD": "",
                            "UpfrontFeeUSD": ""
                        }
                        for price_dimension in price_dimensions:
                            if price_dimensions[price_dimension]["unit"] == "Quantity":
                                resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["UpfrontFeeUSD"] = price_dimensions[price_dimension]['pricePerUnit']["USD"]
                                resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["QuantityRateCode"] = price_dimensions[price_dimension]['rateCode']
                            if price_dimensions[price_dimension]["unit"]  == "Hrs":
                                resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["HrsUSD"] = price_dimensions[price_dimension]['pricePerUnit']["USD"]
                                resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["HrsRateCode"] = price_dimensions[price_dimension]['rateCode']
                    
                    if ri_purchase_option == "No Upfront":
                        resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option] = {
                            "RateCode": "",
                            "Offering_Class": term_attributes["OfferingClass"],
                            "PurchaseOption": ri_purchase_option,
                            "USD": ""
                        }
                        for price_dimension in price_dimensions:
                            resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["RateCode"] = price_dimensions[price_dimension]['rateCode']
                            resources[region]["EC2"][instance_type]["Reserved"][ri_purchase_option]["USD"] = price_dimensions[price_dimension]['pricePerUnit']["USD"]
                    
pprint.pprint(resources["ca-central-1"]["EC2"])