# DeepArk Topic Context v0.1.0

Status: development candidate; not installed or enabled in production.
Target: AstrBot 4.29.3 / Python 3.12.15.

## Behavior

The semantic classifier labels bounded batches as main, candidate, aside or noise.
Only validated responses for observed message IDs can update state. Topic labels
are model hypotheses, not facts. New topics normally require 3 supporting messages
from at least 2 people, or 4 from one person, within a 120-second evidence window
and at least 60% of the last 6 classifications. Busy main discussions require one
additional supporting message. A single explicit mention does not switch topics.

Main-topic participant count and message rate determine a heuristic idle tolerance
(90-900 seconds), context text budget (1200-6000 characters), and aside allocation.
These are bounded heuristics, not statistically calibrated duration predictions.
Short asides remain in a reserved part of the context; explicit requests get first
priority. Matching an earlier aside to the main discussion is the classifier's job.

Per-message input is capped at 1000 characters; at most 96 messages per session,
8 pending messages per classifier call, 16 recent classified context messages.
Overflow pending messages become asides rather than being replayed as old switches.
The cache has a configurable LRU bound (default 64, hard maximum 256 sessions) and
lazy expiry after 30 idle minutes. Nothing is persisted; restart loses this cache.

Classifier calls use an explicitly configured provider, at most once per 10 seconds
per group by default, 60/hour per group and a hard global 120/hour. At most two
calls run concurrently; each has a 5-second timeout. Failures do not force a switch.
No classifier calls occur with default settings. Enabled real use can incur model
costs; this delivery only tests a fake provider. Semantic accuracy needs separately
agreed model evaluation; fake-provider tests verify mechanics, not model accuracy.

## Configuration and integration

`enabled=false`, `allowed_sessions=[]`, `classifier_provider_id=""` by default.
Enable only in an approved environment, supply exact group UMOs and the configured
classifier provider ID. AstrBot native group whitelist, provider, session and plugin
permissions must also allow access. Direct @/wake status is captured before
companion turns an unsolicited message into a wake event.

The optional companion bridge supplies dynamic context to participation decisions
and removes duplicate companion human-history injection when a topic snapshot is
available. Without the new plugin, without an established topic, or on bridge
failure, the original companion path remains. It does not alter companion budgets,
permission gates, bot-reply freshness checks, output checks, or outbound transport.
Other plugins and SDK tool-call histories retain their own context ownership; this
plugin does not claim to bound the entire model request or all plugins' memory.

The final prompt adapts the response to the topic while preserving persona and
sender identity. It requests silence for unrelated unsolicited interruptions;
final language-model behavior is not a deterministic guarantee. This plugin does
not autonomously send messages or start a scheduler. Existing companion decides
when to participate. It honors `/deepark 忘记...` and `/lmem...` by clearing its
transient group cache; this does not delete another plugin's memory.

## Offline acceptance

From the checkout root using the isolated Python environment:

```sh
python3 -m unittest discover -s tests/unit -v
python -m unittest discover -s tests/integration -t . -v
git diff --check
```

The integration suite requires the real SDK but mocks providers and transport.
Do not start AstrBot, connect NapCat, mount production data, or copy credentials.
Use the synthetic replay tool described in docs/features/TOPIC_CONTEXT.md for
manual inspection. Record `git rev-parse HEAD` with actual results.

## Adoption and rollback

User acceptance and code review precede merging and any separately authorized
release. The plugin is added under its own production plugin directory only during
that release; the companion source change must come from the same reviewed commit.
Keep code/config backups separate from data. No database migration is introduced.
For a later rollback, disable/remove the new plugin and restore the affected
companion code/config from the release backup; do not restore chat databases.
No deployment, restart, real-model benchmark or live QQ validation is included here.
