import socket
import subprocess
from quirks.iterable import isiterable,ifilter,imap,chain , ensure_iterable
from quirks.functional import maybe

import re
import datetime
from os import path

import logging
from whois.parser import PywhoisError
from whois import WhoisEntry, NICClient

logger = logging.getLogger(__name__)



def extract_domain(url):
    """Extract the domain from the given URL

    >>> extract_domain('http://www.google.com.au/tos.html')
    'google.com.au'
    >>> extract_domain('http://blog.webscraping.com')
    'webscraping.com'
    >>> extract_domain('69.59.196.211')
    'stackoverflow.com'
    """
    if re.match(r'\d+.\d+.\d+.\d+', url):
        # this is an IP address
        return socket.gethostbyaddr(url)[0]

    suffixes = 'ac', 'ad', 'ae', 'aero', 'af', 'ag', 'ai', 'al', 'am', 'an', 'ao', 'aq', 'ar', 'arpa', 'as', 'asia', 'at', 'au', 'aw', 'ax', 'az', 'ba', 'bb', 'bd', 'be', 'bf', 'bg', 'bh', 'bi', 'biz', 'bj', 'bm', 'bn', 'bo', 'br', 'bs', 'bt', 'bv', 'bw', 'by', 'bz', 'ca', 'cat', 'cc', 'cd', 'cf', 'cg', 'ch', 'ci', 'ck', 'cl', 'cm', 'cn', 'co', 'com', 'coop', 'cr', 'cu', 'cv', 'cx', 'cy', 'cz', 'de', 'dj', 'dk', 'dm', 'do', 'dz', 'ec', 'edu', 'ee', 'eg', 'er', 'es', 'et', 'eu', 'fi', 'fj', 'fk', 'fm', 'fo', 'fr', 'ga', 'gb', 'gd', 'ge', 'gf', 'gg', 'gh', 'gi', 'gl', 'gm', 'gn', 'gov', 'gp', 'gq', 'gr', 'gs', 'gt', 'gu', 'gw', 'gy', 'hk', 'hm', 'hn', 'hr', 'ht', 'hu', 'id', 'ie', 'il', 'im', 'in', 'info', 'int', 'io', 'iq', 'ir', 'is', 'it', 'je', 'jm', 'jo', 'jobs', 'jp', 'ke', 'kg', 'kh', 'ki', 'km', 'kn', 'kp', 'kr', 'kw', 'ky', 'kz', 'la', 'lb', 'lc', 'li', 'lk', 'lr', 'ls', 'lt', 'lu', 'lv', 'ly', 'ma', 'mc', 'md', 'me', 'mg', 'mh', 'mil', 'mk', 'ml', 'mm', 'mn', 'mo', 'mobi', 'mp', 'mq', 'mr', 'ms', 'mt', 'mu', 'mv', 'mw', 'mx', 'my', 'mz', 'na', 'name', 'nc', 'ne', 'net', 'nf', 'ng', 'ni', 'nl', 'no', 'np', 'nr', 'nu', 'nz', 'om', 'org', 'pa', 'pe', 'pf', 'pg', 'ph', 'pk', 'pl', 'pm', 'pn', 'pr', 'pro', 'ps', 'pt', 'pw', 'py', 'qa', 're', 'ro', 'rs', 'ru', 'rw', 'sa', 'sb', 'sc', 'sd', 'se', 'sg', 'sh', 'si', 'sj', 'sk', 'sl', 'sm', 'sn', 'so', 'sr', 'st', 'su', 'sv', 'sy', 'sz', 'tc', 'td', 'tel', 'tf', 'tg', 'th', 'tj', 'tk', 'tl', 'tm', 'tn', 'to', 'tp', 'tr', 'tt', 'tv', 'tw', 'tz', 'ua', 'ug', 'uk', 'us', 'uy', 'uz', 'va', 'vc', 've', 'vg', 'vi', 'vn', 'vu', 'wf', 'ws', 'xn', 'xxx', 'ye', 'yt', 'za', 'zm', 'zw'
    url = re.sub('^.*://', '', url).split('/')[0].lower()
    domain = []
    for section in url.split('.'):
        if section in suffixes:
            domain.append(section)
        else:
            domain = [section]
    return '.'.join(domain)

