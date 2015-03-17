from unittest.mock import MagicMock, patch
from time import sleep
from nio.common.signal.base import Signal
from nio.util.support.block_test_case import NIOBlockTestCase
from nio.modules.threading import spawn
from ..dynamo_db_insert_block import DynamoDBInsert
from ..dynamo_db_base_block import DynamoDBBase
from boto.exception import JSONResponseError
from boto.dynamodb2.fields import HashKey, RangeKey


class SaveCounterDynamoDB(DynamoDBInsert):

    def __init__(self):
        super().__init__()
        self._count = 0

    def execute_signals_query(self, table, signals):
        self._count += 1
        super().execute_signals_query(table, signals)


@patch(DynamoDBBase.__module__ + '.connect_to_region')
@patch(DynamoDBBase.__module__ + '.Table.create')
@patch(DynamoDBBase.__module__ + '.Table.count')
@patch('boto.dynamodb2.table.BatchTable.put_item')
class TestDynamoDBInsert(NIOBlockTestCase):

    def test_connect(self, put_func, count_func, create_func, connect_func):
        """ Make sure we connect with the right creds """
        blk = DynamoDBInsert()
        self.configure_block(blk, {
            'region': 'us_east_1',
            'creds': {
                'access_key': 'FAKEKEY',
                'access_secret': 'FAKESECRET'
            }
        })
        connect_func.assert_called_once_with(
            'us-east-1',
            aws_access_key_id='FAKEKEY',
            aws_secret_access_key='FAKESECRET')

    def test_not_table(self, put_func, count_func, create_func, connect_func):
        """ Assert that tables that aren't found are created """

        # Spit out the resource not found exception we get from AWS
        count_func.side_effect = [5, JSONResponseError(
            400,
            "{'message': 'Requested resource not found: Table: T notfound', "
            "'__type': 'com.amazonaws.dynamodb.v20120810"
            "#ResourceNotFoundException'}")]
        blk = DynamoDBInsert()
        self.configure_block(blk, {
            'log_level': 'DEBUG'
        })

        # Make sure boto didn't create the table that was found
        blk._get_table('should_be_found')
        self.assertEqual(count_func.call_count, 1)
        self.assertEqual(create_func.call_count, 0)

        # Make sure boto tried to create the table
        blk._get_table('should_not_be_found')
        self.assertEqual(count_func.call_count, 2)
        self.assertEqual(create_func.call_count, 1)

        # Make sure the two tables are cached now
        self.assertIn('should_be_found', blk._table_cache)
        self.assertIn('should_not_be_found', blk._table_cache)

        # Subsequent get table calls should hit the cache, we shouldn't see
        # the create function or the count function get called again
        blk._get_table('should_be_found')
        blk._get_table('should_not_be_found')
        self.assertEqual(count_func.call_count, 2)
        self.assertEqual(create_func.call_count, 1)

    def test_save_batch(self, put_func, count_func, create_func, connect_func):
        """ Make sure we save each table in a batch fashion """
        blk = SaveCounterDynamoDB()
        self.configure_block(blk, {
            'log_level': 'DEBUG'
        })
        blk.start()

        blk.process_signals([Signal({'_id': ''}) for i in range(5)])

        # Only one table save call, but 5 individual puts
        self.assertEqual(blk._count, 1)
        self.assertEqual(put_func.call_count, 5)

        blk.stop()

    def test_save_batch_multiple(self, put_func, count_func, create_func,
                                 connect_func):
        """ Make sure we save to different tables optimally """
        blk = SaveCounterDynamoDB()
        self.configure_block(blk, {
            'table': '{{$table}}',
            'log_level': 'DEBUG'
        })
        blk.start()

        blk.process_signals([Signal({
            'table': 'odd' if i % 2 else 'even',
            'val': i,
            '_id': ''
        }) for i in range(5)])

        # Still want 5 individual puts, but to 2 tables
        self.assertEqual(blk._count, 2)
        self.assertEqual(put_func.call_count, 5)

        blk.stop()

    def test_no_save_invalid(self, put_func, count_func, create_func,
                             connect_func):
        """ Make sure we only save valid signals """
        blk = SaveCounterDynamoDB()
        self.configure_block(blk, {
            'log_level': 'DEBUG',
            'hash_key': 'hash'
        })
        blk.start()

        blk.process_signals([
            Signal({'hash': 'hash val'}),
            Signal({'nohash': 'nohash val'})])

        # One table call, one real put call (one should have issued warning)
        self.assertEqual(blk._count, 1)
        self.assertEqual(put_func.call_count, 1)

        blk.stop()

    def test_no_save_bad_table(self, put_func, count_func, create_func,
                               connect_func):
        """ Make sure we only save signals that can evaluate table name """
        blk = SaveCounterDynamoDB()
        self.configure_block(blk, {
            'log_level': 'DEBUG',
            'hash_key': 'hash',
            # we will cause table errors by trying to access a character
            # at a string index that doesn't exist
            'table': '{{$table[10]}}'
        })
        blk.start()

        blk.process_signals([
            Signal({'hash': 'hash val', 'table': 'goodtablename'}),
            # bad is bad because it doesn't have a 10th character
            Signal({'hash': 'hash val', 'table': 'bad'})])

        # One table call, one real put call (one should have errored)
        self.assertEqual(blk._count, 1)
        self.assertEqual(put_func.call_count, 1)

        blk.stop()

    def test_table_lock(self, put_func, count_func, create_func, connect_func):
        """ Make sure that if a table is creating it locks """
        # We should return the error that the table is not found.
        # We should only see this error returned once though, subsequent calls
        # should use the cached version of the table.
        count_func.side_effect = [JSONResponseError(
            400,
            "{'message': 'Requested resource not found: Table: T notfound', "
            "'__type': 'com.amazonaws.dynamodb.v20120810"
            "#ResourceNotFoundException'}")]
        blk = SaveCounterDynamoDB()
        self.configure_block(blk, {
            'log_level': 'DEBUG',
            'hash_key': 'hash'
        })
        # Simulate a table that is creating for a while
        blk._get_table_status = MagicMock(
            side_effect=['CREATING', 'CREATING', 'ACTIVE'])

        # Send two threads to process signals at once
        spawn(blk.process_signals, [Signal({'hash': 'value1'})])
        spawn(blk.process_signals, [Signal({'hash': 'value2'})])

        # We shouldn't have any save calls until the table creates.
        # That takes 1.5 seconds, so let's see what we have after some of that.
        sleep(0.7)
        self.assertEqual(blk._count, 0)

        # Give the table time to create...
        sleep(1)

        # Make sure the table create function only gets called once.  This
        # should happen due to the presence of the lock around _get_table
        self.assertEqual(create_func.call_count, 1)

        # Ok, it's created, we should see both signals get saved
        self.assertEqual(blk._count, 2)

    def test_create(self, put_func, count_func, create_func, connect_func):
        """ Make sure we make tables with the proper configs """

        # Default config - should only have hash config
        blk_default = DynamoDBInsert()
        self.configure_block(blk_default, {})
        blk_default._create_table('fake_table')
        call_args = create_func.call_args
        """
        call_args[0] = ('fake_table',)
        call_args[1] = {
            'schema':
                [<boto.dynamodb2.fields.HashKey object at 0x000000000>],
            'connection':
                <MagicMock name='connect_to_region()' id='0000000000'>
        }
        """
        self.assertEqual(call_args[0][0], 'fake_table')
        self.assertEqual(call_args[1]['schema'][0].name, '_id')
        create_func.reset_mock()

        # Range config - should have both configs
        blk_range = DynamoDBInsert()
        self.configure_block(blk_range, {
            'range_key': 'range_attr'
        })
        blk_range._create_table('fake_table')
        call_args = create_func.call_args
        """
        call_args[0] = ('fake_table',)
        call_args[1] = {
            'schema':
                [<boto.dynamodb2.fields.HashKey object at 0x000000000>,
                 <boto.dynamodb2.fields.RangeKey object at 0x000000000>],
            'connection':
                <MagicMock name='connect_to_region()' id='0000000000'>
        }
        """
        self.assertEqual(call_args[0][0], 'fake_table')
        self.assertEqual(call_args[1]['schema'][0].name, '_id')
        self.assertEqual(call_args[1]['schema'][1].name, 'range_attr')
        create_func.reset_mock()

        # Both config - should have both configs
        blk_both = DynamoDBInsert()
        self.configure_block(blk_both, {
            'hash_key': 'hash_attr',
            'range_key': 'range_attr'
        })
        blk_both._create_table('fake_table')
        call_args = create_func.call_args
        """
        call_args[0] = ('fake_table',)
        call_args[1] = {
            'schema':
                [<boto.dynamodb2.fields.HashKey object at 0x000000000>,
                 <boto.dynamodb2.fields.RangeKey object at 0x000000000>],
            'connection':
                <MagicMock name='connect_to_region()' id='0000000000'>
        }
        """
        self.assertEqual(call_args[0][0], 'fake_table')
        self.assertEqual(call_args[1]['schema'][0].name, 'hash_attr')
        self.assertEqual(call_args[1]['schema'][1].name, 'range_attr')
        create_func.reset_mock()
