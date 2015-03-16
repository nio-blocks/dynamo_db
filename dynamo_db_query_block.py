from enum import Enum
from nio.common.discovery import Discoverable, DiscoverableType
from nio.common.block.base import Block
from nio.common.signal.base import Signal
from nio.metadata.properties import ExpressionProperty, PropertyHolder, \
    ObjectProperty, StringProperty, SelectProperty, ListProperty

from .dynamo_db_base_block import DynamoDBBase


class QueryFilter(PropertyHolder):

    key = ExpressionProperty(title='Filter Key',
                             default='id__eq',
                             attr_default=Exception)
    value = ExpressionProperty(title='Filter Value',
                               default='{{ $id }}',
                               attr_default=Exception)

@Discoverable(DiscoverableType.block)
class DynamoDBQuery(DynamoDBBase):

    query_filters = ListProperty(QueryFilter,
                                 title='Query Filters',
                                 default=[QueryFilter()])

    def execute_signals_query(self, table, signals):
        """ Overriden from base class

        Params:
            table (boto.dynamodb2.table.Table): A valid table
            signals (list(Signal)): The signals which triggered the query

        Returns:
            signals (list): Any signals to notify
        """
        output = []
        for signal in signals:
            try:
                output.extend(self._execute_signal_query(table, signal))
            except:
                self._logger.exception('Failed to execute query')
        return output

    def _execute_signal_query(self, table, signal):
        """ Execute a query against the table

        This method takes in one signal and returns one signal when query
        is successful. Raises an exception if the query is not succesful.

        Params:
            table (boto.dynamodb2.table.Table): A valid table
            signals (list(Signal)): The signals which triggered the query

        Returns:
            signals (list): Any signals to notify

        Raises:
            Exception: A failed query for any reason will raise an exception
        """
        output = []
        query_dict = self._build_query_dict(signal)
        self._logger.debug(
            'Querying table {} with: {}'.format(table, query_dict))
        results = table.query_2(**query_dict)
        for item in results:
            output.append(Signal(dict(item)))
        return output

    def _build_query_dict(self, signal):
        """ Builds a query dictionary from query_filter property

        Params:
            signal (Signal): The signal which triggered the query

        Returns:
            query_dict (dict): Example {'key__eq': 'value'}

        Raises:
            Exception: When query filter key/value expressions fail
        """
        output = []
        query_dict = {}
        for query_filter in self.query_filters:
            # evaluate query filter expression
            try:
                key = query_filter.key(signal)
                value = query_filter.value(signal)
                query_dict[key] = value
            except:
                self._logger.debug('Failed to evaluate query filter key/value')
                raise
        return query_dict
