import boto3 
import sys

#Connection to the API endpoints
region = boto3.Session(region_name='us-east-1')
session = boto3.Session(region_name='eu-west-2')
ec2 = session.client('ec2')
pricing_client = region.client('pricing')
