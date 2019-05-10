# Automate AMI Backups and Cleanup via cloudformation

## Original python code from https://gist.github.com/bkozora

## Setup

- Create s3 bucket
- zip both .py files and upload to s3 bucket
- run cloudformation

The Cron and the names of the files and bucket is all parameterised in the cloudformation
if works accross regions, give your instances a Backup and Retention tags.

The backup script will search for all instances having a tag with "Backup" or "backup" on it. 
As soon as we have the instances list, we loop through each instance and create an AMI of it. Also. 
It will look for a "Retention" tag key which will be used as a retention policy number in days. 

If there is no tag with that name, it will use a 7 days default value for each AMI.

After creating the AMI it creates a "DeleteOn" tag on the AMI indicating when it will be deleted using the Retention value and the cleanup Lambda function

