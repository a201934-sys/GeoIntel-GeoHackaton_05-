
"""Save/resume the existing Exploration Copilot inside the same HPC environment.

Run this file in the working notebook, then:
    checkpoint = save_copilot_session(globals())

Only explicit data/model variables are saved. Live API clients, credentials,
functions and widgets are excluded. State contains challenge data: leave the
runtime_state directory inside the HPC. Load only your own trusted checkpoint.
The original training/data-preparation notebook is still required as source
code for reproducing the model; a checkpoint is a recovery aid, not a substitute.
"""

import gzip as _state_gzip
import hashlib as _state_hashlib
import importlib.metadata as _state_metadata
import json as _state_json
import math as _state_math
import os as _state_os
from pathlib import Path as _StatePath
import pickle as _state_pickle
import platform as _state_platform
from datetime import datetime as _StateDatetime, timezone as _StateTimezone

COPILOT_SESSION_MANAGER_VERSION = 2
_STATE_HELPER_FOLDER = _StatePath(globals().get("__file__", ".")).resolve().parent
_STATE_REQUIRED = (
    "ml_dataset", "ml_results", "ml_model", "ml_inventory", "ml_source_paths",
    "ml_gemma_model", "ml_seismic_metadata", "ml_seismic_png",
)
_STATE_OPTIONAL = (
    "ml_input_root", "ml_features", "ml_centres", "ml_fullstack_path",
    "ml_inline_headers", "ml_crossline_headers", "ml_survey_x", "ml_survey_y",
    "ml_well_locations", "ml_well_info_path", "ml_eo1_deviation_path",
    "ml_deviation_evidence_by_well", "ml_well_location_check", "ml_trace_indices",
    "ml_section_crosslines", "ml_seismic_section", "ml_seismic_sample_coordinates",
    "ml_sample_interval_raw", "ml_amplitude_clip", "ml_reference_cards",
    "ml_chat_log", "ml_seismic_observation_record", "ml_seismic_observation_history",
    "ml_copilot_instructions",
    "ml_checkshot_exports", "ml_checkshots", "ml_checkshot_metadata", "ml_checkshot_qc",
    "ml_checkshot_depth_audit", "ml_td_transfer_experiment", "ml_td_transfer_review",
    "ml_eo1_path_raw", "ml_eo1_path_table", "ml_eo1_path_qc", "ml_eo1_path_metadata",
    "ml_eo1_path_export_dir", "ml_eo1_path_file_to_import",
    "ml_eo1_mdkb_interval_path", "ml_eo1_mdkb_interval_metadata",
    "ml_eo1_td_candidates", "ml_depth_reference_by_well", "ml_td_chat_installed",
    "ml_last_td_review",
)
_STATE_HELPERS = ("add_reference_library.py", "add_seismic_tool.py")
_STATE_TD_HELPER = "add_td_transfer_tool.py"
_STATE_GUIDANCE = """
Describe the 2000-2200 m selection as a well interval, not an established
reservoir interval. VSH/PHIT contrasts alone do not identify sandstone,
siltstone, a reservoir or an effective seal; do not use those lithologies as
evidence of a field match. Discuss structural/stratigraphic geometry on
neighbouring inlines and crosslines now, in parallel with obtaining tie data.
A time-depth tie is needed to connect the selected well interval with specific
seismic events. Allow a combined structural-stratigraphic hypothesis when
supported, and allow insufficient evidence instead of forcing a binary choice.
"""


def apply_demo_guidance(namespace):
    for name in ("_EC_INSTRUCTIONS", "ml_copilot_instructions"):
        if isinstance(namespace.get(name), str) and _STATE_GUIDANCE not in namespace[name]:
            namespace[name] += "\n" + _STATE_GUIDANCE


def _state_digest(path):
    digest = _state_hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _state_versions():
    result = {"python": _state_platform.python_version()}
    for package in ("numpy", "pandas", "scikit-learn"):
        try:
            result[package] = _state_metadata.version(package)
        except _state_metadata.PackageNotFoundError:
            result[package] = None
    return result


