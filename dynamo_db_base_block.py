import re
from enum import Enum
from collections import defaultdict
from time import sleep
from nio.common.discovery import Discoverable, DiscoverableType
from nio.common.block.base import Block
from nio.metadata.properties import ExpressionProperty, PropertyHolder, \
    ObjectProperty, StringProperty, SelectProperty
from nio.modules.threading import Lock

from boto.exception import JSONResponseError
from boto.dynamodb2 import connect_to_region
from boto.dynamodb2.table import Table


class AWSRegion(Enum):
    us_east_1 = 0
    us_west_2 = 1
    eu_west_1 = 2


class AWSCreds(PropertyHolder):
    access_key = StringProperty(title="Access Key",
                                default="[[AMAZON_ACCESS_KEY_ID]]")
    access_secret = StringProperty(title="Access Secret",
                                   default="[[AMAZON_SECRET_ACCESS_KEY]]")


@Discoverable(DiscoverableType.block)
class DynamoDBBase(Block):

    table = ExpressionProperty(title='Table', default='signals')
    region = SelectProperty(
        AWSRegion, default=AWSRegion.us_east_1, title="AWS Region")
    creds = ObjectProperty(AWSCreds, title="AWS Credentials")

    def __init__(self):
        super().__init__()
        self._conn = None
        self._table_cache = {}
        self._table_locks = defaultdict(Lock)

    def configure(self, context):
        super().configure(context)
        region_name = re.sub('_', '-', self.region.name)
        self._logger.debug("Connecting to region {}...".format(region_name))
        self._conn = connect_to_region(
            region_name,
            aws_access_key_id=self.creds.access_key,
            aws_secret_access_key=self.creds.access_secret)
        self._logger.debug("Connection complete")

    def process_signals(self, signals, input_id='default'):
        output = []
        batch_groups = self._get_batch_groups(signals)
        for table_name, sigs in batch_groups.items():
            self._logger.debug("Operating on {} signals to table {}".format(
                len(sigs), table_name))
            try:
                output.extend(self._process_table_signals(table_name, sigs))
            except:
                self._logger.exception("Could not batch operate on table {}"
                                       .format(table_name))
        if output:
            self.notify_signals(output)

    def execute_signals_query(self, table, signals):
        """ Run this block's query on the provided table.

        This should be overriden in the child blocks. It will be passed
        a valid dynamo table against which it can query.

        If the block wishes, it may return a list of signals that will be
        notified.

        Params:
            table (boto.dynamodb2.table.Table): A valid table
            signals (list(Signal)): The signals which triggered the query

        Returns:
            signals (list): Any signals to notify
        """
        raise NotImplementedError()

    def _get_batch_groups(self, signals):
        """ Split the signals up into table groups for batch writing.

        batch_groups is a dictionary where the key is a table name, and the
        value is a list of signals that should be go to that table name

        Returns:
            batch_groups (dict): Dict of key=table_name and value=list(Signals)
        """
        batch_groups = defaultdict(list)
        for sig in signals:
            try:
                table_name = self.table(sig)
                batch_groups[table_name].append(sig)
            except:
                self._logger.exception("Unable to add signal to table list")
        self._logger.debug("Processing {} signals in {} batch groups".format(
            len(signals), len(batch_groups)))
        return batch_groups

    def _process_table_signals(self, table_name, signals):
        """ Go through each table in batch groups and batch operate all of the
        signals to the table

        Returns:
            signals(list): Any signals to notify or empty list

        Raises:
            Exception: When table does not exist and `create` is False
                or when custom block implementation of execute_signals_query
                raises Exception.
        """
        output = []
        # Lock around each table - in case it is creating still
        self._logger.debug(
            "Waiting for table lock on {}".format(table_name))
        with self._table_locks[table_name]:
            self._logger.debug(
                "Table lock acquired for {}".format(table_name))
            table = self._get_table(table_name)
            out_sigs = self.execute_signals_query(table, signals)
            if isinstance(out_sigs, list):
                output.extend(out_sigs)
        return output

    def _get_table(self, table_name, create=True):
        """ Get a DynamoDB table reference based on a table name.

        If we have looked up/created this table before, use the cached
        reference. If not, check to make sure the table exists. If it does
        not exist, create it and return that reference.

        Note that if this function does not find the table, it will create it
        and this creation operation can block for some time (typically ~10s).
        It will only return the table reference once the table is active and
        ready to be stored to or read from.

        As a result, it probably makes sense to call this method in a lock
        for the specific table. Otherwise, simultaneous calls to _get_table
        could result in multiple table creations.

        Args:
            create (bool): If table does not exist, create it.

        Returns:
            table: A boto table reference

        Raises:
            Exception: When table does not exist and `create` is False.
        """
        if table_name in self._table_cache:
            return self._table_cache[table_name]

        table = Table(table_name, connection=self._conn)

        try:
            num_items = table.count()
            self._logger.debug("Table {} found - contains {} items".format(
                table_name, num_items))
        except JSONResponseError as jre:
            if create and 'ResourceNotFoundException' in str(jre):
                # If we get a resource not found exception, the table must not
                # exist, so let's create it
                self._logger.info("Table {} not found - creating it".format(
                    table_name))
                table = self._create_table(table_name)
                self._logger.debug("Table created: {}".format(table))
            else:
                # We got some other type of exception, raise it since that
                # wasn't expected
                raise
        except:
            self._logger.exception("Unable to determine table reference")
            raise

        # Cache this reference to the table for later use
        self._table_cache[table_name] = table
        return table

    def _create_table(self, table_name):
        """ Create a table and return the table reference """
        raise NotImplementedError()
