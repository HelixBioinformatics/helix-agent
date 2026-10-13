#!/usr/bin/env python3
"""Small, restartable EC2/Slurm cluster using existing Academy IAM roles.

Run with uv run --with boto3 python script/tesis/aws_academy_cluster.py ACTION.
Temporary credentials and keys stay outside the repository. Only resources
recorded in the private state file and carrying this deployment's tag are used.
"""

import argparse
import base64
import configparser
import ipaddress
import json
import os
import re
import shlex
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config

ROOT = Path(__file__).resolve().parents[2]
LAB = "183928"
PRIVATE = Path.home() / ".local/state/helix/aws-academy/cluster"
STATE = PRIVATE / "state.json"
DEPLOYMENT = "helix-academy-20261012"


def configure_lab(lab):
    """Keep account credentials, keys and resource state strictly separate."""
    global LAB, PRIVATE, STATE, DEPLOYMENT
    LAB = lab
    suffix = "cluster" if lab == "183928" else "cluster-185395"
    PRIVATE = Path.home() / ".local/state/helix/aws-academy" / suffix
    STATE = PRIVATE / "state.json"
    DEPLOYMENT = "helix-academy-20261012" + ("" if lab == "183928" else "-lab2")


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as file:
            file.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def session():
    parser = configparser.ConfigParser()
    number = 1 if LAB == "183928" else 2
    parser.read(Path.home() / f".aws/helix-academy-{number}.credentials")
    values = parser["default"]
    value = boto3.Session(
        aws_access_key_id=values["aws_access_key_id"],
        aws_secret_access_key=values["aws_secret_access_key"],
        aws_session_token=values["aws_session_token"],
        region_name=values.get("region", "us-east-1"),
    )
    identity = value.client("sts").get_caller_identity()
    session_report = Path.home() / f".local/state/helix/aws-academy/session-{LAB}.json"
    expected = json.loads(session_report.read_text())["after"]["AWSAccountId"]
    if identity["Account"] != expected:
        raise RuntimeError(
            "The selected Academy account does not match the inspected account"
        )
    return value


def require_session_window():
    report = json.loads(
        (Path.home() / f".local/state/helix/aws-academy/session-{LAB}.json").read_text()
    )
    raw = report["after"]["Session to end"]
    timestamp = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4}", raw)
    if timestamp is None:
        raise RuntimeError(
            "Session deadline unavailable; renew the Academy session first"
        )
    deadline = datetime.fromisoformat(timestamp.group())
    remaining = (deadline - datetime.now(timezone.utc)).total_seconds()
    if remaining < 1800:
        raise RuntimeError(
            "Less than 30 minutes remain; use aws_academy_access.py --renew before starting nodes"
        )
    used = report["after"].get("reported_used_usd")
    budget = report["after"].get("reported_budget_usd")
    if used is None or budget is None:
        raise RuntimeError("Academy budget unavailable; refresh portal details before starting compute")
    if budget - used < 10:
        raise RuntimeError("Less than US$10 reported reserve remains; inspect delayed usage before new compute")
    print("Academy session minutes remaining:", int(remaining / 60), flush=True)


def ec2_client():
    return session().client(
        "ec2",
        config=Config(connect_timeout=6, read_timeout=20, retries={"max_attempts": 2}),
    )


def save(state):
    private_write(STATE, json.dumps(state, indent=2) + "\n")


def load():
    return json.loads(STATE.read_text())


def operator_ip():
    with urllib.request.urlopen(
        "https://checkip.amazonaws.com", timeout=10
    ) as response:
        return str(ipaddress.ip_address(response.read().decode().strip())) + "/32"


def refresh(ec2, state):
    ids = [node["id"] for node in state["nodes"] if "id" in node]
    if ids:
        rows = {
            i["InstanceId"]: i
            for r in ec2.describe_instances(InstanceIds=ids)["Reservations"]
            for i in r["Instances"]
        }
        for node in state["nodes"]:
            if "id" not in node:
                continue
            row = rows[node["id"]]
            tags = {t["Key"]: t["Value"] for t in row.get("Tags", [])}
            if tags.get("HelixDeployment") != DEPLOYMENT:
                raise RuntimeError(
                    "Ownership tag mismatch; refusing to operate on this instance"
                )
            node.update(
                state=row["State"]["Name"],
                public_ip=row.get("PublicIpAddress"),
                private_ip=row["PrivateIpAddress"],
            )
    save(state)
    return state


