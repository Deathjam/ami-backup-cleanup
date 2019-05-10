# Automated AMI and Snapshot Deletion
#
# @author Robert Kozora <bobby@kozora.me>
#
# This script will search for all instances having a tag with "Backup" or "backup"
# on it. As soon as we have the instances list, we loop through each instance
# and reference the AMIs of that instance. We check that the latest daily backup
# succeeded then we store every image that's reached its DeleteOn tag's date for
# deletion. We then loop through the AMIs, deregister them and remove all the
# snapshots associated with that AMI.

import boto3
import collections
import datetime
import time
import sys

def lambda_handler(event, context):

# Moved out of main backup region loop, we don't want errors deleting images preventing backups
    regions = boto3.session.Session().get_available_regions('ec2') #ec2.regions()
    for x in regions:

        ec2 = boto3.resource('ec2', x)
        images = ec2.images.filter(Owners=["self"])

        ec = boto3.client('ec2', region_name=x)

        reservations = ec.describe_instances(
            Filters=[
                {'Name': 'tag-key', 'Values': ['backup', 'Backup']},
            ]
        ).get(
            'Reservations', []
        )

        instances = sum(
            [
                [i for i in r['Instances']]
                for r in reservations
            ], [])

        print "Found %d instances that need evaluated" % len(instances)

        to_tag = collections.defaultdict(list)

        date = datetime.datetime.now() - datetime.timedelta(days = 1)
        date_fmt = date.strftime('%Y-%m-%d')

        imagesList = []

        # Set to true once we confirm we have a backup taken today
        backupSuccess = False

        # Loop through all of our instances with a tag named "Backup"
        for instance in instances:
            try:
                ami_name = [
                    str(t.get('Value')) for t in instance['Tags']
                    if t['Key'] == 'Name'][0]
            except IndexError:
                ami_name = ''
        imagecount = 0

        # Loop through each image of our current instance
        for image in images:

            # Our other Lambda Function names its AMIs Lambda - i-instancenumber.
            # We now know these images are auto created
            if image.name.endswith(' - Lambda Backups'):

                print "FOUND IMAGE " + image.id + " FOR INSTANCE " + instance['InstanceId']

                # Count this image's occcurance
            imagecount = imagecount + 1

            try:
                if image.tags is not None:
                    deletion_date = [
                        t.get('Value') for t in image.tags
                        if t['Key'] == 'DeleteOn'][0]
                    delete_date = time.strptime(deletion_date, "%Y-%m-%d")
            except IndexError:
                deletion_date = False
                delete_date = False

            today_time = datetime.datetime.now().strftime('%Y-%m-%d')
            # today_fmt = today_time.strftime('%Y-%m-%d')
            today_date = time.strptime(today_time, '%Y-%m-%d')
            # If image's DeleteOn date is less than or equal to today,
            # add this image to our list of images to process later

            if delete_date <= today_date:
                imagesList.append(image.id)

            # Make sure we have an AMI from today and mark backupSuccess as true
            if image.name.endswith(' - Lambda Backups'):
                # Our latest backup from our other Lambda Function succeeded
                backupSuccess = True
                print "Latest backup from " + date_fmt + " was a success"
            else:
                print "Latest backup from " + date_fmt + " was not a success in this AMI"

            print "instance " + instance['InstanceId'] + " has " + str(imagecount) + " AMIs"

            print "============="

            print "About to process the following AMIs:"
            print imagesList

            if backupSuccess == True:

                myAccount = boto3.client('sts').get_caller_identity()['Account']
                snapshots = ec.describe_snapshots(MaxResults=1000, OwnerIds=[myAccount])['Snapshots']

                # loop through list of image IDs
                for image in imagesList:
                    print "deregistering image %s" % image
                    try:
                        amiResponse = ec.deregister_image(
                            DryRun=False,
                            ImageId=image,
                        )

                        for snapshot in snapshots:
                            if snapshot['Description'].find(image) > 0:
                                snap = ec.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
                                print "Deleting snapshot " + snapshot['SnapshotId']
                                print "-------------"
                    except Exception as e:
                        print "Error: "+ str(e)
                        pass

            else:
                print "No current backup found. Termination suspended."