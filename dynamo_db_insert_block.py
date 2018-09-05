from time import sleep

from boto.dynamodb2.fields import HashKey, RangeKey
from boto.dynamodb2.table import Table

from nio import TerminatorBlock
from nio.properties import StringProperty, VersionProperty
from nio.util.discovery import discoverable

from .dynamo_db_base_block import DynamoDBBase


@discoverable
class DynamoDBInsert(DynamoDBBase, TerminatorBlock):

    hash_key = StringProperty(title="Hash Key", default="_id")
    range_key = StringProperty(title="Range Key", default="")
    version = VersionProperty("1.0.1")

    def execute_signals_query(self, table, signals):
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
                self.logger.warning(
                    "Not saving an invalid signal - must contain hash and "
                    "range keys if specified - {}".format(signal))
        except:
            self.logger.exception("Unable to save signal")

    def _is_valid_signal(self, signal):
        """ Return true if this signal is valid and can be saved """
        # A signal has a valid hash if it contains the hash field
        hash_valid = hasattr(signal, self.hash_key())
        # A signal has a valid range if it contains the range field or no
        # range field was specified
        range_valid = not self.range_key() or hasattr(signal, self.range_key())

        return hash_valid and range_valid

    def _create_table(self, table_name):
        """ Create a table and return the table reference """
        hash_key = self.hash_key()
        range_key = self.range_key()

        if range_key:
            self.logger.info(
                "Creating table with hash key: {}, range key: {}".format(
                    hash_key, range_key))
            schema = [HashKey(hash_key), RangeKey(range_key)]
        else:
            self.logger.info(
                "Creating table with hash key: {}".format(hash_key))
            schema = [HashKey(hash_key)]

        new_table = Table.create(
            table_name,
            schema=schema,
            connection=self._conn)

        # Wait for our new table to be created
        status = 'CREATING'
        while status == 'CREATING':
            sleep(0.5)
            status = self._get_table_status(new_table)
            self.logger.debug("Table status is {}".format(status))

        return new_table

    def _get_table_status(self, table):
        """ Get a table's status from AWS """
        return table.describe().get('Table', {}).get('TableStatus')