def deploy():
    require_session_window()
    ec2 = ec2_client()
    PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    if STATE.exists():
        state = refresh(ec2, load())
        if len(state["nodes"]) != 3:
            raise RuntimeError(
                "Incomplete deployment recorded; inspect status and stop its nodes before repairing it"
            )
        print(json.dumps(state, indent=2))
        return
    if any(
        i["State"]["Name"] not in ("terminated", "shutting-down")
        for r in ec2.describe_instances(
            Filters=[{"Name": "tag:HelixDeployment", "Values": [DEPLOYMENT]}]
        )["Reservations"]
        for i in r["Instances"]
    ):
        raise RuntimeError(
            "Tagged instances exist without a state file; refusing duplicate deployment"
        )
    images = ec2.describe_images(
        Owners=["099720109477"],
        Filters=[
            {
                "Name": "name",
                "Values": [
                    "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
                ],
            },
            {"Name": "architecture", "Values": ["x86_64"]},
            {"Name": "state", "Values": ["available"]},
        ],
    )["Images"]
    image = max(images, key=lambda x: x["CreationDate"])
    vpc = next(v for v in ec2.describe_vpcs()["Vpcs"] if v.get("IsDefault"))
    subnet = sorted(
        (
            s
            for s in ec2.describe_subnets()["Subnets"]
            if s["VpcId"] == vpc["VpcId"] and s["MapPublicIpOnLaunch"]
        ),
        key=lambda s: s["AvailabilityZone"],
    )[0]
    subnet_net = ipaddress.ip_network(subnet["CidrBlock"])
    addresses = [str(subnet_net.network_address + offset) for offset in (220, 221, 222)]
    if ec2.describe_network_interfaces(
        Filters=[{"Name": "addresses.private-ip-address", "Values": addresses}]
    )["NetworkInterfaces"]:
        raise RuntimeError("The proposed private addresses are already in use")
    state = {
        "lab": LAB,
        "deployment": DEPLOYMENT,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "region": "us-east-1",
        "image": image["ImageId"],
        "image_name": image["Name"],
        "vpc": vpc["VpcId"],
        "subnet": subnet["SubnetId"],
        "subnet_cidr": subnet["CidrBlock"],
        "operator_cidr": operator_ip(),
        "max_boot_runtime_minutes": 180,
        "nodes": [],
    }
    key = PRIVATE / "ssh-ed25519"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True
    )
    ec2.import_key_pair(
        KeyName=DEPLOYMENT, PublicKeyMaterial=key.with_suffix(".pub").read_bytes()
    )
    state["key_name"] = DEPLOYMENT
    save(state)
    group = ec2.create_security_group(
        GroupName=DEPLOYMENT,
        Description="Private Slurm/NFS traffic and SSH from the thesis operator",
        VpcId=vpc["VpcId"],
        TagSpecifications=[
            {
                "ResourceType": "security-group",
                "Tags": [{"Key": "HelixDeployment", "Value": DEPLOYMENT}],
            }
        ],
    )["GroupId"]
    state["security_group"] = group
    save(state)
    ec2.authorize_security_group_ingress(
        GroupId=group,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [
                    {
                        "CidrIp": state["operator_cidr"],
                        "Description": "Thesis operator only",
                    }
                ],
            },
            {
                "IpProtocol": "-1",
                "UserIdGroupPairs": [
                    {
                        "GroupId": group,
                        "Description": "Traffic between this cluster nodes",
                    }
                ],
            },
        ],
    )
    munge = base64.b64encode(os.urandom(128)).decode()
    private_write(PRIVATE / "munge-key-base64", munge)
    template = (ROOT / "script/tesis/aws-academy-bootstrap.sh").read_text()
    for index, (name, role, instance_type, volume_gib) in enumerate(
        (
            ("helix-head", "head", "t3.medium", 50),
            ("helix-worker1", "worker", "m5.large", 20),
            ("helix-worker2", "worker", "m5.large", 20),
        )
    ):
        data = template
        for token, value in {
            "ROLE": role,
            "NODE": name,
            "HEAD_IP": addresses[0],
            "WORKER1_IP": addresses[1],
            "WORKER2_IP": addresses[2],
            "SUBNET_CIDR": subnet["CidrBlock"],
            "MUNGE_KEY_BASE64": munge,
        }.items():
            data = data.replace("@@" + token + "@@", value)
        options = dict(
            ImageId=image["ImageId"],
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            KeyName=DEPLOYMENT,
            SubnetId=subnet["SubnetId"],
            PrivateIpAddress=addresses[index],
            SecurityGroupIds=[group],
            IamInstanceProfile={"Name": "LabInstanceProfile"},
            UserData=data,
            InstanceInitiatedShutdownBehavior="stop",
            MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
            BlockDeviceMappings=[
                {
                    "DeviceName": image["RootDeviceName"],
                    "Ebs": {
                        "VolumeSize": volume_gib,
                        "VolumeType": "gp3",
                        "DeleteOnTermination": True,
                    },
                }
            ],
            TagSpecifications=[
                {
                    "ResourceType": resource,
                    "Tags": [
                        {"Key": "Name", "Value": name},
                        {"Key": "HelixDeployment", "Value": DEPLOYMENT},
                    ],
                }
                for resource in ("instance", "volume")
            ],
            ClientToken=DEPLOYMENT + "-" + str(index),
        )
        if instance_type.startswith("t"):
            options["CreditSpecification"] = {"CpuCredits": "standard"}
        row = ec2.run_instances(**options)["Instances"][0]
        state["nodes"].append(
            {
                "name": name,
                "role": role,
                "type": instance_type,
                "root_volume_gib": volume_gib,
                "id": row["InstanceId"],
                "private_ip": addresses[index],
            }
        )
        save(state)
        print("Created", name, row["InstanceId"], flush=True)
    print(json.dumps(refresh(ec2, state), indent=2))


