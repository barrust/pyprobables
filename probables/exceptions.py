''' PyProbables Exceptions '''
from __future__ import (unicode_literals, absolute_import, print_function)


class ProbablesBaseException(Exception):
    ''' Base ProbablesBaseException

        Args:
            message (str): The error message to be reported '''
    def __init__(self, message):
        self.message = message
        super(ProbablesBaseException, self).__init__(self.message)

    def __unicode__(self):
        return self.message

    def __str__(self):
        return self.__unicode__()


class InitializationError(ProbablesBaseException):
    ''' Initialization Exception

        Args:
            message (str): The initialization error messge '''
    def __init__(self, message):
        self.message = message
        super(InitializationError, self).__init__(self.message)


class NotSupportedError(ProbablesBaseException):
    ''' Not Supported Functionality Exception

        Args:
            message (str): The error message to be reported '''
    def __init__(self, message):
        self.message = message
        super(NotSupportedError, self).__init__(self.message)


class CuckooFilterFullError(ProbablesBaseException):
    ''' Cuckoo Filter Full Exception

        Args:
            message (str): The error message to be reported '''
    def __init__(self, message):
        self.message = message
        super(CuckooFilterFullError, self).__init__(self.message)
