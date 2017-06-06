DynamoDBInsert
==============

Save signals to an AWS DynamoDB.

Properties
----------

 - **table**: (type=expression) The name of the table to save to
 - **AWS_region**: The AWS region to save to
 - **hash_key**: (type=string) The attribute on the signals that will be the hash key in the table (required)
 - **range_key**: (type=string) The attribute on the signals that will be the range key in the table (optional). If left blank, no validation will be done and any tables created will not contain a range key.
 - **access_key**: An AWS Access Token
 - **access_secret**: The AWS Access Token's secret


Dependencies
------------

 * [boto](https://github.com/boto/boto)

Commands
--------
None

Input
-----
Any list of signals.

Signals must have the attribute of the `hash_key` defined. If a `range_key` is also specified, then the signals must also contain that as an attribute.

Note that errors may occur if the type of the `hash_key` attribute is different than the type of the `hash_key` on the DynamoDB table.

Output
------
None

***

DynamoDBQuery
=============

Read signals from AWS DynamoDB.

**filter_keys**: Must be of the format `<fieldname>__<filter_operation>`. Options for `filter_operations` are `eq`, `lt`, `lte`, `gt`, `gte`, `between` and (for strings only) `beginswith`.
**limit**: An integer count of the total number of items to return per query
**reverse**: Output signal list will be in reverse order

A query for the hash\_key equal to a value must be present in the query. For example, if `name` is the hash\_key, then one `filter_key` must be `name__eq`.

Note that errors may occur if the type of the table attribute is different than the type of the `filter_value`.

Properties
----------

 - **table**: (type=expression) The name of the table to save to
 - **AWS_region**: The AWS region to save to
 - **access_key**: An AWS Access Token
 - **access_secret**: The AWS Access Token's secret
 - **query_filters**: Key/value pairs for query (Default: `key='id__eq' value='{{ $id }}'`)


Dependencies
------------

 * [boto](https://github.com/boto/boto)

Commands
--------
None

Input
-----
Any list of signals.

Output
------
One signal for each result in the ResultSet from the query.
