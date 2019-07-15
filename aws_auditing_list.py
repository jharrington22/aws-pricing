#!/usr/bin/python3
#Provides attached/unattached instances for ELB for all regions
import boto3
import json
from datetime import datetime
import os
import pickle
import pprint
from prettytable import PrettyTable
import argparse
import sys

#For CLI
parser = argparse.ArgumentParser()
parser.add_argument("--allpricing", "-a", help="Print the pricing report for all regions")
parser.add_argument("--region", "-r", help="Print the pricing report for that region")
parser.add_argument("--mem", help="Use temp stored table")

args = parser.parse_args()

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


# To fix datetime object not serializable
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)

class AWSAudit():
    def __init__(self):
        self.resources = {}
        self.dictionary = {}
        self.ec2_counts = {}
        self.cELB = {}
        self.nELB = {}
        self.vEBS = {}
        self.sEBS = {}
        self.snap_vol_id = {}

        self.con = self.connection("ec2")
        self.sts_client = self.connection('sts')

        if args.region:
            self.aws_regions = [args.region]
        else:
            self.aws_regions = self.con.describe_regions()
            self.aws_regions = [ d['RegionName'] for d in self.aws_regions['Regions']]
        self.initializeResourceDict(self.aws_regions)
        self.get_ec2_resources(self.aws_regions)
        self.get_classicELB_resources(self.aws_regions)
        self.get_networkELB_resources(self.aws_regions)
        self.get_ebs_resources(self.aws_regions)
        self.get_price(self.ec2_counts, self.cELB, self.nELB, self.vEBS, self.sEBS)
        
    def connect(self, service, region_name=None):
        return boto3.client(service, region_name)

    def connection(self, service):
        return boto3.client(service)

    def initializeResourceDict(self, regions):
        resources_dict = {}
        for region_name in regions:
            resources_dict[region_name] = {
                "ELB": {},
                "ELBV2": {},
                "EC2": {},
                "EBS": {
                    "orphaned_snapshots": []
                }
            }
        self.dictionary = resources_dict

    def get_ec2_resources(self, regions):
        count_region = {}
        for region_name in regions:
            count_region[region_name] = {}
            count = 0
            count_list = {}

            conn = self.connect("ec2", region_name=region_name)
            instance_list = conn.describe_instances()
            instance_ids = []
            
            for r in  instance_list['Reservations']:
                for i in r["Instances"]:
                    id = i['InstanceId']
                    instance_ids.append(i['InstanceId'])
                    if "KeyName" in i:
                        key_name = i["KeyName"]
                    else:
                        key_name = ""
                    self.dictionary[region_name]["EC2"][id] = {
                        "type": i['InstanceType'],
                        "key_name": key_name,
                        "launch_time": i['LaunchTime'],
                        "state": i['State']['Name'],
                        "volumes": []
                    }

                    if len(i['BlockDeviceMappings']) > 0:
                        for vol in i['BlockDeviceMappings']:
                            self.dictionary[region_name]["EC2"][id]["volumes"].append(vol['Ebs']['VolumeId'])
                    
                    instance_type = i['InstanceType']
                    if i['State']['Name'] == 'running':
                        if not instance_type in count_list:
                            count_list[instance_type] = {"count" : 0}

                        if instance_type in count_list:
                            count_list[instance_type]["count"] += 1
            count_region[region_name] = count_list
        self.ec2_counts = count_region        

    def get_classicELB_resources(self, regions):
        elb_cost_region = {}
        with open("elb_pricing.json","r") as elb:
            elb_pricing = json.load(elb)

        for region_name in regions:
            unattached_instances = 0
            attached_instances = 0
            total_instances = 0
            elb_cost_region[region_name] = {}
            conn = self.connect("elb", region_name=region_name)
            lb = conn.describe_load_balancers()
            for l in lb['LoadBalancerDescriptions']:
                self.dictionary[region_name]["ELB"][l['LoadBalancerName']]  = {
                    "instanceId": []
                }
                for id in l['Instances']:
                    self.dictionary[region_name]["ELB"][l['LoadBalancerName']]["instanceId"].append(id["InstanceId"])
                
                if not len(self.dictionary[region_name]["ELB"][l['LoadBalancerName']]["instanceId"]) > 0:
                    unattached_instances = unattached_instances + 1
                if len(self.dictionary[region_name]["ELB"][l['LoadBalancerName']]["instanceId"]) > 0:
                    attached_instances = attached_instances + 1
                
                total_instances = attached_instances + unattached_instances

                for term in elb_pricing[region_name]['ELB']['OnDemand']:
                    elb_price = float(elb_pricing[region_name]['ELB']['OnDemand']['USD'])
                    total_elb_cost = round(float( elb_price * total_instances*730.5), 3)
                
                elb_cost_region[region_name] = {
                    "total_instances": total_instances,
                    "price": elb_price,
                    "total_elb_cost": total_elb_cost
                }

            self.cELB = elb_cost_region

    def get_networkELB_resources(self, regions):
        elbv2_cost_region = {}
        with open("elbv2_pricing.json","r") as elb2:
            elbv2_pricing = json.load(elb2)

        for region_name in regions:
            total_elbv2_cost = 0
            elbv2_cost_region[region_name] = {}

            conn = self.connect("elbv2", region_name=region_name)
            lb = conn.describe_load_balancers()
            network_elb = len(lb['LoadBalancers'])
            self.dictionary[region_name]["ELBV2"]  = {
                                 "Length": network_elb
                                                    }
            
            for elbv2_price in elbv2_pricing[region_name]['ELB']['OnDemand']:
                elbv2_cost = float(elbv2_pricing[region_name]['ELB']['OnDemand']['USD'])
                total_elbv2_cost = round(float( elbv2_cost * network_elb *730.5), 3)
                elbv2_cost_region[region_name] = {
                    "Elbv2_Cost": total_elbv2_cost,
                    "Total_length": network_elb,
                    "Cost": elbv2_cost
                }
        self.nELB = elbv2_cost_region

    def get_ebs_resources(self, regions):
        with open("ebs_pricing_list.json","r") as ebs:
            vol_pricing = json.load(ebs)
        sts_response = self.sts_client.get_caller_identity()
        user_account = sts_response['Account']
        vol_cost_region = {}   
        snap_vol_region = {}
        snapshot_count_region= {}

        for region_name in regions:
            snap_vol = []
            snap_vol_region[region_name] = {}
            vol_cost_region[region_name] = {}
            snapshot_count_region[region_name] = {}
            count_list = {}
            count = 0
            snap_vol = []
            orphaned_snap_vol = []
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
            standard_count = 0
            gp2_count = 0
            io1_count = 0
            sc1_count = 0
            st1_count = 0
            gp2_price = 0
            io1_price = 0
            sc1_price = 0
            st1_price = 0
            standard_price = 0
            gp2_vol_size = 0
            io1_vol_size = 0
            sc1_vol_size = 0
            st1_vol_size = 0
            standard_vol_size = 0

            conn = self.connect("ec2", region_name=region_name)

            volumes = conn.describe_volumes()
            vol_length = len(volumes["Volumes"])
            snapshots = conn.describe_snapshots(Filters=[
                {
                    'Name' : 'owner-id',
                    'Values' : [
                    str(user_account),
                    ]
                }
            ])
            snapshot_length = len(snapshots["Snapshots"])
            for vol in volumes['Volumes']:
                vol_id = vol["VolumeId"]
                self.dictionary[region_name]["EBS"][vol_id] = {
                    "state": vol["State"],
                    "snapshots": [],
                    "size": vol["Size"],
                    "volumeType": vol["VolumeType"]
                }

                for vol_type in vol_pricing[region_name]['EBS']:
                    if self.dictionary[region_name]["EBS"][vol_id]["volumeType"] in vol_type:
                        if vol_type == "gp2":
                            gp2_count = gp2_count + 1
                            gp2_price = float(vol_pricing[region_name]['EBS']["gp2"]['OnDemand']['USD'])
                            gp2_vol_size = gp2_vol_size +  self.dictionary[region_name]["EBS"][vol_id]["size"]
                        if vol_type == "io1":
                            io1_count = io1_count + 1
                            io1_price = float(vol_pricing[region_name]['EBS']["io1"]['OnDemand']['USD'])
                            io1_vol_size = io1_vol_size +  self.dictionary[region_name]["EBS"][vol_id]["size"]
                        if vol_type == "sc1":
                            sc1_count = sc1_count + 1
                            sc1_price = float(vol_pricing[region_name]['EBS']["sc1"]['OnDemand']['USD'])
                            sc1_vol_size = sc1_vol_size +  self.dictionary[region_name]["EBS"][vol_id]["size"]
                        if vol_type == "st1":
                            st1_count = st1_count + 1
                            st1_price = float(vol_pricing[region_name]['EBS']["st1"]['OnDemand']['USD'])
                            st1_vol_size = st1_vol_size +  self.dictionary[region_name]["EBS"][vol_id]["size"]
                        if vol_type == "standard":
                            standard_count = standard_count + 1
                            standard_price = float(vol_pricing[region_name]['EBS']["standard"]['OnDemand']['USD'])
                            standard_vol_size = standard_vol_size +  self.dictionary[region_name]["EBS"][vol_id]["size"]
                        
                tv = ((gp2_vol_size*gp2_price) + (io1_vol_size*io1_price) + (sc1_vol_size*sc1_price) + (st1_vol_size*st1_price) + (standard_vol_size*standard_price))
                tvc = round(tv,3)

            vol_cost_region[region_name] = { 
                "Total Volume Cost": tvc,
                "Total Volumes": vol_length,
                "gp2": gp2_count,
                "io1": io1_count,
                "sc1": sc1_count,
                "st1": st1_count,
                "standard": standard_count,
                "gp2_cost" : gp2_price,
                "io1_cost" : io1_price,
                "sc1_cost" : sc1_price,
                "st1_cost" : st1_price,
                "standard_cost" : standard_price,
                "gp2_size": gp2_vol_size,
                "io1_size": io1_vol_size,
                "sc1_size": sc1_vol_size,
                "st1_size": st1_vol_size,
                "standard_size": standard_vol_size
                }
            self.vEBS = vol_cost_region

        # #   Get all snapshots and assign them to their volume
            for snapshot in snapshots['Snapshots']:
                snap = snapshot['VolumeId']
                if snap in self.dictionary[region_name]["EBS"]:
                    self.dictionary[region_name]["EBS"][snap]["snapshots"].append(snapshot['SnapshotId'])
                    if not snap in snap_vol:
                        snap_vol.append(snap)
                        snapshot_count = snapshot_count + 1
                else:
                    self.dictionary[region_name]["EBS"]["orphaned_snapshots"].append(snapshot['SnapshotId'])
                    orphaned_snapshot_count = orphaned_snapshot_count + 1

            snap_vol_region[region_name] = snap_vol
            self.snap_vol_id = snap_vol_region

            snapshot_count_region[region_name] = {
                "sc": snapshot_count,
                "osc": orphaned_snapshot_count
            }
            self.sEBS = snapshot_count_region

    def get_price(self, EC2_counts, classicELB, networkELB, volume, snapshot):
        with open('epl1.json', 'r') as fp:
            pricing_json = json.load(fp)
        with open("elb_pricing.json","r") as elb:
            elb_pricing = json.load(elb)
        with open('snapshots_price.json', 'r') as fp:
            snapshot_pricing = json.load(fp)
        

        #EC2 pricing
        for region in EC2_counts: 
            x.add_row([region, "", "", "", "", "",""])
            total_coi = 0
            total_cost = 0
            total_size = 0
            price_per_month = 0
            ppm = 0
            sc_length = 0
            osc_length = 0
            price =0
            snap_price = 0
            total_size = 0
            s = 0
            
            x.add_row(["", "EC2 Running Instances", "", "", "", "", ""])
            for i_types in EC2_counts[region]:
                if i_types in (instance_type for instance_type in pricing_json[region]["EC2"]):
                    count_of_instances = round(float(EC2_counts[region][i_types]["count"]), 3)
                    price = round(float(pricing_json[region]["EC2"][i_types]["OnDemand"]["USD"]), 3)

                    total_coi = total_coi + (EC2_counts[region][i_types]["count"])
                    total_cost = round(float((price*count_of_instances*730.5)),3)
                    
                    x.add_row(["", "", i_types, EC2_counts[region][i_types]["count"], price, "", ""])
            x.add_row(["", "", "" , "", "", total_coi, total_cost])

        #Classic ELB pricing
        x.add_row(["", "ELB Classic", "", "", "", "", ""])
        if region in classicELB:
            if 'total_elb_cost' in classicELB[region] and 'price' in classicELB[region] and 'total_instances' in classicELB[region]:
                cost = classicELB[region]['total_elb_cost']
                elb_price = classicELB[region]['price']
                elb_total_instances = classicELB[region]['total_instances']
                x.add_row(["", "", "", "", elb_price, elb_total_instances, cost])
        
        #Network ELB pricing
        x.add_row(["", "ELB Network", "", "", "", "", ""])
        if region in networkELB:
            # if 'total_elb_cost' in elb_cost_region[region] and 'price' in elb_cost_region[region] and 'total_instances' in elb_cost_region[region]:
            #     cost = elb_cost_region[region]['total_elb_cost']
            elbv2_price = networkELB[region]['Elbv2_Cost']
            elbv2_total_instances = networkELB[region]['Total_length']
            elbv2_cost = networkELB[region]['Cost']
            x.add_row(["", "", "", "", elbv2_cost, elbv2_total_instances, elbv2_price])

        #Volume pricing
        x.add_row(["", "Volume", "", "", "", "", ""])
        if region in volume:
            volume_price = volume[region]['Total Volume Cost']
            length = volume[region]["Total Volumes"]
            x.add_row(["", "", "gp2", volume[region]["gp2"], volume[region]["gp2_cost"], volume[region]["gp2_size"], ""])
            x.add_row(["", "", "io1", volume[region]["io1"], volume[region]["io1_cost"], volume[region]["io1_size"], ""])
            x.add_row(["", "", "sc1", volume[region]["sc1"], volume[region]["sc1_cost"], volume[region]["sc1_size"], ""])
            x.add_row(["", "", "st1", volume[region]["st1"], volume[region]["st1_cost"], volume[region]["st1_size"], ""])
            x.add_row(["", "", "standard", volume[region]["standard"], volume[region]["standard_cost"], volume[region]["standard_size"], ""])
        x.add_row(["", "", "", "", "Total Volumes", length, volume_price])

          #Snapshots pricing
        x.add_row(["", "Snapshots", "", "", "", "", ""])
        x.add_row(["", "", "", "", "", "", ""])
        if region in snapshot:
            sc_length = snapshot[region]["sc"]
            osc_length = snapshot[region]["osc"]
        if region in (reg for reg in snapshot_pricing):
                snap_price =  float(snapshot_pricing[region]['Snapshot']['OnDemand']['USD'])
        for volume_id in self.snap_vol_id[region]:
            if volume_id in (vol_id for vol_id in self.dictionary[region]['EBS']):
                size = self.dictionary[region]['EBS'][volume_id]['size']
                total_size = total_size + size 
            ppm = round(float(snap_price * float(total_size)),3)
        x.add_row(["", "", "snapshots", sc_length, snap_price, total_size, ppm])
        x.add_row(["", "", "orphaned snapshots", osc_length, snap_price, "", round(float(snap_price*osc_length),3)])

        print(x)

aws_audit = AWSAudit()


