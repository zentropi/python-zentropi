from uuid import uuid4
from zentropi.log import logging_configure, logging_init, logger


def test_logging_configure():
    logging_configure(file_path='/tmp/zentest.log')
    logging_init('test')
    uuid = uuid4().hex    
    logger.warning(f'Here is one {uuid}')
    with open('/tmp/zentest.log') as infile:
        assert uuid in infile.read()