def ssh_options(node):
    return [
        "-i",
        str(PRIVATE / "ssh-ed25519"),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "UserKnownHostsFile=" + str(PRIVATE / "known_hosts"),
        "-o",
        "HostKeyAlias=" + node["id"],
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ServerAliveInterval=15",
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab", choices=["183928", "185395"], default="183928")
    parser.add_argument(
        "action", choices=["deploy", "status", "start", "stop", "exec", "put", "get"]
    )
    parser.add_argument("--node", default="helix-head")
    parser.add_argument("args", nargs="*")
    args = parser.parse_args()
    configure_lab(args.lab)
    if args.action == "deploy":
        deploy()
        return
    ec2 = ec2_client()
    state = refresh(ec2, load())
    if args.action == "status":
        print(json.dumps(state, indent=2))
        return
    if args.action in ("start", "stop"):
        if args.action == "start":
            require_session_window()
        target = "stopped" if args.action == "start" else "running"
        ids = [node["id"] for node in state["nodes"] if node["state"] == target]
        if args.action == "start" and operator_ip() != state["operator_cidr"]:
            group = state["security_group"]
            ec2.revoke_security_group_ingress(
                GroupId=group,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpRanges": [{"CidrIp": state["operator_cidr"]}],
                    }
                ],
            )
            state["operator_cidr"] = operator_ip()
            ec2.authorize_security_group_ingress(
                GroupId=group,
                IpPermissions=[
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpRanges": [
                            {
                                "CidrIp": state["operator_cidr"],
                                "Description": "Thesis operator only",
                            }
                        ],
                    }
                ],
            )
            save(state)
        if ids:
            getattr(ec2, args.action + "_instances")(InstanceIds=ids)
            print(args.action, ids, "waiting for EC2 state", flush=True)
            ec2.get_waiter(
                "instance_running" if args.action == "start" else "instance_stopped"
            ).wait(InstanceIds=ids, WaiterConfig={"Delay": 10, "MaxAttempts": 30})
        print(json.dumps(refresh(ec2, state), indent=2))
        return
    node = next(node for node in state["nodes"] if node["name"] == args.node)
    if node["state"] != "running" or not node["public_ip"]:
        raise RuntimeError(
            "Node is not running; start the Academy session and cluster first"
        )
    target = "ubuntu@" + node["public_ip"]
    if args.action == "exec":
        subprocess.run(
            [
                "ssh",
                *ssh_options(node),
                target,
                "bash -lc " + shlex.quote(" ".join(args.args)),
            ],
            check=True,
        )
    else:
        if len(args.args) != 2:
            parser.error("put/get require source and destination")
        source, destination = args.args
        if args.action == "put":
            destination = target + ":" + destination
        else:
            source = target + ":" + source
        subprocess.run(
            ["scp", *ssh_options(node), "-r", source, destination], check=True
        )


if __name__ == "__main__":
    main()