def whois(url):
    # clean domain to expose netloc
    domain = extract_domain(url)
    try:
        # try native whois command first
        r = subprocess.Popen(['whois', domain], stdout=subprocess.PIPE)
        text = r.stdout.read()
    except OSError:
        # try experimental client
        nic_client = NICClient()
        text = nic_client.whois_lookup(None, domain, 0)
    return Entry.load(domain, text)

class Entry(WhoisEntry):
    def __init__(self, domain, text, regex=None):
        super(Entry, self).__init__(domain, text, regex or  {
            'domain_name':      'Domain Name:\s?(.+)',
            'registrar':        'Registrar:\s?(.+)',
            'whois_server':     'Whois Server:\s?(.+)',
            'referral_url':     'Referral URL:\s?(.+)', # http url of whois_server
            'updated_date':     'Updated Date:\s?(.+)',
            'creation_date':    'Creation Date:\s?(.+)',
            'expiration_date':  'Expiration Date:\s?(.+)',
            'name_servers':     'Name Server:\s?(.+)', # list of name servers
            'status':           'Status:\s?(.+)', # list of statuses
            'emails':           '[\w.-]+@[\w.-]+\.[\w]{2,4}', # list of email addresses
            'registrant_name':                'Registrant\s+Name:\s*(.+)\n',
            'registrant_id':                  'Registrant\s+ID:\s*(.+)\n',
            'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
            'registrant_country_code':      'Registrant\s+Country\s+Code:\s*(.+)\n',
        })

    def __getattr__(self, attr):
        """The first time an attribute is called it will be calculated here.
        The attribute is then set to be accessed directly by subsequent calls.
        """
        whois_regex = self._regex.get(attr)
        if whois_regex:
            values = []
            for value in re.findall(whois_regex, self.text, re.IGNORECASE):
                if isinstance(value, basestring):
                    # try casting to date format
                    value = self.cast_date(value.strip())
                values.append(value)
            #if len(values) == 1:
            #    values = values[0]
            setattr(self, attr, values)
            return getattr(self, attr)
        else:
            raise KeyError('Unknown attribute: %s' % attr)

    @staticmethod
    def cast_date(s):
        """Convert any date string found in WHOIS to a datetime object.
        """
        known_formats = [
            '%Y.%m.%d %H:%M:%S',                 # 2000.01.02 17:46:33
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.000Z',
            ]

        for known_format in known_formats:
            try:
                return datetime.datetime.strptime(s.strip(), known_format)
            except ValueError as e:
                pass
        from whois.parser import cast_date
        return cast_date(s)

    @staticmethod
    def load(domain, text):
        if text.strip() == 'No whois server is known for this kind of object.':
            raise PywhoisError(text)

        if domain.endswith('.com'):
            return ComEntry(domain, text)
        elif domain.endswith('.net'):
            return NetEntry(domain, text)
        elif domain.endswith('.org'):
            return OrgEntry(domain, text)
        elif domain.endswith('.name'):
            return NameEntry(domain, text)
        elif domain.endswith('.me'):
            pass#return WhoisMe(domain, text)
        elif domain.endswith('.ru'):
            pass#return WhoisRu(domain, text)
        elif domain.endswith('.us'):
            pass#return WhoisUs(domain, text)
        elif domain.endswith('.uk'):
            return UkEntry(domain, text)
        elif domain.endswith('.fr'):
            return FrEntry(domain, text)
        elif domain.endswith('.fi'):
            pass#return WhoisFi(domain, text)
        elif domain.endswith('.jp'):
            pass#return WhoisJp(domain, text)
        elif domain.endswith('.pl'):
            return PlEntry(domain, text)
        elif domain.endswith('.es'):
            return EsEntry(domain, text)
        elif domain.endswith('.tl'):
            return TlEntry(domain, text)
        elif domain.endswith('.me'):
            return MeEntry(domain, text)
        elif domain.endswith('.biz'):
            return BizEntry(domain, text)
        elif domain.endswith('.sk'):
            return SkEntry(domain, text)
        elif domain.endswith('.sg'):
            return SgEntry(domain, text)
        elif domain.endswith('.eu'):
            return EuEntry(domain, text)
        elif domain.endswith('.tl'):
            return TlEntry(domain, text)
        elif domain.endswith('.xxx'):
            return XXXEntry(domain, text)
        elif domain.endswith('.nl'):
            return NlEntry(domain, text)
        elif domain.endswith('.info'):
            return InfoEntry(domain, text)

        else:
            return Entry(domain, text)

