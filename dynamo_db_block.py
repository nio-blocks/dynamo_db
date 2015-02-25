from nio.common.discovery import Discoverable, DiscoverableType
from nio.common.block.base import Block


@Discoverable(DiscoverableType.block)
class DynamoDB(Block):
    pass
