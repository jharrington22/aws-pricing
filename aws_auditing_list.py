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
x.field_names = ["Region", "Service", "Instance_Type", "Count", "Price per hour", "Total Instances", "Total cost per month"]
x.align["Region"] = "l"
x.align["Service"] = "l"
x.align["Instance_Type"] = "l"
x.align["Count"] = "l"
x.align["Price per hour"] = "l"
x.align["Total Instances"] = "l"
x.align["Total EC2 cost per month"] = "l"

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
snapshot_count_region = {}
snap_vol_region = {}
vol_cost_region = {}
elb_cost_region = {}
elbv2_cost_region = {}

with open("ebs_pricing_list.json","r") as ebs:
    vol_pricing = json.load(ebs)

with open("elb_pricing.json","r") as elb:
    elb_pricing = json.load(elb)

with open('epl1.json', 'r') as fp:
    pricing_json = json.load(fp)

with open('snapshots_price.json', 'r') as fp:
    snapshot_pricing = json.load(fp)

with open("elbv2_pricing.json","r") as elb2:
    elbv2_pricing = json.load(elb2)


for region in enabledRegions['Regions']:
    count_list = {}
    count = 0
    snap_vol = []
    tv = 0
    tvc = 0
    snapshot_count = 0
    orphaned_snapshot_count = 0
    snapshot_count_list = {}
    total_volume_cost = 0
    attached_instances = 0
    unattached_instances = 0
    total_instances = 0
    total_elb_cost = 0
    total_elbv2_cost = 0

    if os.path.exists(resource_path):
        exit

    region_name = region['RegionName']
    print("Collecting recource for region: {}".format(region_name))
    recource_dict[region_name] = {
        "ELB": {},
        "ELBV2": {},
        "EC2": {},
        "EBS": {
            "orphaned_snapshots": []
        }
    }
    count_region[region_name] = {}
    snapshot_count_region[region_name] = {}
    snap_vol_region[region_name] = {}
    vol_cost_region[region_name] = {}
    elb_cost_region[region_name] = {}
    elbv2_cost_region[region_name] = {}

    # Create connections to AWS
    client = boto3.client('elb',region_name=region_name)
    ec2 = boto3.client('ec2', region_name=region_name)

    elb_network_client = boto3.client('elbv2',region_name=region_name)

    # ELBs and their attached instances
    print("Collecting Classic ELB recource")
    lb = client.describe_load_balancers()
    for l in lb['LoadBalancerDescriptions']:
        recource_dict[region_name]["ELB"][l['LoadBalancerName']]  = {
            "instanceId": []
        }
        for id in l['Instances']:
            recource_dict[region_name]["ELB"][l['LoadBalancerName']]["instanceId"].append(id["InstanceId"])
    
        if not len(recource_dict[region_name]["ELB"][l['LoadBalancerName']]["instanceId"]) > 0:
            unattached_instances = unattached_instances + 1
        if len(recource_dict[region_name]["ELB"][l['LoadBalancerName']]["instanceId"]) > 0:
            attached_instances = attached_instances + 1
            
        total_instances = attached_instances + unattached_instances

        for term in elb_pricing[region_name]['ELB']['OnDemand']:
            elb_price = float(elb_pricing[region_name]['ELB']['OnDemand']['USD'])
            total_elb_cost = round(float( elb_price * total_instances*730), 3)
        
        elb_cost_region[region_name] = {
            "total_instances": total_instances,
            "price": elb_price,
            "total_elb_cost": total_elb_cost
        }
    
    # Network ELBs and their attached instances
    print("Collecting Network ELB recource")
    lb = elb_network_client.describe_load_balancers()
    network_elb = len(lb['LoadBalancers'])
    recource_dict[region_name]["ELBV2"]  = {
            "Length": network_elb
        }
    for elbv2_price in elbv2_pricing[region_name]['ELB']['OnDemand']:
        elbv2_cost = float(elbv2_pricing[region_name]['ELB']['OnDemand']['USD'])
        total_elbv2_cost = round(float( elbv2_cost * network_elb *730), 3)
        elbv2_cost_region[region_name] = {
            "Elbv2_Cost": total_elbv2_cost,
            "Total_length": network_elb,
            "Cost": elbv2_cost
        }
    
    # Get all volumes for region_name and store in dict
    # print("Collecting EBS recource")
    volumes = ec2.describe_volumes()
    vol_length = len(volumes["Volumes"])
    snapshots = ec2.describe_snapshots(Filters=[
        {
            'Name' : 'owner-id',
            'Values' : [
             '639866565627',
            ]
        }
    ])
    snapshot_length = len(snapshots["Snapshots"])
    for vol in volumes['Volumes']:
        vol_id = vol["VolumeId"]
        recource_dict[region_name]["EBS"][vol_id] = {
            "state": vol["State"],
            "snapshots": [],
            "size": vol["Size"],
            "volumeType": vol["VolumeType"]
        }

        for vol_type in vol_pricing[region_name]['EBS']:
            if recource_dict[region_name]["EBS"][vol_id]["volumeType"] in vol_type:
                volume_cost = float(vol_pricing[region_name]['EBS'][vol_type]['OnDemand']['USD'])
                total_volume_cost = total_volume_cost + volume_cost
        tv = total_volume_cost * 744
        tvc = round(tv,3)
    vol_cost_region[region_name] = { 
        "Total Volume Cost": tvc,
        "Total Volumes": vol_length   
    }


    # Get all instances for region_name and store in dict
    print("Collecting EC2 recource")
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
            if i['State']['Name'] == 'running':
                if not instance_type in count_list:
                    count_list[instance_type] = {"count" : 0}

                if instance_type in count_list:
                    count_list[instance_type]["count"] += 1


            if len(i['BlockDeviceMappings']) > 0:
                for vol in i['BlockDeviceMappings']:
                    recource_dict[region_name]["EC2"][id]["volumes"].append(vol['Ebs']['VolumeId'])

    count_region[region_name] = count_list

