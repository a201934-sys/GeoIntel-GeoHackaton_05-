# Prototype model and evidence card

**Purpose:** assist geoscientists in comparing evidence and investigation
priorities, with human review of geological interpretations.

**Well model:** unsupervised K-means using VSH and PHIT. Feature scaling and
clustering use training-well data. The working implementation splits by well
and balances training samples across wells. Cluster numbers are arbitrary
property-group identifiers, not geological labels or accuracy scores.

**Language model:** the configured internal multimodal endpoint. It explains
supplied evidence and does not supply missing measurements. Well counts and
conditional T/D tables are calculated in Python.

**Time-depth experiment:** original imported source surveys, as reported by the
user; MDKB, TVDSS and TWT kept distinct. The incomplete tail of one source export
was excluded from an experimental copy, preserving its original rows. A common
depth grid and equal well weighting prevent a densely exported source from
dominating validation. Method selection remains exploratory with three wells.

**Geographical context:** the target is outside the three-calibration-well
triangle in map view. TWT values were interpolated within source depth coverage.
The nearest method uses one source; IDW shares it and adds another.

**Controls:** exact well/interval/current-image scope; source IDs and links;
explicit unsupported/missing-input behavior; bounded draft correction; no
automatic claim that a numerical/citation check validates geological truth.

**Not established:** independent lithology accuracy, target-well transfer error,
calibrated confidence intervals, verified seismic tie, trap closure or commercial
prospect ranking. No measured productivity improvement has yet been established.
