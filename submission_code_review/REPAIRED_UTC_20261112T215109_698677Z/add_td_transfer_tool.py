
"""Connect the existing conditional eo-1 T/D candidates to Exploration Copilot.

Save beside add_seismic_tool.py, then run in the existing notebook:
    %run -i add_td_transfer_tool.py

Installation makes no model request. Data and original surveys stay in the HPC.
"""
import base64 as _td_base64
import copy as _td_copy
import hashlib as _td_hashlib
import json as _td_json
import math as _td_math
import re as _td_re


_TD_RULES = """
ADDITIONAL TIME-DEPTH EVIDENCE RULES:
T1 is a calculated conditional transfer model, not measured target checkshots.
Cite [T1] for its estimates, donor choices, assumptions and validation context.
Its LAS MDKB reference is confirmed from project configuration. Its time datum
and seismic alignment remain UNVERIFIED. Never call it a verified well tie,
measured eo-1 survey, synthetic seismogram, or proof of a trapping mechanism.
Use the Python-generated tables for numerical T/D values, donor weights and
validation errors; explain them qualitatively instead of repeating numbers.
Distance weights are not confidence probabilities. Model differences are not
confidence intervals. Both candidates share donor data, so agreement is not
independent confirmation. Three-well validation does not measure eo-1's error.
The target lies outside the source-location triangle when T1 says 'outside'.
This is geometric context, not a confidence boundary or proof of failure.
Keep MDKB, TVDSS, donor-export TWT and seismic time distinct. No T1 time may
be asserted to identify a specific S1 reflector while datum alignment remains
unverified. Listed-position proximity does not establish interval intersection.
The original sonic/density logs are not supplied in W1's inventory; do not
invent them. A synthetic seismogram still needs appropriate acoustic data,
wavelet/phase/polarity and time-depth calibration. Describe source and target
data availability separately: measured source-well surveys do not become
measured target-well surveys. If S1 is absent, make no new image observations.
Separate observations, derived estimates, geological hypotheses and next checks.
"""


def _td_citations(text):
    return {identifier.upper()
            for bracket in _td_re.findall(r"\[([^\]\n]+)\]", text)
            for identifier in _td_re.findall(r"\b[WSRAT]\d+\b", bracket, _td_re.I)}


def _td_requested(question):
    return bool(_td_re.search(
        r"\b(?:checkshots?|TWT|IDW|borrow\w*|transfer\w*|synthetic\w*|"
        r"T\s*/\s*D|time[-\u2013\u2014\s]+depth|inverse[-\s]+distance|well[-\s]+to[-\s]+seismic|ties?)\b",
        question, _td_re.I))


