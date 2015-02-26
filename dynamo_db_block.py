import re
from enum import Enum
from collections import defaultdict
from nio.common.discovery import Discoverable, DiscoverableType
from nio.common.block.base import Block
from nio.metadata.properties import ExpressionProperty, PropertyHolder, \
    ObjectProperty, StringProperty, SelectProperty

from boto.exception import JSONResponseError
from boto.dynamodb2 import connect_to_region
from boto.dynamodb2.table import Table
from boto.dynamodb2.fields import HashKey, RangeKey


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
class DynamoDB(Block):

    table = ExpressionProperty(title='Table', default='signals')
    region = SelectProperty(
        AWSRegion, default=AWSRegion.us_east_1, title="AWS Region")
    creds = ObjectProperty(AWSCreds, title="AWS Credentials")
    hash_key = StringProperty(title="Hash Key", default="_id")
    range_key = StringProperty(title="Range Key", default="")

    def __init__(self):
        super().__init__()
        self._conn = None
        self._table_cache = {}

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
        # Split the signals up into table groups for batch writing
        # batch_groups is a dictionary where the key is a table name, and the
        # value is a list of signals that should be saved to that table name
        batch_groups = defaultdict(list)
        for sig in signals:
            batch_groups[self.table(sig)].append(sig)
        self._logger.debug("Processing {} signals in {} batch groups".format(
            len(signals), len(batch_groups)))

        # Go through each table in batch groups and batch write all of the
        # signals to the table
        for table_name, sigs in batch_groups.items():
            self._logger.debug("Saving {} signals to {}".format(
                len(sigs), table_name))
            try:
                # Get the cached table reference if we have it
                table = self._get_table(table_name)
                self._save_signals_to_table(table, sigs)
            except Exception as e:
                self._logger.error("Could not batch write to table {} : {} {}"
                                   .format(table_name, type(e), str(e)))

    def _get_table(self, table_name):
        """ Get a DynamoDB table reference.

        If we have looked up/created this table before, use the cached
        reference. If not, check to make sure the table exists. If it does
        not exist, create it and return that reference.
        """
        if table_name in self._table_cache:
            return self._table_cache[table_name]

        table = Table(table_name, connection=self._conn)

        try:
            num_items = table.count()
            self._logger.debug("Table {} found - contains {} items".format(
                table_name, num_items))
        except JSONResponseError as jre:
            if 'ResourceNotFoundException' in str(jre):
                # If we get a resource not found exception, the table must not
                # exist, so let's create it
                self._logger.info("Table {} not found - creating it".format(
                    table_name))
                table = self._create_table(table_name)
            else:
                # We got some other type of exception, raise it since that
                # wasn't expected
                raise
        except Exception as e:
            self._logger.error("Unable to determine table reference: {} {}"
                               .format(type(e), str(e)))
            return

        # Cache this reference to the table for later use
        self._table_cache[table_name] = table
        return table

    def _create_table(self, table_name):
        """ Create a table and return the table reference """
        hash_key = self.hash_key
        range_key = self.range_key

        if range_key:
            self._logger.info(
                "Creating table with hash key: {}, range key: {}".format(
                    hash_key, range_key))
            return Table.create(
                table_name,
                schema=[HashKey(hash_key), RangeKey(range_key)],
                connection=self._conn)
        else:
            self._logger.info(
                "Creating table with hash key: {}".format(hash_key))
            return Table.create(table_name, schema=[HashKey(hash_key)])

    def _save_signals_to_table(self, table, signals):
        """ Save a list of signals to a table reference """
        with table.batch_write() as batch:
            for sig in signals:
                self._save_signal(batch, sig)

    def _save_signal(self, table, signal):
        """ Save a signal to a DynamoDB table """
        try:
            if self._is_valid_signal(signal):
                table.put_item(data=signal.to_dict())
            else:
                self._logger.warning(
                    "Not saving an invalid signal - must contain hash and "
                    "range keys if specified - {}".format(signal))
        except Exception as e:
            self._logger.error("Unable to save signal: {} {}"
                               .format(type(e), str(e)))

    def _is_valid_signal(self, signal):
        """ Return true if this signal is valid and can be saved """
        # A signal has a valid hash if it contains the hash field
        hash_valid = hasattr(signal, self.hash_key)
        # A signal has a valid range if it contains the range field or no
        # range field was specified
        range_valid = not self.range_key or hasattr(signal, self.range_key)

        return hash_valid and range_valid