def save_copilot_session(namespace, directory="runtime_state", helper_directory=None):
    """Create a fresh, private snapshot; no files or current variables overwritten."""
    missing = [name for name in _STATE_REQUIRED if name not in namespace]
    if missing:
        raise ValueError("Run the working prototype first. Missing: " + ", ".join(missing))
    helper_root = _StatePath(helper_directory or _STATE_HELPER_FOLDER).resolve()
    td_enabled = (namespace.get("ml_td_chat_installed") is True
                  or getattr(namespace.get("ml_copilot_extension"), "_td_transfer_extension", False) is True)
    if td_enabled and any(name not in namespace for name in ("ml_eo1_td_candidates", "ml_depth_reference_by_well")):
        raise ValueError("The T/D extension is active but its candidate/reference data are missing.")
    helper_names = _STATE_HELPERS + ((_STATE_TD_HELPER,) if td_enabled else ())
    helpers = {name: helper_root / name for name in helper_names}
    if any(not path.is_file() for path in helpers.values()):
        raise ValueError("Save the required helper scripts beside the notebook: " + ", ".join(helper_names))
    state = {name: namespace[name] for name in _STATE_REQUIRED + _STATE_OPTIONAL if name in namespace}
    if td_enabled:
        state["ml_td_chat_installed"] = True
    if not bytes(state["ml_seismic_png"]).startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("The loaded section image is not a PNG.")
    root = _StatePath(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    ignore = root / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n!.gitignore\n", encoding="utf-8")
    snapshot = root / _StateDatetime.now(_StateTimezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    snapshot.mkdir(exist_ok=False)
    source_folder = snapshot / "source"
    source_folder.mkdir()
    source_hashes = {}
    for name, original in helpers.items():
        destination = source_folder / name
        destination.write_bytes(original.read_bytes())
        source_hashes[name] = _state_digest(destination)
    state_file = snapshot / "session.pkl.gz"
    with _state_gzip.open(state_file, "wb", compresslevel=3) as handle:
        _state_pickle.dump({"format_version":2, "state":state}, handle,
                           protocol=_state_pickle.HIGHEST_PROTOCOL)
    client = namespace.get("ml_client")
    base_url = str(getattr(client, "base_url", "")) if client is not None else ""
    manifest = {
        "format_version":2, "created_at_utc":_StateDatetime.now(_StateTimezone.utc).isoformat(),
        "state_sha256":_state_digest(state_file), "helper_sha256":source_hashes,
        "helper_order":list(helper_names), "td_extension_enabled":td_enabled,
        "environment_versions":_state_versions(), "saved_variables":sorted(state),
        "well_count":len(state["ml_source_paths"]), "total_samples":len(state["ml_dataset"]),
        "assigned_samples":len(state["ml_results"]),
        "inline_id":int(state["ml_seismic_metadata"]["inline_id"]),
        "image_sha256":_state_hashlib.sha256(bytes(state["ml_seismic_png"])).hexdigest(),
        "llm_base_url":base_url,
        "handling":"Private HPC-only state. API key and live client were not saved.",
    }
    (snapshot / "manifest.json").write_text(_state_json.dumps(manifest, indent=2), encoding="utf-8")
    print("Saved HPC-only session:", snapshot)
    print(f"{manifest['well_count']} wells; {manifest['total_samples']:,} samples; inline {manifest['inline_id']}.")
    print("Conditional T/D extension included:", td_enabled)
    print("Keep this runtime_state folder inside the HPC.")
    return str(snapshot)


def _state_register_well_functions(namespace):
    def interval_evidence(well_id, top_m, bottom_m):
        well = str(well_id).strip().lower()
        if well not in namespace["ml_source_paths"]:
            raise ValueError("Unknown well name.")
        if isinstance(top_m, bool) or isinstance(bottom_m, bool):
            raise ValueError("Depths must be finite numbers.")
        top, bottom = float(top_m), float(bottom_m)
        if not _state_math.isfinite(top) or not _state_math.isfinite(bottom) or top >= bottom:
            raise ValueError("Give a finite top depth smaller than the bottom depth.")
        dataset, results = namespace["ml_dataset"], namespace["ml_results"]
        if not dataset.index.is_unique or not results.index.is_unique:
            raise ValueError("Sample indices must be unique.")
        rows = dataset.loc[dataset["WELL"].eq(well) & dataset["DEPTH"].ge(top) & dataset["DEPTH"].lt(bottom)]
        if rows.empty:
            raise ValueError("No samples occur in the requested interval.")
        assignments = results["GROUP"].reindex(rows.index)
        assigned = rows.loc[assignments.notna()].copy()
        assigned["GROUP"] = assignments.loc[assigned.index].to_numpy()
        groups = []
        for label, group in assigned.groupby("GROUP", sort=True, observed=True):
            groups.append({"GROUP":int(label), "samples":int(len(group)),
                           "VSH_median":round(float(group["VSH"].median()),4),
                           "PHIT_median":round(float(group["PHIT"].median()),4),
                           "assigned_sample_percent":round(100 * len(group) / len(assigned),4),
                           "description":f"Provisional property group {int(label)}; see VSH and PHIT medians"})
        return {"well":well, "source_file":str(namespace["ml_source_paths"][well]),
                "top_m":top, "bottom_m_exclusive":bottom,
                "depth_reference":"LAS depth; MD/TVD and MDKB relationship not confirmed",
                "total_samples":int(len(rows)), "assigned_samples":int(len(assigned)),
                "excluded_samples":int(len(rows)-len(assigned)),
                "zero_VSH_samples":int(rows["VSH"].eq(0).sum()),
                "zero_PHIT_samples":int(rows["PHIT"].eq(0).sum()),
                "groups":groups, "status":"provisional_property_groups",
                "limitations":["Groups have not been validated as lithology classes.",
                               "Percentages describe sample counts, not bed thickness.",
                               "Excluded samples require QC review."]}

    def explain_interval(well_id, top_m, bottom_m, question):
        app = namespace["ml_copilot_extension"]
        evidence = app._well_record(well_id, top_m, bottom_m)
        content = [{"type":"text", "text":"QUESTION:\n" + str(question) + "\nWELL EVIDENCE:\n" +
                    _state_json.dumps(evidence, indent=2, allow_nan=False) +
                    "\nUse [W1]. No seismic image is supplied. A calculated well table will be prepended; "
                    "explain qualitatively without repeating counts or group percentages."}]
        review = app._complete_review(content, well_record=evidence, required_sources=("W1",))
        result = {key:value for key,value in review.items() if not key.startswith("_")}
        result.update(evidence=evidence, sources=[evidence])
        return result

    namespace["ml_interval_evidence"] = interval_evidence
    namespace["ml_explain_interval"] = explain_interval


def restore_copilot_session(checkpoint, namespace, client=None, show_ui=True):
    """Resume your own snapshot in the same environment, without retraining.

    For a non-destructive check, pass a new dict and the existing ml_client.
    Source checksums detect accidental changes, not malicious trusted-pickle
    content. Use only a snapshot you created, kept inside the same HPC.
    """
    folder = _StatePath(checkpoint).expanduser().resolve()
    if folder.is_file():
        folder = folder.parent
    manifest = _state_json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format_version") not in (1, 2):
        raise ValueError("Unsupported checkpoint format.")
    helper_names = tuple(manifest.get("helper_order", _STATE_HELPERS))
    if helper_names not in (_STATE_HELPERS, _STATE_HELPERS + (_STATE_TD_HELPER,)):
        raise ValueError("Checkpoint has an unsupported helper list or order.")
    td_enabled = _STATE_TD_HELPER in helper_names
    if bool(manifest.get("td_extension_enabled", False)) != td_enabled:
        raise ValueError("Checkpoint T/D flag and helper list disagree.")
    state_file = folder / "session.pkl.gz"
    if _state_digest(state_file) != manifest["state_sha256"]:
        raise ValueError("Checkpoint checksum mismatch; the current namespace was not changed.")
    code = {}
    for name in helper_names:
        path = folder / "source" / name
        if _state_digest(path) != manifest["helper_sha256"][name]:
            raise ValueError("Helper checksum mismatch; the current namespace was not changed.")
        code[name] = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    if _state_versions() != manifest["environment_versions"]:
        raise ValueError("Use the same Python/numpy/pandas/scikit-learn environment as the saved session.")
    with _state_gzip.open(state_file, "rb") as handle:
        payload = _state_pickle.load(handle)
    if payload.get("format_version") != manifest["format_version"]:
        raise ValueError("Unsupported state format.")
    state = payload["state"]
    if any(name not in state for name in _STATE_REQUIRED):
        raise ValueError("Checkpoint is incomplete.")
    if td_enabled and any(name not in state for name in ("ml_eo1_td_candidates", "ml_depth_reference_by_well")):
        raise ValueError("Checkpoint is missing T/D candidate or reference data.")
    active_client = client if client is not None else namespace.get("ml_client")
    if active_client is None:
        base_url = _state_os.environ.get("EXPLORATION_LLM_BASE_URL") or manifest.get("llm_base_url")
        if not base_url:
            raise ValueError("Configure ml_client first, or set EXPLORATION_LLM_BASE_URL.")
        from openai import OpenAI
        active_client = OpenAI(base_url=base_url,
                               api_key=_state_os.environ.get("EXPLORATION_LLM_API_KEY", "token-not-needed"),
                               timeout=20.0, max_retries=0)
    previous = dict(namespace)
    try:
        for name in _STATE_REQUIRED + _STATE_OPTIONAL:
            if name not in state:
                namespace.pop(name, None)
        namespace.pop("ml_review_td_transfer_chat", None)
        namespace.update(state)
        namespace["ml_client"] = active_client
        namespace["__name__"] = "_copilot_recovery"
        for name in helper_names:
            exec(code[name], namespace)
        if "ml_reference_cards" in state:
            namespace["ml_reference_cards"] = state["ml_reference_cards"]
        for stale in ("_ec_original_interval_evidence", "_ml_interval_before_deviation"):
            namespace.pop(stale, None)
        _state_register_well_functions(namespace)
        apply_demo_guidance(namespace)
        app = namespace["install_exploration_extension"](namespace, show_ui=False)
        if td_enabled:
            app = namespace["install_td_transfer_chat"](namespace, show_ui=False)
        if "__name__" in previous:
            namespace["__name__"] = previous["__name__"]
        else:
            namespace.pop("__name__", None)
    except Exception:
        namespace.clear()
        namespace.update(previous)
        raise
    if show_ui:
        app.show_ui()
    print("Restored the saved model, assignments, well evidence and section; no Gemma/API request made.")
    return app


def verify_copilot_checkpoint(checkpoint, namespace, well_id="eo-1", top_m=2000, bottom_m=2200):
    """Verify recovery in a separate namespace; preserve the live app and data."""
    import numpy as np
    live_app = namespace.get("ml_copilot_extension")
    if live_app is None:
        raise ValueError("Install the working Copilot first.")
    before = live_app._well_record(well_id, top_m, bottom_m)
    recovered = {}
    try:
        recovered_app = restore_copilot_session(checkpoint, recovered,
                                               client=namespace.get("ml_client"), show_ui=False)
        after = recovered_app._well_record(well_id, top_m, bottom_m)
        def signature(packet):
            totals = tuple(int(packet[key]) for key in ("total_samples", "assigned_samples", "excluded_samples",
                                                        "zero_VSH_samples", "zero_PHIT_samples"))
            groups = sorted((int(group["GROUP"]), int(group["samples"]),
                             round(float(group["VSH_median"]),4), round(float(group["PHIT_median"]),4),
                             round(float(group["assigned_sample_percent"]),4)) for group in packet["groups"])
            return totals, groups
        if signature(before) != signature(after):
            raise ValueError("Recovered interval statistics do not match the current session.")
        if bytes(recovered["ml_seismic_png"]) != bytes(namespace["ml_seismic_png"]):
            raise ValueError("Recovered section image does not match the current session.")
        td_checked = False
        if namespace.get("ml_td_chat_installed") is True:
            if not getattr(recovered_app, "_td_transfer_extension", False):
                raise ValueError("The conditional T/D chat tool was not restored.")
            live_td = live_app._candidate_record()
            recovered_td = recovered_app._candidate_record()
            if _state_json.dumps(live_td, sort_keys=True, allow_nan=False) != _state_json.dumps(recovered_td, sort_keys=True, allow_nan=False):
                raise ValueError("Recovered conditional T/D evidence differs from the current session.")
            for key in ("curve", "boundaries", "donors"):
                if not namespace["ml_eo1_td_candidates"][key].equals(recovered["ml_eo1_td_candidates"][key]):
                    raise ValueError("Recovered T/D candidate tables differ from the current session.")
            if before.get("depth_reference_confirmation") != after.get("depth_reference_confirmation"):
                raise ValueError("Recovered depth-reference confirmation differs from the current session.")
            td_checked = True
        model_checked = False
        if hasattr(namespace["ml_model"], "predict") and len(namespace["ml_results"]):
            features = namespace.get("ml_features", ["VSH", "PHIT"])
            indices = namespace["ml_results"].index[:50]
            inputs = namespace["ml_dataset"].loc[indices, features]
            if not np.array_equal(namespace["ml_model"].predict(inputs), recovered["ml_model"].predict(inputs)):
                raise ValueError("Recovered model predictions differ from the current model.")
            model_checked = True
        report = {"status":"verified_against_current_session", "well":str(well_id),
                  "interval_m":[float(top_m),float(bottom_m)],
                  "interval_statistics_match":True, "section_image_match":True,
                  "model_predictions_compared":model_checked,
                  "conditional_TD_evidence_match":td_checked,
                  "current_session_replaced":False, "llm_requests_made":0}
    finally:
        recovered.clear()
    print("Checkpoint verified against the live session. Current app was preserved.")
    return report


save_copilot_session._td_session_manager_version = 2
restore_copilot_session._td_session_manager_version = 2
verify_copilot_checkpoint._td_session_manager_version = 2


def _state_require_td_v2(namespace):
    if (getattr(save_copilot_session, "_td_session_manager_version", None) != 2
            or getattr(verify_copilot_checkpoint, "_td_session_manager_version", None) != 2
            or not {"ml_eo1_td_candidates", "ml_depth_reference_by_well"}.issubset(_STATE_OPTIONAL)):
        raise RuntimeError("The T/D-capable manager is not active. Run manage_td_session_v2.py again.")
    if not getattr(namespace.get("ml_copilot_extension"), "_td_transfer_extension", False):
        raise RuntimeError("The live T/D chat extension is not active. Run add_td_transfer_tool.py first.")
    missing = [name for name in ("ml_eo1_td_candidates", "ml_depth_reference_by_well") if name not in namespace]
    if missing:
        raise RuntimeError("The live T/D data are missing: " + ", ".join(missing))


def save_td_session_v2(namespace, directory="runtime_state", helper_directory=None):
    """Strict T/D snapshot entry point: never silently save a baseline-only session."""
    _state_require_td_v2(namespace)
    return save_copilot_session(namespace, directory, helper_directory)


def verify_td_session_v2(checkpoint, namespace, well_id="eo-1", top_m=2000, bottom_m=2200):
    """Require successful T/D recovery, not only well-model and image recovery."""
    _state_require_td_v2(namespace)
    report = verify_copilot_checkpoint(checkpoint, namespace, well_id, top_m, bottom_m)
    if report.get("conditional_TD_evidence_match") is not True:
        raise ValueError("The T/D-specific recovery check did not pass.")
    report["session_manager_version"] = 2
    return report


if __name__ == "__main__":
    apply_demo_guidance(globals())
    print("Loaded session manager VERSION 2: conditional T/D recovery supported.")
    print("For the active T/D prototype: checkpoint = save_td_session_v2(globals(), helper_directory='.')")
