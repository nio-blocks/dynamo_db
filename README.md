DynamoDBInsert
==============

Save signals to an AWS DynamoDB.

Properties
----------
- **creds**: AWS credentials to connect with
  - **access_key**: An AWS Access Token
  - **access_secret**: The AWS Access Token's secret
- **hash_key**: The attribute on the signals that will be the hash key in the table (required)
- **range_key**: The attribute on the signals that will be the range key in the table (optional). If left blank, no validation will be done and any tables created will not contain a range key.
- **region**: The AWS region to connect to
- **table**: The name of the table to save to

Inputs
------
- **default**: Any list of signals.
Signals must have the attribute of the `hash_key` defined. If a `range_key` is also specified, then the signals must also contain that as an attribute.
Note that errors may occur if the type of the `hash_key` attribute is different than the type of the `hash_key` on the DynamoDB table.

Outputs
-------
- **default**: One signal for each result in the ResultSet from the query.

Commands
--------
None

Dependencies
------------
 * [boto](https://github.com/boto/boto)

DynamoDBQuery
=============

Read signals from AWS DynamoDB.

Properties
----------
- **creds**:
  - **access_key**: An AWS Access Token
  - **access_secret**: The AWS Access Token's secret
- **limit**: An integer count of the total number of items to return per query
- **query_filters**: Must be of the format `<fieldname>__<filter_operation>`. Options for `filter_operations` are `eq`, `lt`, `lte`, `gt`, `gte`, `between` and (for strings only) `beginswith`.
- **region**: The AWS region to connect to
- **reverse**: Output signal list will be in reverse order
- **table**: The name of the table to save to

Inputs
------
- **default**: Any list of signals.

Outputs
-------
- **default**: One signal for each result in the ResultSet from the query.

Commands
--------
None

Dependencies
------------
 * [boto](https://github.com/boto/boto)
