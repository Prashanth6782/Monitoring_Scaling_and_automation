import boto3
import sys

# Initialize boto3 clients
ec2 = boto3.resource("ec2")
elbv2 = boto3.client("elbv2")
autoscaling = boto3.client("autoscaling")
s3 = boto3.client("s3")
sns = boto3.client("sns")
cloudwatch = boto3.client("cloudwatch")


def get_config():
    """Centralize configuration constants."""
    return {
        "vpc_id": "vpc-0321f38a7b594180d",
        "subnets": [
            "subnet-0f30c30418def6379",
            "subnet-03ca36de9a927fe8e",
            "subnet-06bd72b2e4cb41d10",
            "subnet-09bd0e0acc92d4efa",
        ],
        "security_group": "launch-wizard-63",
        "security_group1": "sg-057f0e6c8849c7ff8",
        "key_name": "studentpk-key",
        "bucket_name": "pk1-my-static-webapp-bucket",
        "index_file": "index.html",
        "local_repo_path": "C:\\Users\\Acer\\OneDrive\\Python_Pk\\Graded Assignment on Monitoring, Scaling and Automation\\index.html",
        "base_ami_id": "ami-0669fb29385f494a4",
        "email": "prashanth153@gmail.com",  # Add your email here
    }


def upload_to_s3(local_path, bucket_name, s3_key):
    """Upload local file to S3 bucket."""
    try:
        s3.upload_file(local_path, bucket_name, s3_key)
        print(f"File {local_path} uploaded to S3 bucket {bucket_name} as {s3_key}.")
    except Exception as e:
        print(f"Error uploading file to S3: {e}")
        sys.exit(1)


def create_s3_bucket(bucket_name):
    """Create an S3 bucket to store static files."""
    try:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "us-west-2"},
        )
        print(f"S3 Bucket {bucket_name} created successfully.")
    except Exception as e:
        print(f"Error creating S3 bucket: {e}")
        sys.exit(1)


def create_load_balancer(config):
    """Create an Application Load Balancer (ALB) to distribute traffic."""
    lb = elbv2.create_load_balancer(
        Name="pk1-webapp-lb",
        Subnets=config["subnets"],
        SecurityGroups=[config["security_group1"]],
        Scheme="internet-facing",
        Type="application",
        IpAddressType="ipv4",
    )
    lb_arn = lb["LoadBalancers"][0]["LoadBalancerArn"]
    print(f"Load Balancer created with ARN: {lb_arn}")

    # Polling to wait until the load balancer is active
    waiter = elbv2.get_waiter("load_balancer_available")
    print(f"Waiting for Load Balancer {lb_arn} to be active...")
    waiter.wait(LoadBalancerArns=[lb_arn])
    print(f"Load Balancer {lb_arn} is now active.")
    return lb_arn


def create_target_group(config):
    """Create a target group for the ALB."""
    target_group = elbv2.create_target_group(
        Name="pk1-webapp-target-group",
        Protocol="HTTP",
        Port=80,
        VpcId=config["vpc_id"],
        TargetType="instance",
    )
    tg_arn = target_group["TargetGroups"][0]["TargetGroupArn"]
    print(f"Target group created with ARN: {tg_arn}")
    return tg_arn


def create_listener(lb_arn, tg_arn):
    """Create a listener to forward requests to the target group."""
    elbv2.create_listener(
        LoadBalancerArn=lb_arn,
        Protocol="HTTP",
        Port=80,
        DefaultActions=[{"Type": "forward", "TargetGroupArn": tg_arn}],
    )
    print("Listener created for Load Balancer.")


def wait_for_asg_instances(asg_name):
    """Poll for instances in the Auto Scaling Group to be in 'running' state."""
    print(f"Waiting for instances in Auto Scaling Group {asg_name} to be 'running'...")
    while True:
        response = autoscaling.describe_auto_scaling_groups(
            AutoScalingGroupNames=[asg_name]
        )
        instances = response["AutoScalingGroups"][0].get("Instances", [])

        if all(instance["LifecycleState"] == "InService" for instance in instances):
            print(f"All instances in Auto Scaling Group {asg_name} are now 'running'.")
            break

        print("Waiting for instances to be 'running' state...")