class PlEntry(Entry):
    def __init__(self, domain, text):
        super(PlEntry, self).__init__(domain, text, regex={
            'registrant_name':                'Registrant:\n\s*(.+)',   # not available
            'registrant_id':                  'Registrant:\n\s*(.+)',   # not available
            'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
            'registrant_country_code':      'Registrant\s+Country\s+Code:\s*(.+)\n',
            'creation_date':                  'created:\s*(.+)\n',
            })


class InfoEntry(Entry):
    def __init__(self, domain, text):
        super(InfoEntry, self).__init__(domain, text, regex={
            'registrant_name':                'Registrant:\n\s*(.+)',   # not available
            'registrant_id':                  'Registrant:\n\s*(.+)',   # not available
            'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
            'registrant_country_code':      'Registrant\s+Country:\s*(.+)\n',
            'creation_date':                  'created:\s*(.+)\n',
            })

class XXXEntry(Entry):
    def __init__(self, domain, text):
        if text.strip() == 'NOT FOUND':
            raise PywhoisError(text)
        else:
            super(XXXEntry, self).__init__(domain, text, regex= {
                'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
                'registrant_name':              'Name:\s*(.+)\n',
                'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
                'registrant_country_code':      'Registrant\s+Country:\s*(.+)\n',
                'creation_date':                'Creation\s+Date:\s*(.+)\n',
                })

class EuEntry(Entry):
    def __init__(self, domain, text):
        if text.strip() == 'NOT DISCLOSED!':
            raise PywhoisError(text)
        else:
            super(EuEntry, self).__init__(domain, text, regex={
                'registrant_name':                'Registrant:(.+)',   # not available
                'registrant_id':                  'Registrant:(.+)',   # not available
                'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
                'registrant_country_code':      'Registrant\s+Country\s+Code:\s*(.+)\n',
                'creation_date':                  'created:(.+)\n',
                })
class SkEntry(Entry):
    def __init__(self, domain, text):
        super(SkEntry, self).__init__(domain, text, regex={
            'registrant_name':                'Admin-id:\s*(.+)',   # not available
            'registrant_id':                  'Admin-id\s*(.+)',   # not available
            'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
            'registrant_country_code':      'Registrant\s+Country\s+Code:\s*(.+)\n',
            'creation_date':                  'created:\s*(.+)\n',
            })

class ComEntry(Entry):
    def __init__(self, domain, text):
        super(ComEntry, self).__init__(domain, text, regex= {
            'registrant_id':                'Registry\s+Registrant\s+ID:(.*)\n',
            'registrant_name':              'Registrant\s+Name:(.*)\n',
            'registrant_country':           'Registrant\s+Country:(.*)\n',
            'registrant_country_code':      'Registrant\s+Country\s+Code:(.*)\n',
            'creation_date':                'Creation\s+Date:(.+)\n',
            })


class MeEntry(Entry):
    def __init__(self, domain, text):
        super(MeEntry, self).__init__(domain, text, regex= {
            'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
            'registrant_name':              'Registrant\s+Name:\s*(.+)\n',
            'registrant_country':           'Registrant\s+Country/Economy:\s*(.+)\n',
            'registrant_country_code':      'Registrant\s+Country/Economy:\s*(.+)\n',
            'creation_date':                'Domain\s+Create\s+Date:\s*(.+)\n',
            })

