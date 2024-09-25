import boto3
import sys

# Initialize boto3 clients
ec2 = boto3.resource("ec2")
elbv2 = boto3.client("elbv2")
autoscaling = boto3.client("autoscaling")
sns = boto3.client("sns")
s3 = boto3.client("s3")


def get_config():
    """Centralize configuration constants."""
    config = {
        "vpc_id": "vpc-0321f38a7b594180d",  # Replace with your VPC ID
        "subnets": [
            "subnet-0f30c30418def6379",
            "subnet-03ca36de9a927fe8e",
            "subnet-06bd72b2e4cb41d10",
            "subnet-09bd0e0acc92d4efa",
        ],  # Replace with your subnet IDs
        "security_group": "launch-wizard-63",  # Replace with your Security Group ID
        "security_group1": "sg-057f0e6c8849c7ff8",  # Replace with your Security Group ID
        "key_name": "studentpk-key",  # Replace with your EC2 Key Pair name
        "bucket_name": "pk1-my-static-webapp-bucket",  # Replace with unique S3 bucket name
        "email": "Prashanth153@gmail.com",  # Replace with your email for SNS notifications
    }
    return config


def delete_ami(ami_id):
    """Delete the specified AMI."""
    ec2_client.deregister_image(ImageId=ami_id)
    print(f"AMI {ami_id} deregistered.")


def delete_s3_bucket(bucket_name):
    """Delete all objects in the S3 bucket and then the bucket itself."""
    try:
        # List and delete all objects in the bucket
        objects = s3.list_objects_v2(Bucket=bucket_name)
        if "Contents" in objects:
            for obj in objects["Contents"]:
                s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
                print(f"Deleted {obj['Key']} from {bucket_name}")

        # Delete the bucket itself
        s3.delete_bucket(Bucket=bucket_name)
        print(f"S3 bucket {bucket_name} deleted successfully.")
    except Exception as e:
        print(f"Error deleting S3 bucket: {e}")


def delete_ec2_instance(instance_id):
    """Terminate the EC2 instance."""
    try:
        instance = ec2.Instance(instance_id)
        instance.terminate()
        instance.wait_until_terminated()
        print(f"EC2 instance {instance_id} terminated.")
    except Exception as e:
        print(f"Error terminating EC2 instance {instance_id}: {e}")


def delete_ami(ami_id):
    """Deregister the AMI."""
    try:
        ec2.Image(ami_id).deregister()
        print(f"AMI {ami_id} deregistered.")
    except Exception as e:
        print(f"Error deregistering AMI {ami_id}: {e}")


# Initialize boto3 clients
ec2_client = boto3.client("ec2")  # Define this first


def delete_ami_by_name(ami_name):
    """Delete the AMI with the specified name if it exists."""
    try:
        images = ec2_client.describe_images(
            Filters=[{"Name": "name", "Values": [ami_name]}]
        )
        for image in images["Images"]:
            ami_id = image["ImageId"]
            print(f"Deleting AMI {ami_id} with name {ami_name}...")
            ec2_client.deregister_image(ImageId=ami_id)
            print(f"AMI {ami_id} deleted.")
    except Exception as e:
        print(f"Error deleting AMI: {e}")


def delete_load_balancer(lb_arn):
    """Delete the load balancer."""
    try:
        elbv2.delete_load_balancer(LoadBalancerArn=lb_arn)
        print(f"Load Balancer {lb_arn} deleted.")
    except Exception as e:
        print(f"Error deleting Load Balancer {lb_arn}: {e}")


def delete_target_group(tg_arn):
    """Delete the target group."""
    try:
        elbv2.delete_target_group(TargetGroupArn=tg_arn)
        print(f"Target group {tg_arn} deleted.")
    except Exception as e:
        print(f"Error deleting Target Group {tg_arn}: {e}")


def delete_auto_scaling_group(asg_name):
    """Delete the auto-scaling group."""
    try:
        autoscaling.delete_auto_scaling_group(
            AutoScalingGroupName=asg_name, ForceDelete=True
        )
        print(f"Auto Scaling Group {asg_name} deleted.")
    except Exception as e:
        print(f"Error deleting Auto Scaling Group {asg_name}: {e}")


def delete_launch_configuration(lc_name):
    """Delete the launch configuration."""
    try:
        autoscaling.delete_launch_configuration(LaunchConfigurationName=lc_name)
        print(f"Launch Configuration {lc_name} deleted.")
    except Exception as e:
        print(f"Error deleting Launch Configuration {lc_name}: {e}")


def cleanup_resources(config, instance_id, ami_id, lb_arn, tg_arn, asg_name, lc_name):
    """Delete all resources created in the deployment."""
    print("Starting cleanup...")

    # Delete S3 bucket
    delete_s3_bucket(config["bucket_name"])
    # sys.exit(0)

    # Delete EC2 instance
    delete_ec2_instance(instance_id)

    # Deregister AMI
    delete_ami(ami_id)

    # Delete Load Balancer
    delete_load_balancer(lb_arn)

    # Delete Target Group
    delete_target_group(tg_arn)

    # Delete Auto Scaling Group
    delete_auto_scaling_group(asg_name)

    # Delete Launch Configuration
    delete_launch_configuration(lc_name)

    print("Cleanup complete.")


def main():
    config = get_config()  # Get all static configuration values
    # delete_ami_by_name("pk1-nginx-webapp-ami")
    delete_ami_by_name("pk1-nginx-webapp-ami")
    # Assume the resources have already been created in a previous run
    instance_id = "i-0123456789abcdef0"  # Replace with your EC2 instance ID
    ami_id = "ami-0123456789abcdef0"  # Replace with your AMI ID
    lb_arn = "arn:aws:elasticloadbalancing:region:account-id:loadbalancer/app/name/id"  # Replace with your Load Balancer ARN
    tg_arn = "arn:aws:elasticloadbalancing:region:account-id:targetgroup/name/id"  # Replace with your Target Group ARN
    asg_name = "pk1-webapp-asg"  # Replace with your Auto Scaling Group name
    lc_name = "pk1-webapp-launch-config"  # Replace with your Launch Configuration name

    # Perform cleanup
    cleanup_resources(config, instance_id, ami_id, lb_arn, tg_arn, asg_name, lc_name)


if __name__ == "__main__":
    main()
