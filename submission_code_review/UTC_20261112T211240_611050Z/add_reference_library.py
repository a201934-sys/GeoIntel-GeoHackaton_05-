"""Six curated public geology notes and local text retrieval for the HPC notebook.

Run: %run -i add_reference_library.py
No network access, model requests, challenge-file reads or file writes.
This prepares reference retrieval; it does not yet change the Copilot router.
The notes are paraphrases of the linked pages, not full geological reports.
Field cases illustrate mechanisms; they are not validated matches to eo-1.
"""

import copy as _ref_copy
import math as _ref_math
import re as _ref_re
from collections import Counter as _RefCounter


ml_reference_cards = [
    {
        "evidence_id": "R1", "kind": "concept", "title": "Trap geometry and sealing",
        "source_url": "https://glossary.slb.com/en/terms/t/trap",
        "source_locator": "SLB Energy Glossary: trap, geology definition",
        "text": (
            "A petroleum trap combines a rock configuration capable of containing hydrocarbons "
            "with an effective sealing boundary. Structural types involve deformation such as "
            "folds and faults; stratigraphic types involve changes in rock relationships, including "
            "unconformities, pinch-outs and reefs."
        ),
        "keywords": "structural trap fault fold geometry seal closure",
        "scope": "General concept; no prospect geometry, reservoir or seal is established by this note.",
    },
    {
        "evidence_id": "R2", "kind": "concept", "title": "Stratigraphic trapping mechanisms",
        "source_url": "https://glossary.slb.com/en/terms/s/stratigraphic_trap",
        "source_locator": "SLB Energy Glossary: stratigraphic trap",
        "text": (
            "Stratigraphic containment can arise from lithological changes, sedimentary features, "
            "pinch-outs or unconformities. Its trapping geometry differs from containment created "
            "by deformation of strata, as in fault or fold structures."
        ),
        "keywords": "stratigraphic stratigraphy pinchout pinch-out unconformity lithology sedimentary facies termination",
        "scope": "General concept; changing reflector continuity alone does not validate a prospect-specific pinch-out.",
    },
    {
        "evidence_id": "R3", "kind": "concept", "title": "Synthetic seismogram and well-to-seismic tie",
        "source_url": "https://glossary.slb.com/terms/s/synthetic_seismogram",
        "source_locator": "SLB Energy Glossary: synthetic seismogram",
        "text": (
            "A synthetic seismic response is modelled by combining a wavelet with reflectivity "
            "derived from acoustic and density logs. Checkshot or VSP first-arrival information "
            "commonly calibrates the acoustic log. The match depends on log quality, seismic "
            "processing and the suitability of the wavelet."
        ),
        "keywords": "well seismic tie sonic density acoustic calibration wavelet checkshot VSP time depth synthetic",
        "scope": "Requirements only; this note supplies no missing logs, checkshots, wavelet or time-depth relationship.",
    },
    {
        "evidence_id": "R4", "kind": "concept", "title": "Seismic processing and image positioning",
        "source_url": "https://glossary.slb.com/terms/s/seismic_processing",
        "source_locator": "SLB Energy Glossary: seismic processing",
        "text": (
            "Seismic processing aims to reduce noise, improve signal and position reflected "
            "events appropriately. Operations can include velocity analysis, static correction, "
            "deconvolution, stacking and migration. These operations influence the image used "
            "for geological interpretation."
        ),
        "keywords": "seismic processing imaging artifact artefact migration velocity noise diffraction",
        "scope": "General processing background; no specific artefact or processing failure is diagnosed here.",
    },
    {
        "evidence_id": "A1", "kind": "field_case", "title": "Statfjord: fault-block reservoir example",
        "source_url": "https://www.norskpetroleum.no/en/facts/field/statfjord/",
        "source_locator": "Norwegianpetroleum.no: Statfjord, Reservoir section",
        "text": (
            "Statfjord in the northern North Sea contains Jurassic sandstone reservoirs in "
            "the Brent and Statfjord groups and Cook Formation. The reservoirs occupy a main "
            "west-tilted fault block and smaller fault blocks on its eastern side."
        ),
        "keywords": "Statfjord field analogue analog structural fault block tilted sandstone Jurassic North Sea",
        "scope": (
            "Illustrative fault-block comparison. A match to this prospect requires independent "
            "evidence for geometry, reservoir age/facies and basin setting; these similarities "
            "have not been established for eo-1."
        ),
    },
    {
        "evidence_id": "A2", "kind": "field_case", "title": "East Texas: unconformity-related reservoir example",
        "source_url": "https://www.beg.utexas.edu/publications/274",
        "source_locator": "Hentz (editor), 2010, BEG Report of Investigations 274, public abstract",
        "text": (
            "At East Texas field, Woodbine reservoir strata dip west and are cut by an angular "
            "unconformity on the Sabine Uplift flank. Low-permeability calcareous siltstones "
            "within the Austin Chalk provide the top seal described in the study."
        ),
        "keywords": "East Texas field analogue analog stratigraphic unconformity truncation Woodbine reservoir seal",
        "scope": (
            "Illustrative unconformity-related comparison. It supplies no evidence that an "
            "equivalent reservoir, truncation, age, depositional setting or seal occurs at eo-1."
        ),
    },
]