class EsEntry(Entry):
    def __init__(self, domain, text):
        super(EsEntry, self).__init__(domain, text, regex= {
            'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
            'registrant_name':              'Registrant\s+Name:\s*(.+)\n',
            'registrant_country':           'Registrant\s+Country/Economy:\s*(.+)\n',
            'registrant_country_code':      'Registrant\s+Country/Economy:\s*(.+)\n',
            'creation_date':                'Domain\s+Create\s+Date:\s*(.+)\n',
        })

class NetEntry(Entry):
    def __init__(self, domain, text):
        if 'No match for "' in text:
            raise PywhoisError(text)
        else:
            super(NetEntry, self).__init__(domain, text, regex= {
                'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
                'registrant_name':              'Registrant\s+Name:\s*(.+)\n',
                'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
                'registrant_country_code':      'Registrant\s+Country:\s*(.+)\n',
                'creation_date':                'Creation\s+Date:\s*(.+)\n',
                })

class OrgEntry(Entry):
    def __init__(self, domain, text):
        if text.strip() == 'NOT FOUND':
            raise PywhoisError(text)
        else:
            super(OrgEntry, self).__init__(domain, text, regex= {
                'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
                'registrant_name':              'Registrant\s+Name:\s*(.+)\n',
                'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
                'registrant_country_code':      'Registrant\s+Country:\s*(.+)\n',
                'creation_date':                'Created\s+On:\s*(.+)\n',
                })

class SgEntry(Entry):
    def __init__(self, domain, text):
        if text.strip() == 'NOT FOUND':
            raise PywhoisError(text)
        else:
            super(SgEntry, self).__init__(domain, text, regex= {
                'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
                'registrant_name':              'Name:\s*(.+)\n',
                'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
                'registrant_country_code':      'Registrant\s+Country:\s*(.+)\n',
                'creation_date':                'Creation\s+Date:\s*(.+)\n',
                })


class NameEntry(Entry):
    def __init__(self, domain, text):
        if 'No match.' in text:
            raise PywhoisError(text)
        else:
            super(NameEntry, self).__init__(domain, text, regex={
                'domain_name_id':  'Domain Name ID:\s*(.+)',
                'domain_name':     'Domain Name:\s*(.+)',
                'registrar_id':    'Sponsoring Registrar ID:\s*(.+)',
                'registrar':       'Sponsoring Registrar:\s*(.+)',
                'registrant_id':   'Registrant ID:\s*(.+)',
                'admin_id':        'Admin ID:\s*(.+)',
                'technical_id':    'Tech ID:\s*(.+)',
                'billing_id':      'Billing ID:\s*(.+)',
                'creation_date':   'Created On:\s*(.+)',
                'expiration_date': 'Expires On:\s*(.+)',
                'updated_date':    'Updated On:\s*(.+)',
                'name_server_ids': 'Name Server ID:\s*(.+)',  # list of name server ids
                'name_servers':    'Name Server:\s*(.+)',  # list of name servers
                'status':          'Domain Status:\s*(.+)',  # list of statuses
            })

class UkEntry(Entry):
    def __init__(self, domain, text):
        if 'Not found:' in text:
            raise PywhoisError(text)
        else:
            super(UkEntry, self).__init__(domain, text, regex={
                'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
                'registrant_name':                'Registrant:\n\s*(.+)',
                'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
                'registrant_country_code':      'Registrant\s+Country\s+Code:\s*(.+)\n',
                'creation_date':                  'Registered on:\s*(.+)',
            })

class FrEntry(Entry):
    def __init__(self, domain, text):
        if text.strip() == 'No entries found':
            raise PywhoisError(text)
        else:
            super(FrEntry, self).__init__(domain, text, regex={
                'registrant_id':                'holder-c:\s*(.+)\n',
                'registrant_name':                'Registrant:\n\s*(.+)',
                'creation_date': 'created:\s*(.+)',
                'registrant_country':           'country:\s*(.+)\n',
                'registrant_country_code':      'country:\s*(.+)\n',
                })
class NlEntry(Entry):
    def __init__(self, domain, text):
        if text.strip() == 'No entries found':
            raise PywhoisError(text)
        else:
            super(NlEntry, self).__init__(domain, text, regex={
                'registrant_id':                'holder-c:\s*(.+)\n',
                'registrant_name':                'Registrant:\n\s*(.+)',
                'creation_date': 'created:\s*(.+)',
                'registrant_country':           'country:\s*(.+)\n',
                'registrant_country_code':      'country:\s*(.+)\n',
                })

