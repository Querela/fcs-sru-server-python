# try:
#     import pkg_resources
#
#     pkg_resources.declare_namespace(__name__)
# except ImportError:
#     import pkgutil
#
#     __path__ = pkgutil.extend_path(__path__, __name__)

# https://pawamoy.github.io/posts/plugins-as-python-native-namespace-packages/
# https://github.com/microsoft/pyright/issues/2882

__path__ = __import__("pkgutil").extend_path(__path__, __name__)
