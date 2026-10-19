"""Let v1 import Chroma when Windows blocks grpc's cygrpc DLL.

Local Chroma talks to chroma_db through its own library. The blocked file is
only pulled in because Chroma imports a gRPC telemetry exporter at startup.
"""

import sys
from types import ModuleType


class _Flex(ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        child = _Flex(name)
        setattr(self, name, child)
        return child

    def __call__(self, *args, **kwargs):
        return _Flex("call")


def install() -> None:
    cy = _Flex("cygrpc")
    cy.CompressionAlgorithm.none = 0
    cy.CompressionAlgorithm.deflate = 1
    cy.CompressionAlgorithm.gzip = 2
    pkg = _Flex("grpc._cython")
    pkg.cygrpc = cy
    sys.modules["grpc._cython"] = pkg
    sys.modules["grpc._cython.cygrpc"] = cy