def create_auto_scaling_group(config, ami_id, tg_arn):
    """Create an Auto Scaling Group and define scaling policies."""
    launch_config_name = "pk1-webapp-launch-config"

    # Define the user data script for EC2 instances to copy index.html from S3 and restart Nginx
    user_data_script = f"""#!/bin/bash
set -x
exec > /var/log/user-data.log 2>&1
sudo apt-get update -y
sudo apt-get install -y software-properties-common
sudo apt-get install -y awscli
sudo aws s3 cp s3://{config["bucket_name"]}/{config["index_file"]} /var/www/html/index.html
sudo systemctl restart nginx
    """

    try:
        autoscaling.create_launch_configuration(
            LaunchConfigurationName=launch_config_name,
            ImageId=ami_id,
            InstanceType="t4g.micro",
            KeyName=config["key_name"],
            SecurityGroups=[config["security_group1"]],
            UserData=user_data_script,
        )
        print(f"Launch Configuration {launch_config_name} created.")
    except Exception as e:
        print(f"Launch Configuration creation failed: {e}")

    try:
        autoscaling.create_auto_scaling_group(
            AutoScalingGroupName="pk1-webapp-asg",
            LaunchConfigurationName=launch_config_name,
            MinSize=2,
            MaxSize=5,
            DesiredCapacity=2,
            VPCZoneIdentifier=",".join(config["subnets"]),
            TargetGroupARNs=[tg_arn],
            HealthCheckType="ELB",
            HealthCheckGracePeriod=300,
        )
        print("Auto Scaling Group created and registered with Target Group.")
    except Exception as e:
        print(f"Auto Scaling Group creation failed: {e}")

    try:
        autoscaling.put_scaling_policy(
            AutoScalingGroupName="pk1-webapp-asg",
            PolicyName="pk1-scale-up",
            AdjustmentType="ChangeInCapacity",
            ScalingAdjustment=1,
            Cooldown=60,
        )
        print("Scaling policy for scaling up created.")
    except Exception as e:
        print(f"Failed to create scaling policy: {e}")


def create_sns_topic_and_subscription(sns_client, email):
    """Create an SNS topic and subscribe the email to it."""
    try:
        response = sns_client.create_topic(Name="pk1-webapp-notifications")
        topic_arn = response["TopicArn"]
        print(f"SNS Topic created with ARN: {topic_arn}")

        # Subscribe the email to the SNS topic
        sns_client.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)
        print(
            f"Subscription created for {email}. Please check your email to confirm the subscription."
        )
        return topic_arn  # Return the topic ARN for use in the alarm
    except Exception as e:
        print(f"Error creating SNS topic or subscription: {e}")
        sys.exit(1)


def create_cloudwatch_alarm(topic_arn, tg_arn):
    """Create a CloudWatch alarm to monitor unhealthy instances in the Target Group."""
    try:
        cloudwatch.put_metric_alarm(
            AlarmName="pk1-webapp-unhealthy-instance-alarm",
            ComparisonOperator="GreaterThanThreshold",  # Trigger when there are unhealthy instances
            EvaluationPeriods=2,  # Increase evaluation periods for better consistency
            MetricName="UnHealthyHostCount",
            Namespace="AWS/ApplicationELB",
            Period=60,  # 1-minute evaluation period
            Statistic="Average",
            Threshold=1,  # Alarm triggers when more than 1 unhealthy host is detected
            ActionsEnabled=True,
            AlarmActions=[topic_arn],  # Send notification to SNS topic
            Dimensions=[
                {"Name": "TargetGroup", "Value": tg_arn},
                {"Name": "LoadBalancer", "Value": "pk1-webapp-lb"},
            ],
            AlarmDescription="Alarm when there are unhealthy instances in the Target Group",
        )
        print("CloudWatch alarm created to monitor unhealthy instances.")
    except Exception as e:
        print(f"Error creating CloudWatch alarm: {e}")


def main():
    config = get_config()

    # Step 1: Create the S3 bucket and upload the local index.html file
    create_s3_bucket(config["bucket_name"])
    upload_to_s3(config["local_repo_path"], config["bucket_name"], config["index_file"])

    # Step 2: Create the Load Balancer and Target Group
    lb_arn = create_load_balancer(config)
    tg_arn = create_target_group(config)

    # Step 3: Create a Listener for the Load Balancer
    create_listener(lb_arn, tg_arn)

    # Step 4: Create Auto Scaling Group
    create_auto_scaling_group(config, config["base_ami_id"], tg_arn)

    # Wait for instances in Auto Scaling Group to be running
    wait_for_asg_instances("pk1-webapp-asg")

    # Step 5: Set up SNS topic and CloudWatch alarm for unhealthy instances
    topic_arn = create_sns_topic_and_subscription(sns, config["email"])
    create_cloudwatch_alarm(topic_arn, tg_arn)


if __name__ == "__main__":
    main()
