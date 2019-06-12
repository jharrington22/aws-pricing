#!/usr/bin/python

import boto3
import json
import pprint

us_east_1_session = boto3.Session(profile_name='opstest', region_name='us-east-1')

session = boto3.Session(profile_name='opstest', region_name='eu-west-2')

pricing_client = us_east_1_session.client('pricing')

ec2 = session.client('ec2')

# print("All Services")
# print("============")
# response = pricing_client.describe_services()
# for service in response['Services']:
#     print(service['ServiceCode'] + ": " + ", ".join(service['AttributeNames']))
# print()
# print("============")
# 
# 
# print("Selected EC2 Attributes & Values")
# print("================================")
# response = pricing_client.describe_services(ServiceCode='AmazonEC2')
# attrs = response['Services'][0]['AttributeNames']
# 
# for attr in attrs:
#     response = pricing_client.get_attribute_values(ServiceCode='AmazonEC2', AttributeName=attr)
# 
#     values = []
#     for attr_value in response['AttributeValues']:
#         values.append(attr_value['Value'])
# 
#     print("  " + attr + ": " + ", ".join(values))
# print("================================")
# price_list = pricing_client.get_products(ServiceCode="AmazonEC2", Filters=[{'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'storage'}, {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'General Purpose'}])
volume_types = {
    "gp2": "General Purpose",
    "io1": "Provisioned IOPS",
    "sc1": "Cold HDD",
    "st1": "Throughput Optimized HDD",
    "standard": "Magnetic"
}

region_short_names = {
    "ap-southeast-1": "APS1-EBS:VolumeUsage",
    "eu-central-1": "EUC1-EBS:VolumeUsage",
    "eu-west-1": "EU-EBS:VolumeUsage",
    "ap-northeast-1": "APN1-EBS:VolumeUsage",
    "ap-northeast-2": "APN2-EBS:VolumeUsage",
    "ap-south-1": "APS3-EBS:VolumeUsage",
    "us-east-2": "USE2-EBS:VolumeUsage",
    "eu-north-1": "EUN1-EBS:VolumeUsage",
    "eu-west-3": "EUW3-EBS:VolumeUsage",
    "us-west-1": "USW1-EBS:VolumeUsage",
    "ap-southeast-2": "APS2-EBS:VolumeUsage",
    "us-east-1": "EBS:VolumeUsage",
    "eu-west-2": "EUW2-EBS:VolumeUsage",
    "sa-east-1": "SAE1-EBS:VolumeUsage",
    "us-west-2": "USW2-EBS:VolumeUsage",
    "ca-central-1": "CAN1-EBS:VolumeUsage",
    "ap-east-1": "APE1-EBS:VolumeUsage"
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

def get_usage_type(region, volume_type):
    return "{}.{}".format(region_short_names[region], volume_type)

#region_

price_list = pricing_client.get_products(ServiceCode="AmazonEC2", Filters=[{'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'storage'}, {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': 'Provisioned IOPS'}])
# price_list = pricing_client.get_products(ServiceCode="AmazonEC2", Filters=[{'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'storage'}, {'Type': 'TERM_MATCH', 'Field': 'usageType', 'Value': 'EUC1-EBS:VolumeUsage.gp2'}])
for product in price_list["PriceList"]:
    p = json.loads(product)
    # for k in p:
    #     v = [ vv for vv in p[k] ]
    #     print("{}: {}".format(k, ' '.join(v)))
    pprint.pprint(json.dumps(p["product"], indent=2))
    pprint.pprint(json.dumps(p["terms"], indent=2))
#price_list = pricing_client.get_products(ServiceCode="AmazonEC2", Filters=[{'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'storage'}])
# pprint.pprint(price_list["PriceList"])
volumes = ec2.describe_volumes()

print(get_usage_type("us-east-1", "gp2"))

ebs_vol_pricing = {
    "us-east-1"
}

#pprint.pprint(volumes["Volumes"])

detached_volumes = []
attached_volumes = []

# for vol in volumes["Volumes"]:
#     if len(vol["Attachments"]) == 0:
#         detached_volumes.append(vol)
#     else:
#         attached_volumes.append(vol)

# print("Attached volumes: {}".format(len(attached_volumes)))
# print("Detached volumes: {}".format(len(detached_volumes)))
# 
for v in detached_volumes:
    if not v["VolumeType"] == "gp2":
        print(v)
# print(detached_volumes[1])

