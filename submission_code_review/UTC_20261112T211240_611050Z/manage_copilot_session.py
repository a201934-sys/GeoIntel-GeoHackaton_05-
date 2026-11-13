"""Clarify the live T/D explanation; preserve estimates and update helper guidance.

Run in the existing HPC notebook. Makes no model request and writes no survey
data. A first-use backup of the owned chat helper is kept beside that helper.
"""
from pathlib import Path
import copy
import math


_TD_REASONING_REFINEMENT = """
TIME-DEPTH METHOD CLARIFICATIONS:
Explain the complete calculation: MDKB is mapped to TVDSS using the exported
path; each donor's exported TWT is interpolated at those TVDSS depths; the
nearest candidate uses one donor alone and IDW blends the two selected donors.
Path interpolation alone does not produce the time estimates.
Use nearest_source_wells, IDW_source_wells and shared_source_wells when supplied.
The nearest candidate does not use every donor used by IDW. Their common donor
contributes shared information, so they are not independent validations.
The location triangle uses ALL THREE calibration source wells, not the two
selected IDW donors. Name that set or explicitly say three calibration wells.
Distinguish spatial/geographic transfer outside this triangle from interpolation
WITHIN the donor TVDSS coverage. Never imply that depth extrapolation occurred
when depth_extrapolation_performed is false. Map location alone does not measure
the target error. Name the ranking criterion: overall mean MAE can favour IDW
while nearest wins more individual wells or has lower highest-per-well MAE.
Do not imply IDW wins every well or depth band. Use the supplied per-well winners
and validation data. Target checkshot/VSP recommendations must identify eo-1;
the source-well surveys are already supplied. Such calibration constrains time
versus depth; it does not by itself validate lithology or amplitude response.
"""


def refine_td_reasoning(namespace, helper_file="add_td_transfer_tool.py"):
    app = namespace.get("ml_copilot_extension")
    method = getattr(type(app), "_review_td_transfer", None)
    if method is None or not getattr(app, "_td_transfer_extension", False):
        raise RuntimeError("Install the T/D chat extension first.")
    helper = Path(helper_file).resolve()
    if not helper.is_file():
        raise FileNotFoundError("Save the T/D helper beside the notebook first: " + str(helper))
    source = helper.read_text(encoding="utf-8")
    if "class TDTransferChatExtension" not in source or "_TD_RULES" not in source:
        raise ValueError("Selected file is not the T/D helper; it was not modified.")

    candidate = copy.deepcopy(namespace["ml_eo1_td_candidates"])
    record = candidate["evidence"]
    experiment = namespace["ml_td_transfer_experiment"]
    record["calibration_source_wells"] = sorted(experiment["curves"])
    record["nearest_source_wells"] = [record["nearest_donor"]]
    record["IDW_source_wells"] = [row["well"] for row in record["IDW_donors"]]
    record["shared_source_wells"] = sorted(set(record["nearest_source_wells"]) & set(record["IDW_source_wells"]))

    scores = experiment["scores"].pivot(index="held_out", columns="method", values="MAE_ms")
    winners = []
    for well, row in scores.iterrows():
        nearest, idw = float(row["nearest"]), float(row["IDW_power_1"])
        if not math.isfinite(nearest) or not math.isfinite(idw):
            raise ValueError("Per-well MAE values must be finite.")
        winner = ("tie" if math.isclose(nearest, idw, rel_tol=0, abs_tol=1e-10)
                  else "nearest" if nearest < idw else "IDW_power_1")
        winners.append({"held_out_well": str(well), "lower_MAE_method": winner})
    record["per_well_MAE_winners"] = winners
    record["construction_steps"] = [
        "Map LAS MDKB to TVDSS by linear interpolation of exported DUG path stations.",
        "Interpolate each selected donor's TWT at the same TVDSS, within its exported depth coverage.",
        "Nearest uses the nearest source alone; power-1 IDW blends the two nearest sources using listed X/Y distances.",
    ]
    z = [float(row["TVDSS_m"]) for row in record["boundaries"]]
    coverages = {row["well"]: row["TVDSS_coverage_m"] for row in record["source_surveys"]}
    for donor in record["IDW_source_wells"]:
        low, high = map(float, coverages[donor])
        if not (math.isfinite(low) and math.isfinite(high) and low <= min(z) <= max(z) <= high):
            raise ValueError("Source depth coverage does not support this interval; review candidates.")
    record["depth_extrapolation_performed"] = False
    record["spatial_transfer_context"] = {
        "target_relative_to_calibration_source_triangle": record["donor_triangle_location"],
        "triangle_source_wells": record["calibration_source_wells"],
        "selected_IDW_donors": record["IDW_source_wells"],
        "basis": "Listed well positions; separate from the within-coverage depth interpolation",
    }

    marker = "# TD_REASONING_REFINEMENT_V1"
    if marker not in source:
        backup = helper.with_name(helper.stem + ".before_reasoning_update.py")
        if not backup.exists():
            backup.write_bytes(helper.read_bytes())
        updated = source + "\n\n" + marker + "\n_TD_RULES += " + repr(_TD_REASONING_REFINEMENT) + "\n"
        compile(updated, str(helper), "exec")
        helper.write_text(updated, encoding="utf-8")
    runtime = method.__globals__
    if _TD_REASONING_REFINEMENT not in runtime["_TD_RULES"]:
        runtime["_TD_RULES"] += "\n" + _TD_REASONING_REFINEMENT
    namespace["_TD_RULES"] = runtime["_TD_RULES"]
    namespace["ml_eo1_td_candidates"] = candidate
    if app.history:
        previous_reply = app.history[-1].get("reply", {})
        if (previous_reply.get("action") == "review_td_transfer"
                and "extrapolations rather than interpolations" in previous_reply.get("answer", "").lower()):
            note = ("Earlier wording needs correction: the target is outside the three-calibration-well "
                    "triangle in map view; donor TWT was interpolated within depth coverage.")
            flags = previous_reply.setdefault("quality_flags", [])
            if note not in flags:
                flags.append(note)
    print("Clarified T/D construction, source sharing, map geometry and ranking criteria.")
    print("Per-well MAE comparison:", winners)
    print("Existing time estimates are unchanged. No Gemma request was made.")
    return record


if __name__ == "__main__":
    ml_td_reasoning_record = refine_td_reasoning(globals())
