"""
Expose ORM models from the legacy ``shared/models.py`` module.

The repository currently contains both a ``shared/models.py`` file and a
``shared/models/`` package. Importing ``shared.models`` resolves to this
package, so we bridge it to the file-based implementation instead of
recursively importing ourselves.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


_MODELS_FILE = Path(__file__).resolve().parent.parent / "models.py"
_SPEC = spec_from_file_location("shared._models_file", _MODELS_FILE)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load shared models from {_MODELS_FILE}")

_MODULE = module_from_spec(_SPEC)
sys.modules.setdefault("shared._models_file", _MODULE)
_SPEC.loader.exec_module(_MODULE)

KYCStatus = _MODULE.KYCStatus
JobStatus = _MODULE.JobStatus
JobSearchStatus = _MODULE.JobSearchStatus
PipelineStage = _MODULE.PipelineStage
InvoiceStatus = _MODULE.InvoiceStatus
GuaranteeStatus = _MODULE.GuaranteeStatus
PaymentMethod = _MODULE.PaymentMethod
EmploymentType = _MODULE.EmploymentType
WorkLocationType = _MODULE.WorkLocationType

TimestampMixin = _MODULE.TimestampMixin
UUIDPrimaryKey = _MODULE.UUIDPrimaryKey
SoftDeleteMixin = _MODULE.SoftDeleteMixin

Employer = _MODULE.Employer
Candidate = _MODULE.Candidate
Job = _MODULE.Job
MatchResult = _MODULE.MatchResult
Invoice = _MODULE.Invoice
Guarantee = _MODULE.Guarantee

__all__ = [
    "KYCStatus",
    "JobStatus",
    "JobSearchStatus",
    "PipelineStage",
    "InvoiceStatus",
    "GuaranteeStatus",
    "PaymentMethod",
    "EmploymentType",
    "WorkLocationType",
    "TimestampMixin",
    "UUIDPrimaryKey",
    "SoftDeleteMixin",
    "Employer",
    "Candidate",
    "Job",
    "MatchResult",
    "Invoice",
    "Guarantee",
]
