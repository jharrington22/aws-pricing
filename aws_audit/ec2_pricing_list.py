import boto3
import json
import pprint 
import re

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
        "EC2" : {}
    }

   
paginator = pricing_client.get_paginator('get_products')
resp_pages = paginator.paginate(ServiceCode="AmazonEC2",
                                        Filters=[
                                            {'Type':'TERM_MATCH', 'Field':'preInstalledSw', 'Value':'NA'},
                                            {'Type':'TERM_MATCH', 'Field':'operatingSystem', 'Value':'Linux'},
                                            {'Type':'TERM_MATCH', 'Field':'tenancy', 'Value':'Shared'},
                                            {'Type':'TERM_MATCH', 'Field':'licenseModel', 'Value':'No License required'},
                                            {'Type':'TERM_MATCH', 'Field':'capacitystatus', 'Value':'Used'}
                                          ])
for page in resp_pages:
    for item in page["PriceList"]:
        price_item = json.loads(item)
        # if "location"in price_item["product"]["attributes"]:
            
        terms = price_item["terms"]
        if "instanceType" in price_item["product"]["attributes"]:
            instance_type = price_item["product"]["attributes"]["instanceType"]
            region = list(region_short_names.keys())[list(region_short_names.values()).index(price_item["product"]["attributes"]["location"])]

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
                            "Tenancy": price_item["product"]["attributes"]["tenancy"],
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

#Write the result to a json file
with open('epl1.json', 'w+') as fp:
   json.dump(resources,fp)         
