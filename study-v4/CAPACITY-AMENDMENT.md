# Prospective inference-capacity amendment

The first v4 run, v4-calibration-001, hit its predeclared 300-second local deadline
on its first invocation. There was no complete candidate, no evaluation and no
score. The run stopped under its original rule. Its exact original native
session, invocation/events and original frozen source bytes are preserved.

Before a new model invocation, authorize a separate capacity-calibration run with
600 seconds per call, at most two completed attempts, max reasoning, no tools,
zero automatic retries, unchanged inputs, fixtures, evaluator and thresholds.
All stopping conditions and the single feedback-repair rule remain unchanged.
The CLI records the selected cap in run-config.json and every invocation record.
The original 300-second result remains unscored; it is never folded into a 600-
second score. A 600-second success cannot be reported as a 300-second success.

This amendment tests adequate inference capacity only. It does not relax a
functional criterion, demonstrate task difficulty, establish improvement from
the incomplete run, or turn these probes into formal runner-native trajectories.
