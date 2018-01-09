from nio.signal.base import Signal
from nio.util.discovery import discoverable
from nio.properties import (Property, PropertyHolder, ListProperty,
                            BoolProperty, VersionProperty)

from .dynamo_db_base_block import DynamoDBBase


class Limitable():
    """ A dynamo block mixin that allows you to limit results """

    limit = Property(title='Limit', default='')

    def _build_query_dict(self, signal=None):
        existing_args = super()._build_query_dict(signal)
        limit = self.limit(signal)
        # Don't send limit if they it is an empty string (default)
        if limit:
            existing_args['limit'] = int(limit)
        return existing_args


class Reversable():
    """ A dynamo block mixin that allows you to reverse results """

    reverse = BoolProperty(title='Reverse', default=False)

    def _build_query_dict(self, signal=None):
        existing_args = super()._build_query_dict(signal)
        if self.reverse():
            existing_args['reverse'] = self.reverse()
        return existing_args


class QueryFilter(PropertyHolder):

    key = Property(title='Filter Key',
                   default='id__eq',
                   attr_default=Exception)
    value = Property(title='Filter Value',
                     default='{{ $id }}',
                     attr_default=Exception)


@discoverable
class DynamoDBQuery(Limitable, Reversable, DynamoDBBase):

    query_filters = ListProperty(QueryFilter,
                                 title='Query Filters',
                                 default=[QueryFilter()])
    version = VersionProperty("1.0.1")

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
                self.logger.exception('Failed to execute query')
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
        self.logger.debug(
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
        query_dict = super()._build_query_dict(signal)
        for query_filter in self.query_filters():
            # evaluate query filter expression
            key = query_filter.key(signal)
            value = query_filter.value(signal)
            query_dict[key] = value
        return query_dict
