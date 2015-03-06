DynamoDB
===========

Save signals to an AWS DynamoDB

Properties
--------------

 - **Table**: (expression) The name of the table to save to
 - **AWS Region**: The AWS region to save to
 - **Hash Key**: (string) The attribute on the signals that will be the hash key in the table - This is required
 - **Range Key**: (string) (optional) The attribute on the signals that will be the range key in the table - This is optional, if left blank, no validation will be done and any tables created will not contain a range key.
 - **Access Key**: An AWS Access Token
 - **Access Secret**: The AWS Access Token's secret


Dependencies
----------------

 * boto - https://github.com/boto/boto

Commands
----------------
None

Input
-------
Any list of signals.

Signals must have the attribute of the **hash_key** defined. If a range key is also specified, then the signals must also contain that as an attribute.

Note that errors may occur if the type of the hash key attribute is different than the type of the hash key on the DynamoDB table.

Output
---------
None
