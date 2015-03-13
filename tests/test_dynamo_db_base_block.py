from unittest.mock import MagicMock, patch
from nio.common.signal.base import Signal
from nio.util.support.block_test_case import NIOBlockTestCase
from ..dynamo_db_base_block import DynamoDBBase


class PassDynamoDB(DynamoDBBase):

    def execute_signals_query(self, tables, signals):
        return signals


@patch(DynamoDBBase.__module__ + '.connect_to_region')
class TestDynamoDBBase(NIOBlockTestCase):

    @patch('boto.dynamodb2.table.BatchTable.put_item')
    @patch(DynamoDBBase.__module__ + '.Table.count')
    def test_save_batch(self, count_func, put_func, connect_func):
        """ Make sure we save each table in a batch fashion """
        blk = PassDynamoDB()
        self.configure_block(blk, {
            'log_level': 'DEBUG'
        })
        blk.start()

        blk.process_signals([Signal({'_id': ''}) for i in range(5)])

        self.assert_num_signals_notified(5)

        blk.stop()
