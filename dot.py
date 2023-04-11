# -*- coding:utf-8 -*-

import boto3
import json

try:
    # sts의 get-caller-identity를 통해 SDK 사용 가능 여부를 확인 합니다.
    try:
        sts_client = boto3.client("sts")
        caller_identity = sts_client.get_caller_identity()
    except Exception as e:
        print("STS 인증에 실패했습니다. 권한 부여가 정상적인지 확인하세요.", e)
        exit()
except Exception as e:
    print("Boto3가 올바르게 설치되지 않았습니다. python3 -m pip install boto3 --upgarde 명령을 통해 설치를 진행해주세요.", e)
    exit()

# Instance ID를 검증합니다.
ec2_client = boto3.client("ec2")
while True:
    target = input("Instance ID를 입력해주세요. : ").strip()
    try:
        response = ec2_client.describe_instances(InstanceIds=[target])
        if len(response["Reservations"]) > 0:
            break
        else:
            print("존재하지 않는 Instance ID 입니다. Instance ID를 다시 입력하세요.")
    except:
        print("알 수 없는 에러가 Instance ID 입력에서 발생하였습니다. 다시 실행해주세요.")

# EBS volume ID를 검증합니다.
while True:
    volume_id = input("EBS volume ID를 입력해주세요. : ").strip()
    try:
        response = ec2_client.describe_volumes(VolumeIds=[volume_id])
        if len(response["Volumes"]) > 0:
            break
        else:
            print("존재하지 않는 Volume ID 입니다. Volume ID를 다시 입력하세요.")
    except:
        print("알 수 없는 에러가 Volume ID 입력에서 발생하였습니다. 다시 실행해주세요.")

# Device 이름을 검증합니다.
while True:
    device_name = input("Device 이름을 입력해주세요. (e.g. /dev/sda1) : ").strip()
    try:
        response = ec2_client.describe_instance_attribute(
            InstanceId=target, Attribute="blockDeviceMapping"
        )
        device_names = [mapping["DeviceName"] for mapping in response["BlockDeviceMappings"]]
        if device_name in device_names:
            break
        else:
            print("존재하지 않는 Device 이름 입니다. Device 이름을 다시 입력하세요.")
    except:
        print("알 수 없는 에러가 Device 이름 입력에서 발생하였습니다. 다시 실행해주세요.")


# 종료 시 삭제 옵션을 검증합니다.
while True:
    dot = input("종료 시 삭제 옵션을 입력해주세요. (e.g. true / false) : ").strip()
    if dot.lower() in ["true", "false"]:
        break
    else:
        print("입력 값이 잘못되었습니다. 확인 후 다시 입력해주세요.")

# 리전 정보를 검증합니다.
while True:
    region = input("Region 정보를 입력해주세요. 입력하지 않는 경우, ap-northeast-2 를 기본값으로 사용합니다. : ").strip()
    if region == "":
        region = "ap-northeast-2"
        break
    try:
        ec2_client.describe_regions(RegionNames=[region])
        break
    except:
        print("존재하지 않는 Region 정보 입니다. Region 정보를 다시 입력하세요.")

# 사용자 입력 값을 보여줍니다.
print(" ")
print("--------------------------------------")
print("사용자 입력 값은 아래와 같습니다.")
print("--------------------------------------")
print(
    "Instance ID: {}\nEBS volume ID: {}\nDevice name: {}\nDelete option on exit: {}\nRegion: {}".format(
        target, volume_id, device_name, dot, region
    )
)
print("--------------------------------------")
print(" ")

# Dry-Run을 통해 작업이 가능한 상태인지 확인합니다.
try:
    ec2_client = boto3.client("ec2", region_name=region)
    dry_run_output = ec2_client.modify_instance_attribute(
        DryRun=True,
        InstanceId=target,
        BlockDeviceMappings=[
            {
                "DeviceName": device_name,
                "Ebs": {"DeleteOnTermination": dot == "true", "VolumeId": volume_id},
            }
        ],
    )

except Exception as e:
    if "DryRunOperation" not in str(e):
        print("알 수 없는 에러 Dry-Run 확인 중 발생하였습니다.")
        exit()

# Dry-Run 수행 결과를 확인하고 작업을 수행할지 선택합니다.
confirm = input(
    "Dry-Run 실행 결과 정상으로 확인되었습니다.\n해당 명령을 수행하는 경우, 발생할 문제에 대해 인지하였고 동의하는 것으로 판단합니다.\n진행하시겠습니까? (Y/n)"
).lower()
if confirm != "y":
    print("실행을 취소합니다.")
    exit()

# 실행 전 결과를 저장합니다.
ec2 = boto3.resource("ec2", region_name=region)
instance = ec2.Instance(target)
before = instance.block_device_mappings

# 수행할 명령은 아래에서 실행됩니다.
try:
    ec2_client.modify_instance_attribute(
        DryRun=False,
        InstanceId=target,
        BlockDeviceMappings=[
            {
                "DeviceName": device_name,
                "Ebs": {"DeleteOnTermination": dot == "true", "VolumeId": volume_id},
            }
        ],
    )
except Exception as e:
    print("알 수 없는 에러 modify_instance_attribute 중 발생하였습니다.")
    exit()

# 실행 후 결과를 저장합니다.
instance.reload()
after = instance.block_device_mappings

print(" ")
print("--------------------------------------")
print("실행 후 정보는 아래와 같습니다.")
print(" ")
print("{:<20}{}".format("Instance ID:", target))
print("{:<20}{}".format("EBS volume ID:", volume_id))
print("{:<20}{}".format("Device name:", device_name))
print("{:<20}{}".format("Delete on exit:", dot))
print("{:<20}{}".format("Region:", region))
print(" ")
print("--------------------------------------")
print("실행 전 정보는 아래와 같습니다.")
print("--------------------------------------")
for mapping in before:
    print("{:<20}{}".format("Instance ID:", instance.id))
    print("{:<20}{}".format("EBS volume ID:", mapping["Ebs"]["VolumeId"]))
    print("{:<20}{}".format("Device name:", mapping["DeviceName"]))
    print("{:<20}{}".format("Delete on exit:", mapping["Ebs"]["DeleteOnTermination"]))
    print("{:<20}{}".format("Region:", region))
print("--------------------------------------")
print(" ")
