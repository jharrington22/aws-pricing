# AWS Audit and pricing

A python package to audit the AWS Resources and total spending by
* generating the resource list by region and resource type(used/unused)
* generate pricing list from AWS pricing API for each region and resource type

### Installation

    $ pip install aws_auditing_list

### Requirements 

Install boto3>=1.9.163
https://pypi.python.org/pypi/boto#downloads

Install prettytable>=0.7.2
https://pypi.org/project/PrettyTable#downloads

argparse
https://docs.python.org/3/library/argparse.html

## CLI Tools

```

arguments: 
-h, --help              show this help message and exit
--region REGION
                        AWS Region
--pricing, -p 
                        get the pricing for the region
--resources, -r 
                        get the resources for the region
--orphaned_volume, -ov 
                        get volume IDs with no Instance Ids attached
--orphaned_snapshot, -os 
                        get snapshot IDs with no parent volume
```

## Usage

To get the pricing of the resources in a particular region
```
usage: python3 aws_auditing_list [--region] [-p]
```

To get the resource list in a particular region
```
usage: python3 aws_auditing_list [--region] [-r]
```

## Credentials
In the aws director @localhost: ~/.aws/ 
