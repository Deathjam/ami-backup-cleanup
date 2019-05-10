#!/usr/bin/python
# -*- coding: utf-8 -*-
# Automated AMI Backups
#
# @author Robert Kozora <bobby@kozora.me>
#
# This script will search for all instances having a tag with "Backup" or "backup"
# on it. As soon as we have the instances list, we loop through each instance
# and create an AMI of it. Also, it will look for a "Retention" tag key which
# will be used as a retention policy number in days. If there is no tag with
# that name, it will use a 7 days default value for each AMI.
#
# After creating the AMI it creates a "DeleteOn" tag on the AMI indicating when
# it will be deleted using the Retention value and another Lambda function

import boto3
import collections
import datetime
import sys
import pprint
import time


def lambda_handler(event, context):

    regions = boto3.session.Session().get_available_regions('ec2')  # ec2.regions()

    for x in regions:

        print 'Region_name %s' % x

    for x in regions:

        print 'Region_name %s' % x

        ec = boto3.client('ec2', region_name=x)
        reservations = ec.describe_instances(Filters=[{'Name': 'tag-key'
                , 'Values': ['backup', 'Backup']}]).get('Reservations',
                [])

        instances = sum([[i for i in r['Instances']] for r in
                        reservations], [])

        print 'Found %d instances that need backing up' % len(instances)

        to_tag = collections.defaultdict(list)

        inDone = []

        for instance in instances:

            # BlockDeviceMappings=[
                # {
                    # 'DeviceName': '/dev/sdf',
                    # 'NoDevice': '',
                # },
            # ],

            try:
                no_devices_tag = [str(t.get('Value')) for t in
                                  instance['Tags'] if t['Key']
                                  == 'DoNotImage'][0]
            except IndexError:
                no_devices_tag = ''

            try:
                no_device_array = []

                if len(no_devices_tag) > 0:
                    no_devices = no_devices_tag.split(',')

                    for no_device in no_devices:
                        no_device_array.append({'DeviceName': no_device.strip(),
                                'NoDevice': ''})

                    print 'DoNotImage values to process %s ' \
                        % len(no_device_array)
            except:
                no_device_array = []

            try:
                ami_name = [str(t.get('Value')) for t in instance['Tags'
                            ] if t['Key'] == 'Name'][0]
            except IndexError:
                ami_name = ''

            try:
                retention_days = [int(t.get('Value')) for t in
                                  instance['Tags'] if t['Key']
                                  == 'Retention'][0]
            except IndexError:
                retention_days = 7
            finally:

            # for dev in instance['BlockDeviceMappings']:
            #    if dev.get('Ebs', None) is None:
            #        continue
            #    vol_id = dev['Ebs']['VolumeId']
            #    print "Found EBS volume %s on instance %s" % (
            #        vol_id, instance['InstanceId'])

                # snap = ec.create_snapshot(
                #    VolumeId=vol_id,
                # )

                # create_image(instance_id, name, description=None, no_reboot=False, block_device_mapping=None, dry_run=False)
                # DryRun, InstanceId, Name, Description, NoReboot, BlockDeviceMappings

                create_time = datetime.datetime.now()
                create_fmt = create_time.strftime('%Y-%m-%d')

                # AMIid = ec.create_image(InstanceId=instance['InstanceId'], Name="Lambda - " + instance['InstanceId'] + " from " + create_fmt, Description="Lambda created AMI of instance " + instance['InstanceId'] + " from " + create_fmt, NoReboot=True, DryRun=False)

                try:
                    if str(instance['InstanceId']) not in inDone:

                        if len(no_device_array) > 0:
                            AMIid = ec.create_image(
                                InstanceId=instance['InstanceId'],
                                Name=create_fmt + ' - ' + ami_name + ' - ' + instance['InstanceId'] + ' - Lambda Backups',
                                Description='Lambda created AMI of instance ' + instance['InstanceId'] + ' from ' + create_fmt,
                                NoReboot=True,
                                DryRun=False,
                                BlockDeviceMappings=no_device_array,
                                )
                        else:
                            AMIid = \
                                ec.create_image(InstanceId=instance['InstanceId'],
                                    Name=create_fmt + ' - ' + ami_name + ' - ' + instance['InstanceId'] + ' - Lambda Backups',
                                    Description='Lambda created AMI of instance ' + instance['InstanceId'] + ' from ' + create_fmt,
                                    NoReboot=True,
                                    DryRun=False)

                        inDone.insert(0, str(instance['InstanceId']))

                        print 'Created AMI %s of instance %s ' \
                            % (AMIid['ImageId'], instance['InstanceId'])
                    else:

                        print 'We already got an AMI of instance %s ' \
                            % instance['InstanceId']

                    pprint.pprint(instance)

                    # sys.exit()
                    # break

                    # to_tag[retention_days].append(AMIid)

                    to_tag[retention_days].append(AMIid['ImageId'])

                    print 'Retaining AMI %s of instance %s for %d days' \
                        % (AMIid['ImageId'], instance['InstanceId'],
                           retention_days)
                except Exception, e:
                    print 'Error: ' + str(e)
                    pass

                # except:
                #   print "Unexpected error:", sys.exc_info()[0]
                #   pass

        print to_tag.keys()

        for retention_days in to_tag.keys():
            delete_date = datetime.date.today() \
                + datetime.timedelta(days=retention_days)
            delete_fmt = delete_date.strftime('%Y-%m-%d')
            print 'Will delete %d AMIs on %s' \
                % (len(to_tag[retention_days]), delete_fmt)

            # break

            ec.create_tags(Resources=to_tag[retention_days],
                           Tags=[{'Key': 'DeleteOn',
                           'Value': delete_fmt}])