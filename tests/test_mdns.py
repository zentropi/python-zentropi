import pytest
from zentropi import mdns
from socket import inet_aton


class MockZeroconf(object):
    class SocketInfo(object):
        addresses = [inet_aton('127.0.0.1')]
        port = 26514
        properties = {'tls': False}

    def get_service_info(self, _type, _path):
        return self.SocketInfo()

    def close(self):
        pass

class MockZeroconfTLS(object):
    class SocketInfo(object):
        addresses = [inet_aton('127.0.0.1')]
        port = 26514
        properties = {'tls': True}

    def get_service_info(self, _type, _path):
        return self.SocketInfo()

    def close(self):
        pass

class MockZeroconfUnavailable(object):
    def get_service_info(self, _type, _path):
        return None

    def close(self):
        pass


def test_mdns(monkeypatch):
    monkeypatch.setattr(mdns, 'Zeroconf', MockZeroconf)
    addr = mdns.resolve_zeroconf_address()
    assert addr == 'ws://127.0.0.1:26514/'


def test_mdns_https(monkeypatch):
    monkeypatch.setattr(mdns, 'Zeroconf', MockZeroconfTLS)
    addr = mdns.resolve_zeroconf_address(schema='http')
    assert addr == 'https://127.0.0.1:26514/'

@pytest.mark.xfail(raises=ConnectionError)
def test_mdns_unavailable(monkeypatch):
    monkeypatch.setattr(mdns, 'Zeroconf', MockZeroconfUnavailable)
    addr = mdns.resolve_zeroconf_address()
