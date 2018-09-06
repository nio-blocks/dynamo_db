DynamoDBInsert
==============
The DynamoDBInsert block inserts incoming signals into a [AWS DynamoDB](https://aws.amazon.com/documentation/dynamodb/).

Properties
----------
- **creds**: AWS credentials to connect to the DynamoDB with.
- **hash_key**: The attribute on the signals that will be the hash key in the table (required).
- **range_key**: The attribute on the signals that will be the range key in the table (optional). If left blank, no validation will be done and any tables created will not contain a range key.
- **region**: The AWS region the DynamoDB is located in.
- **table**: The name of the DynamoDB table to insert into.

Inputs
------
- **default**: Any list of signals. Signals must have the attribute of the `hash_key` defined. If a `range_key` is also specified, then the signals must also contain that as an attribute. Note that errors may occur if the type of the `hash_key` attribute is different than the type of the `hash_key` on the DynamoDB table.

Outputs
-------
None

Commands
--------
None

Dependencies
------------
 * [boto](https://github.com/boto/boto)

***

DynamoDBQuery
=============
The DynamoDBQuery block queries a AWS DynamoDB and outputs the query result as a signal.

Properties
----------
- **creds**: AWS credentials to connect to the DynamoDB with.
- **enrich**: Signal Enrichment
  - *exclude_existing*: If checked (true), the attributes of the incoming signal will be excluded from the outgoing signal. If unchecked (false), the attributes of the incoming signal will be included in the outgoing signal.
  - *enrich_field*: (hidden) The attribute on the signal to store the results from this block. If this is empty, the results will be merged onto the incoming signal. This is the default operation. Having this field allows a block to 'save' the results of an operation to a single field on an incoming signal and notify the enriched signal.
- **limit**: An integer count of the maximum number of items to return per query.
- **query_filters**: Filtering options for limiting the query results. Must be of the format `<fieldname>__<filter_operation>`. Options for `filter_operations` are `eq`, `lt`, `lte`, `gt`, `gte`, `between` and (for strings only) `beginswith`.
- **region**: The AWS region the DynamoDB is located in.
- **reverse**: Outgoing signal list will be in reverse order of the query result.
- **table**: The name of the DynamoDB table to query from.

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

