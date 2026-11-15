"""toffoli-oracle: classical logic -> Toffoli-native quantum oracles whose emitted cost matches the report."""

from .report import Hardware, Point, ResourceReport, lower_bound
from .xag import Gate, Op, Xag

__version__ = "0.0.1"
__all__ = ["Gate", "Hardware", "Op", "Point", "ResourceReport", "Xag", "lower_bound"]
