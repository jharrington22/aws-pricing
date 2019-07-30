
#Region short names
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

#Dictionary to store values
resources = {}

#List of keys in the dict region_short_names
aws_region = list(region_short_names.keys())