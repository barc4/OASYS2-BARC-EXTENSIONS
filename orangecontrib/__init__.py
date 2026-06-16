from pkgutil import extend_path

# orangecontrib is shared by multiple Orange/OASYS add-ons.
__path__ = extend_path(__path__, __name__)
