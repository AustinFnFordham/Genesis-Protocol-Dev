"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..", "..");
const fixturePath = path.join(root, "Contracts", "examples", "action-execution-patterns.v0.1.json");
const schemaPath = path.join(root, "Contracts", "schemas", "action-execution-pattern.schema.json");
const catalogPath = path.join(root, "development", "combat_slice", "catalog.json");

const fixture = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
const schema = JSON.parse(fs.readFileSync(schemaPath, "utf8"));
const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));

assert.equal(fixture.schema_version, "acp-001.0.1");
assert.equal(fixture.dataset_status, "noncanonical_fixture");
assert.equal(schema.$schema, "https://json-schema.org/draft/2020-12/schema");
assert.equal(schema.additionalProperties, false);

assert.equal(fixture.projection_policy.ungranted_profile_visibility, "never_in_combat_selector");
assert.equal(fixture.projection_policy.empty_category_behavior, "hide");
assert.match(fixture.projection_policy.category_visibility, /granted/);

const allIds = [
  ...fixture.profiles.map((record) => record.id),
  ...fixture.patterns.map((record) => record.id),
  ...fixture.augmentations.map((record) => record.id)
];
assert.equal(new Set(allIds).size, allIds.length, "record IDs must be unique");

for (const profile of fixture.profiles) {
  for (const field of ["taxonomy", "action_category", "cost", "grant", "prerequisites", "resolution", "source_control"]) {
    assert.ok(Object.hasOwn(profile, field), `${profile.id} separates ${field}`);
  }
  if (["source_gap", "proposed"].includes(profile.status)) {
    assert.notEqual(profile.source_control.approval, "adopted", `${profile.id} cannot silently authorize gameplay`);
  }
}

const byId = new Map(fixture.profiles.map((profile) => [profile.id, profile]));
for (const id of [
  "profile.offhand_blaster_bonus.candidate",
  "profile.offhand_saber_bonus.candidate",
  "profile.echani_flow_bonus.observed_proposal",
  "profile.throw_carried_object_main.candidate"
]) {
  assert.ok(byId.has(id), `required owner-intent profile missing: ${id}`);
}
assert.equal(byId.get("profile.offhand_blaster_bonus.candidate").cost.bonus, 1);
assert.equal(byId.get("profile.offhand_blaster_bonus.candidate").resolution.proficiency.missing_result, "disadvantage");
assert.equal(byId.get("profile.offhand_saber_bonus.candidate").cost.bonus, 1);
assert.equal(byId.get("profile.offhand_saber_bonus.candidate").resolution.proficiency.decision_status, "candidate");
assert.equal(byId.get("profile.echani_flow_bonus.observed_proposal").cost.bonus, 1);
assert.ok(byId.get("profile.throw_carried_object_main.candidate").prerequisites.some((item) => item.kind === "object_instance"));

for (const pattern of fixture.patterns) {
  assert.ok(pattern.steps.length >= 2, `${pattern.id} must compose at least two steps`);
  assert.equal(pattern.promotion.grants_mechanical_bonus, false, `${pattern.id} promotion cannot invent a bonus`);
  assert.ok(pattern.revalidation.length > 0, `${pattern.id} needs live revalidation`);
  assert.ok(Object.keys(pattern.per_actor_cost_forecast).length > 0, `${pattern.id} needs per-actor accounting`);
}

const dual = fixture.patterns.find((item) => item.id === "maneuver.saber_and_offhand_blaster.candidate");
assert.deepEqual(dual.per_actor_cost_forecast["actor:self"].main, 1);
assert.deepEqual(dual.per_actor_cost_forecast["actor:self"].bonus, 1);
assert.equal(new Set(dual.steps.map((step) => step.id)).size, 2);

const team = fixture.patterns.find((item) => item.pattern_kind === "team_maneuver");
assert.ok(team.participants.includes("pc:aero"));
assert.ok(team.participants.includes("pc:varon"));
assert.ok(team.participants.includes("pc:rissa"));
assert.ok(team.participants.some((id) => id.startsWith("pc:togruta")));
assert.ok(new Set(team.steps.map((step) => step.actor_binding)).size >= 2, "team maneuver needs multiple actors");

for (const augmentation of fixture.augmentations) {
  assert.ok(augmentation.target_profile_ids.length > 0, `${augmentation.id} targets named profiles`);
  assert.ok(augmentation.target_components.length > 0, `${augmentation.id} targets named components`);
  assert.ok(augmentation.cost.resources?.some((item) => item.resource_id === "force_points" && item.amount > 0));
  assert.notEqual(augmentation.source_control.approval, "adopted", `${augmentation.id} remains noncanonical`);
}

const reconciliation = new Map(fixture.category_reconciliation.map((item) => [item.capability, item]));
const expectedOwnerCategories = {
  "Dodge Action": "main",
  "Battle Insight": "secondary",
  "Blade Bind & Strip": "maneuver",
  "Lightsaber Strike": "main",
  "Echani Strike": "main",
  "Lightsaber Strike (two-handed)": "main",
  "Blaster Pistol Shot": "main",
  "Echani Grapple": "secondary",
  "Calm the Animal (untrained)": "secondary",
  "Reload Blaster": "secondary",
  "Burst": "secondary",
  "Force Connection (focused)": "secondary",
  "Minor Telekinesis (Jedi Fundamentals)": "bonus",
  "Blade Bind & Takedown": "maneuver",
  "Weapon Feint": "secondary",
  "Readied Dodge": "secondary"
};
for (const [name, category] of Object.entries(expectedOwnerCategories)) {
  assert.equal(reconciliation.get(name)?.owner_category, category, `owner category coverage: ${name}`);
}

// Pin the observations that made this amendment necessary. If Claude's catalog changes,
// this fails so the docs can be reconciled instead of claiming stale coverage.
const observedCatalogCosts = {
  dodge_action: ["main", 1],
  battle_insight: ["main", 1],
  blade_bind: ["main", 1],
  saber_strike: ["main", 1],
  unarmed_strike: ["main", 1],
  saber_strike_2h: ["main", 1],
  blaster_shot: ["main", 1],
  grapple: ["main", 1],
  calm_beast: ["main", 1],
  reload_sidearm: ["main", 1],
  burst: ["main", 1],
  force_connection: ["main", 1],
  minor_telekinesis: ["main", 1],
  feint: ["secondary", 1],
  readied_dodge: ["secondary", 1]
};
for (const [profileId, [resource, amount]] of Object.entries(observedCatalogCosts)) {
  assert.equal(catalog.profiles[profileId]?.cost?.[resource], amount, `catalog observation drift: ${profileId}`);
}
assert.deepEqual(catalog.profiles.controlled_takedown.cost, { main: 1, secondary: 1 });
assert.equal(catalog.profiles.force_augment.cost.fp, 1);
assert.deepEqual(catalog.profiles.force_augment.requires.augments, ["saber_strike", "riposte"]);

console.log(`ACP-001 coverage passed: ${fixture.profiles.length} profiles, ${fixture.patterns.length} patterns, ${fixture.category_reconciliation.length} category rows.`);
