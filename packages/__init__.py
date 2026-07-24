import os
import sys

# Inject 'core-models' path into sys.path to allow importing 'tmf_reference_model'
# directly, since 'core-models' contains a hyphen and cannot be imported using standard dot notation.
_core_models_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "core-models")
)
if _core_models_path not in sys.path:
    sys.path.insert(0, _core_models_path)
