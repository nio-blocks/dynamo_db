from unittest.mock import MagicMock, patch
from nio.common.signal.base import Signal
from nio.util.support.block_test_case import NIOBlockTestCase
from ..dynamo_db_query_block import DynamoDBQuery
from ..dynamo_db_base_block import DynamoDBBase


@patch(DynamoDBBase.__module__ + '.connect_to_region')
@patch(DynamoDBBase.__module__ + '.Table.count')
@patch(DynamoDBBase.__module__ + '.Table.query_2')
class TestDynamoDBQuery(NIOBlockTestCase):

    def test_build_query_dict_default(self, q_func, count_func, connect_func):
        blk = DynamoDBQuery()
        self.configure_block(blk, {})
        query_dict = blk._build_query_dict(Signal({'id': 1}))
        self.assertDictEqual(query_dict, {
            'id__eq': 1
        })

    def test_build_query_dict_multiple(self, q_func, count_func, connect_func):
        blk = DynamoDBQuery()
        self.configure_block(blk, {
            'query_filters': [
                {'key': 'str__eq', 'value': '1'},
                {'key': 'dup__eq', 'value': 'first'},
                {'key': 'dup__eq', 'value': 'duplicate'},
                {'key': 'int__eq', 'value': '{{ 1 }}' },
                {'key': 'exp__eq', 'value': "{{ $id }}"}
            ]
        })
        query_dict = blk._build_query_dict(Signal({'id': 'signal'}))
        self.assertDictEqual(query_dict, {
            'str__eq': '1',
            'dup__eq': 'duplicate',
            'int__eq': 1,
            'exp__eq': 'signal'
        })

    def test_build_query_dict_limit(self, q_func, count_func, connect_func):
        blk = DynamoDBQuery()
        self.configure_block(blk, {'limit': 1})
        query_dict = blk._build_query_dict(Signal({'id': 1}))
        self.assertDictEqual(query_dict, {
            'id__eq': 1,
            'limit': 1
        })

    def test_build_query_dict_reverse(self, q_func, count_func, connect_func):
        blk = DynamoDBQuery()
        self.configure_block(blk, {'reverse': True})
        query_dict = blk._build_query_dict(Signal({'id': 1}))
        self.assertDictEqual(query_dict, {
            'id__eq': 1,
            'reverse': True
        })

    def test_build_query_dict_fail(self, q_func, count_func, connect_func):
        blk = DynamoDBQuery()
        self.configure_block(blk, {
            'query_filters': [
                {'key': 'good__eq', 'value': 'good'},
                {'key': 'bad__eq', 'value': "{{ $id }}"},
                {'key': 'moregood__eq', 'value': 'moregood'}
            ]
        })
        self.assertRaises(Exception, blk._build_query_dict, Signal())

    def test_query_table(self, q_func, count_func, connect_func):
        blk = DynamoDBQuery()
        self.configure_block(blk, {
            'query_filters': [
                {'key': 'id__eq', 'value': '{{ $id }}'},
                {'key': 'str__beginswith', 'value': 'begin'}
            ]
        })
        # have the query return two results
        q_func.return_value = [{}, {}]
        blk.process_signals([Signal({'id': 1})])
        q_func.assert_called_once_with(id__eq=1,
                                      str__beginswith='begin')
        self.assert_num_signals_notified(2)

    def test_query_multiple(self, q_func, count_func, connect_func):
        blk = DynamoDBQuery()
        self.configure_block(blk, {})
        # have each query return one result
        q_func.return_value = [{}]
        blk.process_signals([Signal({'id': 1}),
                             Signal(),
                             Signal({'id': 1})])
        # one of the three queries falied so two signals are notified
        self.assert_num_signals_notified(2)