#   Get all snapshots and assign them to their volume
    # print("Collecting EBS snapshots")
    for snapshot in snapshots['Snapshots']:
        snap = snapshot['VolumeId']
        if snap in recource_dict[region_name]["EBS"]:
            recource_dict[region_name]["EBS"][snap]["snapshots"].append(snapshot['SnapshotId'])
            snapshot_count = snapshot_count + 1
            snapshot_count_list["sc"] = {"snapshot_count" : snapshot_count}
            if not snap in snap_vol:
                snap_vol.append(snap)
            
        else:
            recource_dict[region_name]["EBS"]["orphaned_snapshots"].append(snapshot['SnapshotId'])
            orphaned_snapshot_count = orphaned_snapshot_count + 1
            snapshot_count_list["osc"] = {"orphaned_snapshot_count" : orphaned_snapshot_count}
    snap_vol_region[region_name] = snap_vol
    snapshot_count_region[region_name] = snapshot_count_list


prices = {}

for region in count_region:
    x.add_row(["", "", "", "", "", "",""])
    x.add_row(["", "", "", "", "", "",""])
    x.add_row(["", "", "", "", "", "",""])
    x.add_row([region, "", "", "", "", "",""])
    total_coi = 0
    total_cost = 0
    total_price = 0
    price_per_month = 0
    ppm = 0
    length = 0
    price =0
    snap_price = 0
    total_size = 0
    s = 0

    #Calculating Pricing for EC2 Instances
    x.add_row(["", "EC2 Running Instances", "", "", "", "", ""])
    for i_types in count_region[region]:
        if i_types in (instance_type for instance_type in pricing_json[region]["EC2"]):

            count_of_instances_float = float(count_region[region][i_types]["count"])
            count_of_instances = round(count_of_instances_float, 3)

            price_float = float(pricing_json[region]["EC2"][i_types]["OnDemand"]["USD"])
            price = round(price_float, 3)
            
            total_coi = total_coi + (count_region[region][i_types]["count"])
            total_cost_float = float(total_cost+(price*count_of_instances*744))
            total_cost = round(total_cost_float,3)
            x.add_row(["", "", i_types, count_region[region][i_types]["count"], price, "", ""])
    x.add_row(["", "", "" , "", "", total_coi, total_cost])

    #Calculating pricing for Snapshots
    x.add_row(["", "Snapshots", "", "", "", "", ""])
    x.add_row(["", "", "", "", "", "", ""])
    for volume_id in snap_vol_region[region]:
        length = len(snap_vol_region[region])
        # if volume_id in (vol_id for vol_id in recource_dict[region]['EBS']):
        #     s = recource_dict[region]['EBS'][volume_id]['size']
        #     size = float(recource_dict[region]['EBS'][volume_id]['size'])
        #     total_size = s + total_size
        if region in (reg for reg in snapshot_pricing):
            snap_price =  float(snapshot_pricing[region]['Snapshot']['OnDemand']['USD'])
            total_price = total_price + (snap_price*length)   
    price_per_month = total_price * 744
    ppm = round(price_per_month, 3)
    x.add_row(["", "", "", "", snap_price, length, ppm])

    x.add_row(["", "Volume", "", "", "", "", ""])
    if region in vol_cost_region:
        volume_price = vol_cost_region[region]['Total Volume Cost']
        length = vol_cost_region[region]["Total Volumes"]
    x.add_row(["", "", "", "", "", length, volume_price])

    x.add_row(["", "ELB Classic", "", "", "", "", ""])
    if region in elb_cost_region:
        if 'total_elb_cost' in elb_cost_region[region] and 'price' in elb_cost_region[region] and 'total_instances' in elb_cost_region[region]:
            cost = elb_cost_region[region]['total_elb_cost']
            elb_price = elb_cost_region[region]['price']
            elb_total_instances = elb_cost_region[region]['total_instances']
            x.add_row(["", "", "", "", elb_price, elb_total_instances, cost])
    
    x.add_row(["", "ELB Network", "", "", "", "", ""])
    if region in elb_cost_region:
        # if 'total_elb_cost' in elb_cost_region[region] and 'price' in elb_cost_region[region] and 'total_instances' in elb_cost_region[region]:
        #     cost = elb_cost_region[region]['total_elb_cost']
        elbv2_price = elbv2_cost_region[region]['Elbv2_Cost']
        elbv2_total_instances = elbv2_cost_region[region]['Total_length']
        elbv2_cost = elbv2_cost_region[region]['Cost']
        x.add_row(["", "", "", "", elbv2_cost, elbv2_total_instances, elbv2_price])

print(x)