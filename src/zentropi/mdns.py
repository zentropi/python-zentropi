from zeroconf import Zeroconf
from socket import inet_ntoa as bytes_to_ipv4_dotted


def resolve_zeroconf_address(name='zencelium', schema='ws'):
    TYPE = '_http._tcp.local.'
    zeroconf = Zeroconf()
    try:
        sinfo = zeroconf.get_service_info(TYPE, name + '.' + TYPE)
    finally:
        zeroconf.close()
    if not sinfo:
        raise Exception('Unable to find server through Zeroconf.')
    addr = bytes_to_ipv4_dotted(sinfo.addresses[0])
    schema = schema + ('s' if sinfo.properties.get('tls') else '')
    return f'{schema}://{addr}:{sinfo.port}/'