_REF_STOPWORDS = set("a an and are as at be by can could for from in is it of on or "
                     "that the their these this to using was were what which with would "
                     "compare comparison explain based please".split())
_REF_WORDS = {"faults":"fault", "folds":"fold", "blocks":"block", "traps":"trap",
              "trapping":"trap", "analogues":"analogue", "analog":"analogue",
              "analogs":"analogue", "fields":"field", "artefacts":"artefact",
              "artifacts":"artefact", "artifact":"artefact"}


def _ref_tokens(text):
    return [_REF_WORDS.get(word, word) for word in _ref_re.findall(r"[a-z0-9]+", str(text).lower())
            if word not in _REF_STOPWORDS]


def ml_search_references(question, top_k=3, kind=None):
    """TF-IDF/cosine text retrieval, not geological similarity or probability.

    kind may be 'concept', 'field_case', or None. Returns positive text matches
    with stable evidence IDs, original public links and comparison limitations.
    It never claims a case is a validated analogue of the current prospect.
    """
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError("top_k must be a positive integer.")
    if kind not in (None, "concept", "field_case"):
        raise ValueError("kind must be concept, field_case, or None.")
    query = _RefCounter(_ref_tokens(question))
    if not query:
        return []
    docs = [_RefCounter(_ref_tokens(card["title"] + " " + card["text"] + " " + card["keywords"]))
            for card in ml_reference_cards]
    df = _RefCounter(word for doc in docs for word in doc)
    idf = {word: _ref_math.log((len(docs) + 1) / (count + 1)) + 1 for word, count in df.items()}
    query_weights = {word: count * idf[word] for word, count in query.items() if word in idf}
    query_norm = _ref_math.sqrt(sum(value ** 2 for value in query_weights.values()))
    if query_norm == 0:
        return []
    ranked = []
    for card, doc in zip(ml_reference_cards, docs):
        if kind is not None and card["kind"] != kind:
            continue
        weights = {word: count * idf[word] for word, count in doc.items()}
        norm = _ref_math.sqrt(sum(value ** 2 for value in weights.values()))
        score = sum(weights.get(word, 0) * value for word, value in query_weights.items()) / (norm * query_norm)
        if score > 0:
            result = _ref_copy.deepcopy(card)
            result["text_retrieval_score_not_geological_confidence"] = round(score, 6)
            ranked.append((score, card["evidence_id"], result))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in ranked[:top_k]]


if __name__ == "__main__":
    print(f"Loaded {len(ml_reference_cards)} curated public reference cards, including two field cases.")
    print("Reference search is ready; these cards are not yet connected to the Copilot chat.")
    print("Search scores measure text relevance, not geological confidence or a validated field match.")

