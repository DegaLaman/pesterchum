from email import utils
_timezones = {'GMT':000} # Add in rest of timezones
def quote(string):
    return utils.quote(string)
def unquote(string):
    return utils.unquote(string)
def parseaddr(address):
    address = utils.parseaddr(address)
    if address == ('',''):
        return (None,None)
    return a
def dump_address_pair(pair):
    if pair == (None,None):
        pair = ('','')
    return utils.formataddr(pair)
def parsedate_tz(date):
    return utils.parsedate_tz(date)
def parsedate(date):
    return utils.parsedate(date)
def mktime_tz(tup):
    return utils.mktime_tz(tup)
"""
class Message:
    def __init__(file,seekable=None):
        self.headers = []
        self.fp = file
        self.unixfrom = ''
        
class AddressList:
    def __init__(self, field):
        pass
"""
