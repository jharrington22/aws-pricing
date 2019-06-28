#!/usr/bin/python3
#Provides attached/unattached instances for ELB for all regions
import boto3
import json
from datetime import datetime
import os
import pickle
import pprint
from prettytable import PrettyTable

#Creating Table
x = PrettyTable()
x.field_names = ["Region", "Instance_Type", "Count", "Price per hour", "Cost per month", "Total Instances", "Total cost per month for the region"]
x.align["Region"] = "l"
x.align["Instance_Type"] = "l"
x.align["Count"] = "l"
x.align["Price per hour"] = "l"
x.align["Cost per month"] = "l"
x.align["Total Instances"] = "l"
x.align["Total cost per month for the region"] = "l"

resource_path = 'resource_dict_snp.p'
# To fix datetime object not serializable
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)

#To call all the regions available
botoClient = boto3.client('ec2')
enabledRegions = botoClient.describe_regions()

recource_dict = {}
count_region = {}

for region in enabledRegions['Regions']:
    count_list = {}
    count = 0

    if os.path.exists(resource_path):
        exit

    region_name = region['RegionName']
    # print("Collecting recource for region: {}".format(region_name))
    recource_dict[region_name] = {
        "ELB": {},
        "EC2": {},
        "EBS": {
            "orphaned_snapshots": []
        }
    }
    count_region[region_name] = {}
    # Create connections to AWS
    client = boto3.client('elb',region_name=region_name)
    ec2 = boto3.client('ec2', region_name=region_name)

    #ELBs and their attached instances
    print("Collecting ELB recource")
    lb = client.describe_load_balancers()
    for l in lb['LoadBalancerDescriptions']:
        recource_dict[region_name]["ELB"][l['LoadBalancerName']]  = {
            "instanceId": []
        }
        for id in l['Instances']:
            recource_dict[region_name]["ELB"][l['LoadBalancerName']]["instanceId"].append(id["InstanceId"])


    # Get all volumes for region_name and store in dict
    print("Collecting EBS recource")
    volumes = ec2.describe_volumes()
    snapshots = ec2.describe_snapshots()
    for vol in volumes['Volumes']:
        vol_id = vol["VolumeId"]
        recource_dict[region_name]["EBS"][vol_id] = {
            "state": vol["State"],
            "snapshots": [],
            "size": vol["Size"]
        }

    # Get all instances for region_name and store in dict
    # print("Collecting EC2 recource")
    instance_ids = []
    instance_list = ec2.describe_instances()
    for r in  instance_list['Reservations']:
        for i in r["Instances"]:
            #instance_information = d['Instances']
            id = i['InstanceId']
            instance_ids.append(i['InstanceId'])
            if "KeyName" in i:
                key_name = i["KeyName"]
            else:
                key_name = ""
            recource_dict[region_name]["EC2"][id] = {
                "type": i['InstanceType'],
                "key_name": key_name,
                "launch_time": i['LaunchTime'],
                "state": i['State']['Name'],
                "volumes": []
            }

            instance_type = i['InstanceType']
            if not instance_type in count_list:
                count_list[instance_type] = {"count" : 0}

            if instance_type in count_list:
                count_list[instance_type]["count"] += 1


            if len(i['BlockDeviceMappings']) > 0:
                for vol in i['BlockDeviceMappings']:
                    recource_dict[region_name]["EC2"][id]["volumes"].append(vol['Ebs']['VolumeId'])

    count_region[region_name] = count_list
    # pprint.pprint(count_region)
    # pprint.pprint(recource_dict["ca-central-1"]["EC2"])

#   Get all snapshots and assign them to their volume
    print("Collecting EBS snapshots")
    for snapshot in snapshots['Snapshots']:
        snap = snapshot['VolumeId']
        if snap in recource_dict[region_name]["EBS"]:
            recource_dict[region_name]["EBS"][snap]["snapshots"].append(snapshot['SnapshotId'])
        else:
            recource_dict[region_name]["EBS"]["orphaned_snapshots"].append(snapshot['SnapshotId'])


# Calculating the price of EC2 instances in each region for a month

with open('ec2pricing.json', 'r') as fp:
    pricing_json = json.load(fp)
for region in count_region:
    x.add_row(["", "", "", "", "", "", ""])
    x.add_row(["", "", "", "", "", "", ""])
    x.add_row([region, "", "", "", "", "", ""])
    total_coi = 0
    total_cost = 0
    for i_types in count_region[region]:
        if i_types in (instance_type for instance_type in pricing_json[region]["EC2"]):
            count_of_instances_float = float(count_region[region][i_types]["count"])
            count_of_instances = round(count_of_instances_float, 3)
            price_float = float(pricing_json[region]["EC2"][i_types]["OnDemand"]["USD"])
            price = round(price_float, 3)
            total_coi = total_coi + (count_region[region][i_types]["count"])
            total_cost_float = float(total_cost+(price*count_of_instances*744))
            total_cost = round(total_cost_float,3)
            cpm_float = price*count_of_instances
            cpm = round(cpm_float,3)
            # print(str(price) + "*" + str(count_of_instances) + " = " +  str(price*count_of_instances))
            # print("Region:  " + region + "  Type:  " + i_types + "  Count:  " + str(count_region[region][i_types]["count"]) + "  Price:  " + str(pricing_json[region]["EC2"][i_types]["OnDemand"]["USD"]) + "  Cost:  " + str(price*count_of_instances))
            x.add_row(["", i_types, count_region[region][i_types]["count"], price, cpm, "", ""])
    # if total_coi == 0 and total_cost == 0:
    #     continue
    x.add_row(["", "", "", "", "", total_coi, total_cost])
print(x)
# print(recource_dict)
