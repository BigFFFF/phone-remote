from __future__ import annotations

import logging
import socket
from dataclasses import dataclass

from zeroconf import IPVersion, ServiceInfo, Zeroconf

from . import API_VERSION, __version__
from .network import local_ipv4_addresses
from .security import ServerIdentity

SERVICE_TYPE = "_phone-remote._tcp.local."


@dataclass
class DiscoveryPublisher:
    identity: ServerIdentity
    port: int
    logger: logging.Logger
    zeroconf: Zeroconf | None = None
    service: ServiceInfo | None = None

    def start(self) -> bool:
        lan_addresses = local_ipv4_addresses()
        addresses = [socket.inet_aton(value) for value in lan_addresses]
        if not addresses:
            self.logger.warning("mDNS discovery not started: no non-loopback IPv4 address")
            return False
        try:
            properties = {
                "serverId": self.identity.server_id,
                "name": self.identity.display_name,
                "apiVersion": str(API_VERSION),
                "serverVersion": __version__,
                "identity": self.identity.fingerprint[:16],
                "tls": "1",
            }
            instance = f"{self.identity.server_id}.{SERVICE_TYPE}"
            self.service = ServiceInfo(
                SERVICE_TYPE,
                instance,
                addresses=addresses,
                port=self.port,
                properties=properties,
                server=f"{socket.gethostname()}.local.",
            )
            self.zeroconf = Zeroconf(
                interfaces=lan_addresses,
                ip_version=IPVersion.V4Only,
            )
            self.zeroconf.register_service(self.service)
        except Exception:
            if self.zeroconf is not None:
                self.zeroconf.close()
            self.zeroconf = None
            self.service = None
            self.logger.exception("mDNS discovery registration failed")
            return False
        self.logger.info("mDNS discovery started service=%s port=%s", SERVICE_TYPE, self.port)
        return True

    def close(self) -> None:
        if self.zeroconf is not None:
            if self.service is not None:
                try:
                    self.zeroconf.unregister_service(self.service)
                except Exception:
                    self.logger.exception("mDNS discovery unregistration failed")
            self.zeroconf.close()
        self.zeroconf = None
        self.service = None