class BizEntry(Entry):
    def __init__(self, domain, text):
        super(BizEntry, self).__init__(domain, text, regex= {
            'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
            'registrant_name':              'Registrant\s+Name:\s*(.+)\n',
            'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
            'registrant_country_code':      'Registrant\s+Country\s+Code:\s*(.+)\n',
            'creation_date':                'Domain\s+Registration\s+Date:\s*(.+)\n',
            })

class TlEntry(Entry):
    def __init__(self, domain, text):
        super(TlEntry, self).__init__(domain, text, regex= {
            'registrant_id':                'Registrant\s+ID:\s*(.+)\n',
            'registrant_name':              'Registrant\s+Name:\s*(.+)\n',
            'registrant_country':           'Registrant\s+Country:\s*(.+)\n',
            'registrant_country_code':      'Registrant\s+Country\s+Code:\s*(.+)\n',
            'creation_date':                'Domain\s+Registration\s+Date:\s*(.+)\n',
            })

def get_ip_hash(ip):
    try:
        from netaddr import  IPAddress
        ip = IPAddress(ip)
        return str(ip.value)
    except ImportError:
        logger.error('"netaddr" not found using "hash()" for hashing instead')
    return hash(ip)

class _AddrUtil(object):
    def __init__(self, filename):
        import pygeoip
        # Load the database once and store it globally in interpreter memory.
        self.GEOIP = pygeoip.GeoIP(filename)
    def _get_domain(self, url):
        from urlparse import urlparse
        parsedurl = urlparse(url)
        return parsedurl.netloc
    def _get_geo_code(self, ip_address):
        if not hasattr(self, '_country_code_by_addr'):
            self._country_code_by_addr = maybe(self.GEOIP.country_code_by_addr)
        return self._country_code_by_addr(ip_address)
    def _resolve(self, domain):
        if not hasattr(self, 'query'):
            from dns.resolver import query
            self._query = ensure_iterable(maybe(query))
        return imap(str, ifilter(None, chain(self._query(domain, 'A'),self._query(domain, 'AAAA'))))
    def _get_ip_addresses(self, domain):
        import socket
        try:
            # try to resolve all A and AAAA records recursively
            return {
                'domain': domain,
                'addresses':[{ 'address': str(a), 'country': self._get_geo_code(a) } for a in self._resolve(domain)]
            }
        except:
            # fallback and resolve only one ip address
            return {
                'domain': domain,
                'addresses':[{ 'address': a, 'country': self._get_geo_code(a) } for a in socket.gethostbyname(domain)]
            }
    def _get_whois(self, domain):
        #import whois

        #pt1 = re.compile(r'(\w+):\s*(.*)\s*')
        #pt2 = re.compile(r'(?P<day>\d+)[.](?P<month>\d+)[.](?P<year>\d+)\s+(?P<hour>\d+)[:](?P<minute>\d+)[:](?P<second>\d+)')
        try:
            #domain = re.match(r'(?:.*[.])*([^.]+[.][^.]+)', domain).group(1)
            try:
                w = whois(domain)
                if w:
                    dt = filter(lambda x: not isinstance(x,str) ,w.creation_date)
                    dt = sorted(dt)[0] if dt else None
                    return {
                        'domain': domain,
                        'whois': [
                            {
                                'contact': '; '.join(w.registrant_id or w.registrant_name),
                                'address1': '; '.join(w.registrant_country_code or w.registrant_country),
                                'address2': '; '.join(w.registrant_country),
                                'date_from': dt,
                                }
                        ]
                    }
            except Exception as e:
                logger.exception(e)
        except Exception as e:
            logger.exception(e)
        return {
            'domain': domain,
            }
    def __call__(self, url):
        domain = self._get_domain(url)
        return dict(chain(self._get_ip_addresses(domain).iteritems(), self._get_whois(domain).iteritems()))





addrutil = _AddrUtil(path.join(path.dirname(__file__), 'GeoIP.dat'))