def _td_fact_table(record):
    rows = record["boundaries"]
    lines = [
        "**Conditional transferred time-depth estimates [T1]**",
        "Donor-export TWT reference; alignment to seismic remains unverified.", "",
        "| Boundary | MDKB (m) | TVDSS (m) | Nearest TWT (ms) | IDW TWT (ms) |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        label = "Top" if row is rows[0] else "Bottom boundary (excluded)"
        lines.append(f"| {label} | {float(row['MDKB_m']):.3f} | {float(row['TVDSS_m']):.3f} | "
                     f"{float(row['TWT_nearest_ms']):.3f} | {float(row['TWT_IDW_ms']):.3f} |")
    donor_text = "; ".join(
        f"{d['well']}: {100*float(d['weight']):.2f}% distance weight, "
        f"{float(d['distance_km']):.3f} km listed-position distance"
        for d in record["IDW_donors"]
    )
    lines += ["", donor_text + " [T1]",
              f"Maximum candidate difference at the planning nodes: "
              f"{float(record['max_candidate_difference_ms']):.3f} ms. "
              "This is a sensitivity measure, not a confidence interval. [T1]", "",
              "| Exploratory three-well comparison | Mean well MAE (ms) | Mean well RMSE (ms) | Highest well MAE (ms) |",
              "|---|---:|---:|---:|"]
    for score in record["validation_context"]:
        lines.append(f"| {score['method']} | {float(score['mean_well_MAE_ms']):.3f} | "
                     f"{float(score['mean_well_RMSE_ms']):.3f} | {float(score['worst_well_MAE_ms']):.3f} |")
    lines += ["", "These validation errors compare interpolated source-well exports; "
              "they do not measure eo-1's true error. [T1]"]
    return "\n".join(lines)


class TDTransferChatExtension:
    _td_transfer_extension = True

    def __init__(self, namespace, base):
        self.ns, self.base, self.ui = namespace, base, None
        self.history = base.history
        self._candidate_record()
        self._connect_depth_reference()

    def __getattr__(self, name):
        return getattr(self.base, name)

    def _connect_depth_reference(self):
        current = self.base.well_evidence
        original = getattr(current, "_td_original_well_evidence", current)
        ns = self.ns

        def confirmed(well, top, bottom):
            record = _td_copy.deepcopy(original(well, top, bottom))
            fact = ns.get("ml_depth_reference_by_well", {}).get(str(record["well"]).lower(), {})
            if fact.get("confirmed") is True and fact.get("canonical") == "MDKB":
                record["depth_reference"] = "MDKB (m), confirmed from DUG project log-set configuration"
                record["depth_reference_confirmation"] = _td_copy.deepcopy(fact)
            return record

        confirmed._td_original_well_evidence = original
        self.base.well_evidence = confirmed
        ns["ml_interval_evidence"] = confirmed

    def _candidate_record(self):
        record = _td_copy.deepcopy(self.ns["ml_eo1_td_candidates"]["evidence"])
        if (record.get("evidence_id") != "T1" or record.get("well") != "eo-1"
                or record.get("status") != "conditional_transferred_TD_estimates_not_measured_target_checkshots"
                or record.get("time_depth_tie_established") is not False
                or record.get("time_datum_verified") is not False
                or record.get("synthetic_seismogram_generated") is not False):
            raise ValueError("This tool accepts the existing conditional eo-1 candidate record only.")
        fact = self.ns.get("ml_depth_reference_by_well", {}).get("eo-1", {})
        if fact.get("confirmed") is not True or fact.get("canonical") != "MDKB":
            raise ValueError("Record the confirmed eo-1 LAS MDKB reference before installing.")
        top, bottom = map(float, record["interval_MDKB_m"])
        if not _td_math.isfinite(top) or not _td_math.isfinite(bottom) or top >= bottom:
            raise ValueError("Candidate interval is invalid.")
        if len(record["boundaries"]) != 2:
            raise ValueError("Candidate interval needs its top and bottom boundary.")
        for i, row in enumerate(record["boundaries"]):
            if float(row["MDKB_m"]) != (top if i == 0 else bottom):
                raise ValueError("Candidate boundary and interval scope disagree.")
            for key in ("TVDSS_m", "TWT_nearest_ms", "TWT_IDW_ms"):
                if not _td_math.isfinite(float(row[key])):
                    raise ValueError("Candidate boundary values must be finite.")
        experiment = self.ns.get("ml_td_transfer_experiment", {})
        if isinstance(experiment, dict) and "summary" in experiment and "scores" in experiment:
            current = experiment["summary"].reset_index().to_dict(orient="records")
            expected = {r["method"]: r for r in record["validation_context"]}
            if {r["method"] for r in current} != set(expected):
                raise ValueError("Validation context changed; rebuild the conditional candidates.")
            for score in current:
                if any(not _td_math.isclose(float(score[key]), float(expected[score["method"]][key]),
                                           rel_tol=1e-10, abs_tol=1e-10)
                       for key in ("mean_well_MAE_ms", "mean_well_RMSE_ms", "worst_well_MAE_ms")):
                    raise ValueError("Validation scores changed; rebuild the conditional candidates.")
            record["validation_by_well"] = experiment["scores"].to_dict(orient="records")
            record["held_out_well_names"] = sorted(experiment["scores"]["held_out"].unique().tolist())
        review = self.ns.get("ml_td_transfer_review", {})
        if isinstance(review, dict) and review.get("target_well") == "eo-1" and "by_depth" in review:
            record["exploratory_validation_by_TVDSS_band"] = review["by_depth"].to_dict(orient="records")
        _td_json.dumps(record, allow_nan=False)
        return record

    def ask(self, question):
        question = str(question).strip()
        if not question or len(question) > 4000:
            return {"answer": "Enter a question of 1-4000 characters.", "action": "clarify"}
        record = self._candidate_record()
        scope = (f"eo-1 from {float(record['interval_MDKB_m'][0]):g} to "
                 f"{float(record['interval_MDKB_m'][1]):g} m MDKB")
        direct_td = _td_requested(question)
        names = [w for w in self.base.wells if _td_re.search(
            r"(?<![\w-])" + _td_re.escape(w) + r"(?![\w-])", question, _td_re.I)]
        explicit = self.ns["_ec_explicit_inlines"](question)
        image_request = bool(explicit or _td_re.search(
            r"\b(?:compare|review|interpret\w*|structural|stratigraphic|trap\w*)\b", question, _td_re.I)
            and _td_re.search(r"\b(?:seismic|section|inline)\b", question, _td_re.I))
        ranges = self.ns["_ec_metre_ranges"](question)
        if (not ranges and _td_re.search(r"\bcheckshots?\b", question, _td_re.I)
                and _td_re.search(r"\b(?:which|available|loaded|have|has)\b", question, _td_re.I)):
            inventory = self.ns.get("ml_checkshots", {})
            names_loaded = sorted(inventory) if isinstance(inventory, dict) else []
            if names_loaded:
                text = "Loaded source-well T/D surveys: " + ", ".join(names_loaded) + ". "
                text += ("No measured eo-1 survey is loaded. " if "eo-1" not in names_loaded else "")
                text += "The transfer model covers " + scope + " and remains conditional [T1]."
                return {"answer": text, "action": "list_td_sources", "sources": [{
                    "evidence_id": "T1", "evidence_type": "conditional_time_depth_model",
                    "review_status": "Transferred estimate; datum and seismic alignment unverified",
                    "metadata": dict(record, loaded_source_survey_inventory={
                        w: _td_copy.deepcopy(self.ns.get("ml_checkshot_metadata", {}).get(w, {}))
                        for w in names_loaded}),
                }]}
        exact_scope = ("eo-1" in names and len(ranges) == 1
                       and next(iter(ranges)) == tuple(record["interval_MDKB_m"]))
        if not direct_td and not (image_request and exact_scope):
            return self.base.ask(question)
        if "eo-1" not in names or len(ranges) != 1:
            return {"answer": "Specify eo-1 and one MDKB interval in metres. "
                    "The supplied conditional candidates cover " + scope + ".", "action": "clarify"}
        if _td_re.search(r"\b(?:m|metres?|meters?)\s+(?:TVDSS|TVDKB|MDSS)\b", question, _td_re.I):
            return {"answer": "These candidates use MDKB interval boundaries. "
                    "An explicitly TVDSS/TVDKB/MDSS range cannot be substituted for them.", "action": "clarify"}
        donors = {d["well"] for d in record["IDW_donors"]}
        if set(names) - ({"eo-1"} | donors):
            return {"answer": "This transfer review supports eo-1 and its supplied donor wells. "
                    "Request other target wells separately.", "action": "unsupported"}
        if not exact_scope:
            return {"answer": "The supplied T/D candidates cover " + scope + " only. "
                    "Generate and review candidates for the other interval first.", "action": "clarify"}
        if explicit:
            loaded = int(self.ns["ml_seismic_metadata"]["inline_id"])
            if explicit != {loaded}:
                return {"answer": f"Only inline {loaded} is loaded; no other inline was assessed.", "action": "unsupported"}
        return self._review_td_transfer(question, include_image=image_request)

    def _review_td_transfer(self, question, include_image=False):
        td = self._candidate_record()
        top, bottom = td["interval_MDKB_m"]
        well = self.base._well_record("eo-1", top, bottom)
        refs = self.base._retrieve_references(question)
        packet = {"W1": well, "T1": td, "public_references": refs}
        required = ["W1", "T1"]
        png, metadata = None, None
        if include_image:
            metadata, png = self.base._seismic_snapshot()
            packet["S1"] = metadata
            required.append("S1")
        text = ("QUESTION:\n" + question + "\nSUPPLIED EVIDENCE:\n" +
                _td_json.dumps(packet, indent=2, allow_nan=False) +
                "\nPython will prepend the well-statistics and conditional-T/D tables. "
                "Do not repeat numerical sample counts, percentages, T/D values, weights or errors in prose. "
                "Briefly acknowledge the supplied well-property evidence [W1], then focus on the conditional model [T1]. "
                "Explain the comparison, uncertainty and next investigations. About 300 words. " +
                ("A current seismic image is supplied; cite [S1] for image observations." if png else
                 "No seismic image was supplied. Do not make new seismic image observations."))
        content = [{"type": "text", "text": text}]
        if png:
            content.append({"type": "image_url", "image_url": {
                "url": "data:image/png;base64," + _td_base64.b64encode(png).decode("ascii")}})
        instructions = self.ns["_EC_INSTRUCTIONS"] + "\n" + _TD_RULES

        def issues(answer):
            problems = self.ns["_ec_group_percentage_issues"](answer, well)
            problems += self.ns["_ec_reference_issues"](
                answer, refs, self.ns["_ec_reference_requested"](question), required)
            cited = _td_citations(answer)
            allowed = set(required) | {r["evidence_id"] for r in refs}
            problems += [f"Citation [{item}] was not supplied." for item in sorted(cited - allowed)]
            problems += [f"Cite supplied [{item}]." for item in required if item not in cited]
            if not _td_re.search(r"\b(?:conditional|provisional|estimated|transferred)\b", answer, _td_re.I):
                problems.append("Identify the transferred time-depth model as conditional or provisional.")
            if not _td_re.search(r"\b(?:datum|time reference|time[- ]zero)\b", answer, _td_re.I):
                problems.append("Explain that the time reference/datum remains unverified.")
            if _td_re.search(r"\b(?:time )?datum\s+(?:is|has been)\s+(?:confirmed|verified)\b", answer, _td_re.I):
                problems.append("The supplied TWT datum has not been verified.")
            return list(dict.fromkeys(problems))

        answer, finish = self.base._request(instructions, content)
        initial = issues(answer)
        remaining = list(initial)
        revision_error = None
        if initial:
            correction = _td_copy.deepcopy(content)
            correction[0]["text"] += ("\nCORRECT THE FOLLOWING DRAFT ISSUES:\n" +
                                      "\n".join(initial) + "\nUse only supplied evidence and citations.")
            try:
                answer, finish = self.base._request(instructions, correction)
                remaining = issues(answer)
            except Exception as error:
                revision_error = type(error).__name__
        draft = answer
        if remaining:
            answer = "**Narrative withheld [" + ", ".join(required) + "]:** evidence checks still need review. "
            answer += "The calculated tables below retain their source status."
        facts = self.ns["_ec_well_fact_table"](well) + "\n\n" + _td_fact_table(td)
        answer = facts + "\n\n" + answer
        flags = self.ns["_ec_quality_flags"](answer, finish, [i for i in required if i != "T1"])
        flags += remaining
        if finish == "length" and "The model response reached its token limit and may be incomplete." not in flags:
            flags.append("The model response reached its token limit and may be incomplete.")
        sources = [well, {
            "evidence_id": "T1", "evidence_type": "conditional_time_depth_model",
            "review_status": "Transferred estimate; time datum and seismic alignment unverified",
            "metadata": td,
        }]
        if png:
            seismic_source = {
                "evidence_id": "S1", "evidence_type": "Rendered seismic image with unreviewed AI assessment",
                "metadata": metadata, "source_file": metadata["source_file"],
                "image_sha256": _td_hashlib.sha256(png).hexdigest(),
                "review_status": "Unreviewed AI visual assessment",
                "observation_text": answer, "model": self.base.model, "finish_reason": finish,
                "assessment_scope": "W1 and conditional T1; no verified time-depth tie",
            }
            sources.append(seismic_source)
            self.ns["ml_seismic_observation_record"] = _td_copy.deepcopy(seismic_source)
            self.ns.setdefault("ml_seismic_observation_history", []).append(_td_copy.deepcopy(seismic_source))
        sources += self.base._reference_sources(refs, answer)
        result = {"answer": answer, "action": "review_td_transfer", "sources": sources,
                  "evidence": packet, "finish_reason": finish, "quality_flags": flags,
                  "arguments": {"well_id": "eo-1", "top_m": top, "bottom_m": bottom},
                  "evidence_qc": {"status": "withheld" if remaining else "passed_scoped_checks",
                      "scope": "Supplied citations, local group percentages and explicit conditional/datum language; not all numbers or geological claims",
                      "revision_attempts": int(bool(initial)), "initial_issues": initial,
                      "remaining_issues": remaining}}
        if revision_error:
            result["evidence_qc"]["revision_error"] = revision_error
        if remaining:
            result["withheld_model_draft"] = draft
        if png:
            result["_image_png"] = png
        self.ns["ml_last_td_review"] = _td_copy.deepcopy(result)
        return result

    def show_ui(self):
        import ipywidgets as widgets
        import pandas as pd
        from html import escape
        from IPython.display import display, HTML, Markdown

        td = self._candidate_record()
        top, bottom = td["interval_MDKB_m"]
        question = widgets.Textarea(
            value=f"Using eo-1 from {top:g} to {bottom:g} m, compare the nearest and IDW time-depth estimates. What remains uncertain?",
            rows=3, layout=widgets.Layout(width="100%"))
        ask = widgets.Button(description="Ask Copilot", button_style="primary", icon="paper-plane")
        clear = widgets.Button(description="Clear display", icon="trash")
        status = widgets.Label(value="Ready")
        box_layout = widgets.Layout(width="100%", min_width="0px", height="auto",
                                    max_height="650px", overflow="auto", padding="10px", flex="0 0 auto")
        chat, evidence = widgets.Output(layout=box_layout), widgets.Output(layout=widgets.Layout(
            width="100%", min_width="0px", height="auto", max_height="650px", overflow="auto", padding="10px"))
        view = widgets.Image(value=self.ns["ml_seismic_png"], format="png", layout=widgets.Layout(width="100%"))
        tabs = widgets.Tab(children=[chat, evidence, view], layout=widgets.Layout(width="100%", min_width="0px"))
        for i, label in enumerate(("Conversation", "Latest evidence", "Loaded seismic view")):
            tabs.set_title(i, label)

        def render_turn(text, reply):
            with chat:
                display(HTML("<p><b>You:</b> " + escape(text) + "</p>"))
                display(Markdown("**Copilot:**\n\n" + reply.get("answer", "No answer returned.")))
                for flag in reply.get("quality_flags", []):
                    print("QC flag:", flag)
                for source in self.base._sources(reply):
                    print(f"[{source.get('evidence_id', 'W1')}] {source.get('review_status', 'Provisional')}")
                    if source.get("source_url"):
                        display(HTML('<a target="_blank" rel="noopener noreferrer" href="' +
                                     escape(source["source_url"], quote=True) + '">' + escape(source["source_url"]) + '</a>'))
                display(HTML("<hr>"))

        def render_evidence(reply):
            evidence.clear_output()
            with evidence:
                if reply.get("evidence_qc"):
                    print("Evidence checks:", _td_json.dumps(reply["evidence_qc"], indent=2))
                for source in self.base._sources(reply):
                    print("\n[" + source.get("evidence_id", "W1") + "]", source.get("review_status", "Provisional"))
                    if "groups" in source:
                        print("Depth reference:", source.get("depth_reference"))
                        display(pd.DataFrame(source["groups"]))
                        print("Source:", source.get("source_file"))
                    elif source.get("evidence_type") == "public_reference":
                        print(source["title"], "\n", source["text"], "\n", source["scope"])
                        print("Text relevance, not geological confidence:", source.get("text_retrieval_score_not_geological_confidence"))
                    else:
                        print(_td_json.dumps(source.get("metadata", source), indent=2, allow_nan=False))
                        if source.get("image_sha256"):
                            print("Image SHA256:", source["image_sha256"])

        def on_ask(_):
            text = question.value.strip()
            if not text:
                status.value = "Enter a question."
                return
            ask.disabled = clear.disabled = question.disabled = True
            status.value = "Reviewing the supplied evidence..."
            try:
                reply = self.ask(text)
                self.history.append({"question": text, "reply": reply})
                render_turn(text, reply)
                render_evidence(reply)
                if reply.get("_image_png"):
                    view.value = reply["_image_png"]
                status.value = "Response complete. Review the evidence and its status."
            except Exception as error:
                with chat:
                    print("Request failed:", type(error).__name__, str(error))
                status.value = "Request failed; see the message above."
            finally:
                ask.disabled = clear.disabled = question.disabled = False

        def on_clear(_):
            chat.clear_output()
            evidence.clear_output()
            self.history.clear()
            status.value = "Display cleared."

        ask.on_click(on_ask)
        clear.on_click(on_clear)
        loaded = int(self.ns["ml_seismic_metadata"]["inline_id"])
        banner = ("<h3>Exploration Copilot</h3><p>Well properties, seismic review and conditional time-depth transfer. "
                  f"Loaded inline: {loaded}. T/D candidates: eo-1, {top:g}–{bottom:g} m MDKB. "
                  "Transferred times remain conditional; the common time datum is unverified.</p>")
        self.ui = widgets.VBox([widgets.HTML(self.ns.get("_EC_TABLE_STYLE", "") + banner),
                               question, widgets.HBox([ask, clear]), status, tabs],
                              layout=widgets.Layout(width="100%", min_width="0px", height="auto"))
        self.ui.add_class("ec-copilot-readable")
        old_ui = self.ns.get("ml_chat_ui")
        if old_ui is not None:
            old_ui.close()
        self.ns["ml_chat_ui"] = self.ui
        for item in self.history:
            render_turn(item.get("question", ""), item.get("reply", {}))
        if self.history:
            render_evidence(self.history[-1].get("reply", {}))
        display(self.ui)
        return self.ui


def install_td_transfer_chat(namespace, show_ui=True):
    missing = [name for name in ("ml_copilot_extension", "ml_eo1_td_candidates", "ml_depth_reference_by_well",
               "_EC_INSTRUCTIONS", "_ec_well_fact_table", "_ec_metre_ranges", "_ec_explicit_inlines",
               "_ec_group_percentage_issues", "_ec_reference_issues", "_ec_reference_requested",
               "_ec_quality_flags") if name not in namespace]
    if missing:
        raise RuntimeError("Run the existing Copilot and candidate-building cells first. Missing: " + ", ".join(missing))
    base = namespace["ml_copilot_extension"]
    while getattr(base, "_td_transfer_extension", False):
        base = base.base
    app = TDTransferChatExtension(namespace, base)
    namespace.update(ml_copilot_extension=app, ml_ask=app.ask,
                     ml_review_td_transfer_chat=app.ask,
                     ml_chat_log=app.history, ml_td_chat_installed=True)
    if show_ui:
        app.show_ui()
    print("Installed conditional T/D review [T1]. Existing well, seismic and reference tools remain available.")
    print("Installation made no model request. No time-depth model was applied to DUG or seismic.")
    return app


if __name__ == "__main__":
    install_td_transfer_chat(globals())


# TD_REASONING_REFINEMENT_V1
_TD_RULES += "\nTIME-DEPTH METHOD CLARIFICATIONS:\nExplain the complete calculation: MDKB is mapped to TVDSS using the exported\npath; each donor's exported TWT is interpolated at those TVDSS depths; the\nnearest candidate uses one donor alone and IDW blends the two selected donors.\nPath interpolation alone does not produce the time estimates.\nUse nearest_source_wells, IDW_source_wells and shared_source_wells when supplied.\nThe nearest candidate does not use every donor used by IDW. Their common donor\ncontributes shared information, so they are not independent validations.\nThe location triangle uses ALL THREE calibration source wells, not the two\nselected IDW donors. Name that set or explicitly say three calibration wells.\nDistinguish spatial/geographic transfer outside this triangle from interpolation\nWITHIN the donor TVDSS coverage. Never imply that depth extrapolation occurred\nwhen depth_extrapolation_performed is false. Map location alone does not measure\nthe target error. Name the ranking criterion: overall mean MAE can favour IDW\nwhile nearest wins more individual wells or has lower highest-per-well MAE.\nDo not imply IDW wins every well or depth band. Use the supplied per-well winners\nand validation data. Target checkshot/VSP recommendations must identify eo-1;\nthe source-well surveys are already supplied. Such calibration constrains time\nversus depth; it does not by itself validate lithology or amplitude response.\n"
