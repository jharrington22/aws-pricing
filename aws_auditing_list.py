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
parser.add_argument('--allpricing', '-a', help='Print the pricing report for all regions')
parser.add_argument('--region', '-r', help='Print the pricing report for that region')
parser.add_argument('--mem', help='Use temp stored table')

args = parser.parse_args()

#Creating Table
x = PrettyTable()
x.field_names = ['Region', 'Service', 'Instance_Type', 'Count', 'Price per hour', 'Total Instances/Size', 'Total cost per month']
x.align = 'l'


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
        self.classic__elb = {}
        self.network__elb = {}
        self.volume_ebs = {}
        self.snapshot_ebs = {}
        self.snap_vol_id = {}

        self.con = self.connection('ec2')
        self.sts_client = self.connection('sts')

        if args.region:
            self.aws_regions = [args.region]
        else:
            self.aws_regions = self.con.describe_regions()
            self.aws_regions = [ d['RegionName'] for d in self.aws_regions['Regions']]

        self.initializeResourceDict(self.aws_regions)
        self.get_ec2_resources(self.aws_regions)
        self.get_classic_elb_resources(self.aws_regions)
        self.get_network_elb_resources(self.aws_regions)
        self.get_ebs_resources(self.aws_regions)
        self.get_price(self.ec2_counts, self.classic_elb, self.network_elb, self.volume_ebs, self.snapshot_ebs)
        
    def connect(self, service, region_name=None):
        return boto3.client(service, region_name)

    def connection(self, service):
        return boto3.client(service)

    def initializeResourceDict(self, regions):
        resources_dict = {}
        for region_name in regions:
            resources_dict[region_name] = {
                'ELB': {},
                'ELBV2': {},
                'EC2': {},
                'EBS': {
                    'orphaned_snapshots': []
                }
            }
        self.dictionary = resources_dict

    def get_ec2_resources(self, regions):
        count_region = {}
        for region_name in regions:
            count_region[region_name] = {}
            count_list = {}

            conn = self.connect('ec2', region_name=region_name)
            instance_list = conn.describe_instances()
            instance_ids = []
            
            for r in instance_list['Reservations']:
                for i in r['Instances']:
                    id = i['InstanceId']
                    instance_ids.append(i['InstanceId'])
                    if 'KeyName' in i:
                        key_name = i['KeyName']
                    else:
                        key_name = ''
                    self.dictionary[region_name]['EC2'][id] = {
                        'type': i['InstanceType'],
                        'key_name': key_name,
                        'launch_time': i['LaunchTime'],
                        'state': i['State']['Name'],
                        'volumes': []
                    }

                    if len(i['BlockDeviceMappings']) > 0:
                        for vol in i['BlockDeviceMappings']:
                            self.dictionary[region_name]['EC2'][id]['volumes'].append(vol['Ebs']['VolumeId'])
                    
                    instance_type = i['InstanceType']
                    if i['State']['Name'] == 'running':
                        if not instance_type in count_list:
                            count_list[instance_type] = {'count' : 0}

                        if instance_type in count_list:
                            count_list[instance_type]['count'] += 1
            count_region[region_name] = count_list
        self.ec2_counts = count_region        

    def get_classic_elb_resources(self, regions):
        elb_cost_region = {}
        with open('elb_pricing.json','r') as elb:
            elb_pricing = json.load(elb)

        for region_name in regions:
            unattached_instances = 0
            attached_instances = 0
            total_instances = 0
            elb_cost_region[region_name] = {}
            conn = self.connect('elb', region_name=region_name)
            lb = conn.describe_load_balancers()
            for l in lb['LoadBalancerDescriptions']:
                self.dictionary[region_name]['ELB'][l['LoadBalancerName']]  = {
                    'instanceId': []
                }
                if l['Instances']:
                    self.dictionary[region_name]['ELB'][l['LoadBalancerName']]['InstanceId'] = [ id for id in l['Instances']]
                else:
                    self.dictionary[region_name]['ELB'][l['LoadBalancerName']]['InstanceId'] = []

                if not len(self.dictionary[region_name]['ELB'][l['LoadBalancerName']]['instanceId']) > 0:
                    unattached_instances = unattached_instances + 1
                if len(self.dictionary[region_name]['ELB'][l['LoadBalancerName']]['instanceId']) > 0:
                    attached_instances = attached_instances + 1
                

                total_instances = attached_instances + unattached_instances

                for term in elb_pricing[region_name]['ELB']['OnDemand']:
                    elb_price = float(elb_pricing[region_name]['ELB']['OnDemand']['USD'])
                    total_elb_cost = round(float( elb_price * total_instances*730.5), 3)
                
                elb_cost_region[region_name] = {
                    'total_instances': total_instances,
                    'price': elb_price,
                    'total_elb_cost': total_elb_cost
                }

            self.classic_elb = elb_cost_region

    def get_network_elb_resources(self, regions):
        elbv2_cost_region = {}
        with open('elbv2_pricing.json','r') as elb2:
            elbv2_pricing = json.load(elb2)

        for region_name in regions:
            total_elbv2_cost = 0
            elbv2_cost_region[region_name] = {}

            conn = self.connect('elbv2', region_name=region_name)
            lb = conn.describe_load_balancers()
            network_elb = len(lb['LoadBalancers'])
            self.dictionary[region_name]['ELBV2']  = {
                                 'Length': network_elb
                                                    }
            
            for elbv2_price in elbv2_pricing[region_name]['ELB']['OnDemand']:
                elbv2_cost = float(elbv2_pricing[region_name]['ELB']['OnDemand']['USD'])
                total_elbv2_cost = round(float( elbv2_cost * network_elb *730.5), 3)
                elbv2_cost_region[region_name] = {
                    'Elbv2_Cost': total_elbv2_cost,
                    'Total_length': network_elb,
                    'Cost': elbv2_cost
                }
        self.network_elb = elbv2_cost_region

    def get_ebs_resources(self, regions):
        with open('ebs_pricing_list.json','r') as ebs:
            vol_pricing = json.load(ebs)
        sts_response = self.sts_client.get_caller_identity()
        user_account = sts_response['Account']
        vol_cost_region = {}   
        snap_vol_region = {}
        snapshot_count_region= {}

        for region_name in regions:
            snap_vol = []
            snap_vol_region[region_name] = {}
            vol_cost_region[region_name] = {
                    'attached' : {},
                    'unattached' : {}
            }
            attached_list = {}
            unattached_list = {}
            snapshot_count_region[region_name] = {}
            snap_vol = []
            attached_vol_list = []
            unattached_vol_list = []
            conn = self.connect('ec2', region_name=region_name)

            volumes = conn.describe_volumes()
            vol_length = len(volumes['Volumes'])
            snapshots = conn.describe_snapshots(Filters=[
                {
                    'Name' : 'owner-id',
                    'Values' : [
                    str(user_account),
                    ]
                }
            ])
            snapshot_length = len(snapshots['Snapshots'])
   
            for vol in volumes['Volumes']:
                if len(vol['Attachments']):
                    if not vol['VolumeId'] in attached_vol_list:
                        attached_vol_list.append(vol['VolumeId'])
                else:
                    if not vol['VolumeId'] in unattached_vol_list:
                        unattached_vol_list.append(vol['VolumeId'])

             
                vol_id = vol['VolumeId']
                self.dictionary[region_name]['EBS'][vol_id] = {
                    'state': vol['State'],
                    'snapshots': [],
                    'size': vol['Size'],
                    'volumeType': vol['VolumeType']
                }

                v_type = vol['VolumeType']
                for vol_type in vol_pricing[region_name]['EBS']:
                    if self.dictionary[region_name]['EBS'][vol_id]['volumeType'] in vol_type:
                        if vol_id in attached_vol_list:
                                if not v_type in attached_list:
                                        attached_list[v_type]={'count' : 0, 'size' : 0}
                                else:
                                        attached_list[v_type]['count'] +=1 
                                        attached_list[v_type]['size'] += self.dictionary[region_name]['EBS'][vol_id]['size']
                                        attached_list[v_type]['price'] = float(vol_pricing[region_name]['EBS'][v_type]['OnDemand']['USD'])
                       
                        if vol_id in unattached_vol_list:
                                if not v_type in unattached_list:
                                        unattached_list[v_type]={'count' : 0, 'size' : 0}
                                else:
                                        unattached_list[v_type]['count'] +=1 
                                        unattached_list[v_type]['size'] += self.dictionary[region_name]['EBS'][vol_id]['size']
                                        unattached_list[v_type]['price'] = float(vol_pricing[region_name]['EBS'][v_type]['OnDemand']['USD'])
                
                vol_cost_region[region_name]['attached'] = attached_list 
                vol_cost_region[region_name]['unattached'] = unattached_list

            self.volume_ebs = vol_cost_region         
            
            orphaned_snapshot_count = 0
            snapshot_count = 0
        #Get all snapshots and assign them to their volume
            for snapshot in snapshots['Snapshots']:
                snap = snapshot['VolumeId']
                if snap in self.dictionary[region_name]['EBS']:
                    self.dictionary[region_name]['EBS'][snap]['snapshots'].append(snapshot['SnapshotId'])
                    if not snap in snap_vol:
                        snap_vol.append(snap)
                        snapshot_count = snapshot_count + 1
                else:
                    self.dictionary[region_name]['EBS']['orphaned_snapshots'].append(snapshot['SnapshotId'])
                    orphaned_snapshot_count = orphaned_snapshot_count + 1

            snap_vol_region[region_name] = snap_vol
            self.snap_vol_id = snap_vol_region

            snapshot_count_region[region_name] = {
                'sc': snapshot_count,
                'osc': orphaned_snapshot_count
            }
            self.snapshot_ebs = snapshot_count_region

    def get_price(self, EC2_counts, classic_elb, network_elb, volume, snapshot):
        with open('epl1.json', 'r') as fp:
            pricing_json = json.load(fp)
        with open('elb_pricing.json','r') as elb:
            elb_pricing = json.load(elb)
        with open('snapshots_price.json', 'r') as fp:
            snapshot_pricing = json.load(fp)
        

        #Pricing
        for region in EC2_counts: 
            x.add_row([region, '', '', '', '', '',''])
            total_coi = 0
            total_cost = 0
            total_size = 0
            ppm = 0
            sc_length = 0
            osc_length = 0
            price =0
            snap_price = 0
            total_size = 0
            total_cost = 0.00
            unattached_volume_cost = 0.00
            attached_volume_cost = 0.00
            unattached_length = 0
            attached_length = 0
            
            x.add_row(['', 'EC2 Running Instances', '', '', '', '', ''])
            for i_types in EC2_counts[region]:
                if i_types in (instance_type for instance_type in pricing_json[region]['EC2']):
                    count_of_instances = round(float(EC2_counts[region][i_types]['count']), 3)
                    price = round(float(pricing_json[region]['EC2'][i_types]['OnDemand']['USD']), 3)

                    total_coi = total_coi + (EC2_counts[region][i_types]['count'])
                    total_cost = round(float(total_cost+(price*count_of_instances)),3)
                    
                    x.add_row(['', '', i_types, EC2_counts[region][i_types]['count'], price, '', ''])
            x.add_row(['', '', '' , '', '', total_coi, total_cost*730.5])

        #Classic ELB pricing
            x.add_row(['', 'ELB Classic', '', '', '', '', ''])
            if region in classic_elb:
                if 'total_elb_cost' in classic_elb[region] and 'price' in classic_elb[region] and 'total_instances' in classic_elb[region]:
                    cost = classic_elb[region]['total_elb_cost']
                    elb_price = classic_elb[region]['price']
                    elb_total_instances = classic_elb[region]['total_instances']
                    x.add_row(['', '', '', '', elb_price, elb_total_instances, cost])
            
        #Network ELB pricing
            x.add_row(['', 'ELB Network', '', '', '', '', ''])
            if region in network_elb:
                # if 'total_elb_cost' in elb_cost_region[region] and 'price' in elb_cost_region[region] and 'total_instances' in elb_cost_region[region]:
                #     cost = elb_cost_region[region]['total_elb_cost']
                elbv2_price = network_elb[region]['Elbv2_Cost']
                elbv2_total_instances = network_elb[region]['Total_length']
                elbv2_cost = network_elb[region]['Cost']
                x.add_row(['', '', '', '', elbv2_cost, elbv2_total_instances, elbv2_price])

        #Volume pricing
            x.add_row(['', 'Volume', '', '', '', '', ''])
            x.add_row(['', '', 'Attached Volume', '', '', '', ''])
            x.add_row(['', '', '', '', '', '', ''])
            for status in volume[region]:
                    for vtype in volume[region][status]:
                            if status == 'attached':
                                attached_length = volume[region][status][vtype]['count'] + attached_length
                                attached_volume_cost = round(float((float(volume[region][status][vtype]['size']) * volume[region][status][vtype]['price'])+ attached_volume_cost),3)
                                x.add_row(['', '', vtype, volume[region][status][vtype]['count'], volume[region][status][vtype]['price'], volume[region][status][vtype]['size'], ''])
            x.add_row(['', '', '', '', 'Total Attached Volumes', attached_length, attached_volume_cost]) 
            x.add_row(['', '', '', '', '', '', ''])
            x.add_row(['', '', 'Orphaned Volume', '', '', '', ''])
            x.add_row(['', '', '', '', '', '', ''])
            for status in volume[region]:
                    for vtype in volume[region][status]:
                            if status == 'unattached':
                                unattached_length = volume[region][status][vtype]['count'] + unattached_length
                                unattached_volume_cost = round(float((float(volume[region][status][vtype]['size']) * volume[region][status][vtype]['price'])+ unattached_volume_cost),3)
                                x.add_row(['', '', vtype, volume[region][status][vtype]['count'], volume[region][status][vtype]['price'], volume[region][status][vtype]['size'], ''])
            x.add_row(['', '', '', '', 'Total Orphaned Volumes', unattached_length, unattached_volume_cost])              
        #Snapshots pricing
            x.add_row(['', 'Snapshots', '', '', '', '', ''])
            x.add_row(['', '', '', '', '', '', ''])
            if region in snapshot:
                sc_length = snapshot[region]['sc']
                osc_length = snapshot[region]['osc']
            if region in (reg for reg in snapshot_pricing):
                    snap_price =  float(snapshot_pricing[region]['Snapshot']['OnDemand']['USD'])
            for volume_id in self.snap_vol_id[region]:
                if volume_id in (vol_id for vol_id in self.dictionary[region]['EBS']):
                    size = self.dictionary[region]['EBS'][volume_id]['size']
                    total_size = total_size + size 
                ppm = round(float(snap_price * float(total_size)),3)
            x.add_row(['', '', 'snapshots', sc_length, snap_price, total_size, ppm])
            x.add_row(['', '', 'orphaned snapshots', osc_length, snap_price, '', round(float(snap_price*osc_length),3)])

        print(x)

aws_audit = AWSAudit()


