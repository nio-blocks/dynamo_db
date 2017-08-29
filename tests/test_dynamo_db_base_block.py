from unittest.mock import patch

from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase
from nio.util.discovery import not_discoverable

from ..dynamo_db_base_block import DynamoDBBase


@not_discoverable
class PassDynamoDB(DynamoDBBase):

    def execute_signals_query(self, tables, signals):
        return signals


@not_discoverable
class ExceptionDynamoDB(DynamoDBBase):

    def execute_signals_query(self, tables, signals):
        raise Exception


@patch(DynamoDBBase.__module__ + '.connect_to_region')
@patch(DynamoDBBase.__module__ + '.Table.create')
@patch(DynamoDBBase.__module__ + '.Table.count')
@patch('boto.dynamodb2.table.BatchTable.put_item')
class TestDynamoDBBase(NIOBlockTestCase):

    def test_notify_sigs(self, put_func, count_func, create_func,
                         connect_func):
        """ Make sure a basic use of the base block passes through signals """
        blk = PassDynamoDB()
        self.configure_block(blk, {
            'log_level': 'DEBUG',
            'table': '{{ $_id }}'
        })
        blk.start()

        blk.process_signals([Signal({'_id': i}) for i in range(5)])

        self.assert_num_signals_notified(5)

        blk.stop()

    def test_exception(self, put_func, count_func, create_func, connect_func):
        """ Make sure exceptions are handled for blocks that raise them """
        blk = ExceptionDynamoDB()
        self.configure_block(blk, {
            'log_level': 'DEBUG'
        })
        blk.start()

        blk.process_signals([Signal({'_id': ''}) for i in range(5)])

        self.assert_num_signals_notified(0)

        blk.stop()
