// Headless creator QA: assemble the exact document the wizard builds and run
// it through the same Ajv guardrail. Run: node qa_creator.mjs
import Ajv from 'ajv';
import { readFileSync } from 'fs';

const charSchema = JSON.parse(readFileSync('public/Character.schema.json', 'utf8'));
const ccfSchema = JSON.parse(readFileSync('public/CharacterClassFeature.schema.json', 'utf8'));

const ajv = new Ajv({ strict: false, allErrors: true });
ajv.addSchema(ccfSchema, 'CharacterClassFeature.schema.json');
const validate = ajv.compile(charSchema);

const doc = {
  id: 'character_rrawrkhal',
  name: 'Rrawrkhal',
  era: 'Galactic_Empire',
  rarity: 'unique',
  narrative: 'A Wookiee Guardian shaped by a Noble past, walking the balanced path.',
  description: 'russet fur with silver streaks, scar across left brow, amber eyes',
  species_id: 'wookiee',
  background_id: 'background_noble',
  game_mode: { mode_id: 'mode_standard', xp_multiplier: 1, out_of_class_xp_penalty: 1 },
  level: 1,
  xp: 0,
  ability_scores: { strength: 14, dexterity: 10, constitution: 12, intelligence: 10, wisdom: 10, charisma: 10 },
  moral_compass: { morality: 50, alignment: 'balanced', conflict: 0 },
  tags: ['tag_player_character', 'tag_species_wookiee'],
  features: ['subclass_guardian_protector'],
  equipment: ['worn traveler jacket', 'holstered blaster'],
  visual_dna: {
    identity_constants: ['russet fur with silver streaks', 'scar across left brow', 'amber eyes'],
    gear_variables: ['worn traveler jacket', 'holstered blaster'],
    environment_context: ['character creation chamber, blue holo-light'],
  },
  llm_guidance: { roleplay_guidance: 'Alignment balanced (50/100). Honor the Noble background in social scenes.' },
  image_generation: { base_prompt: 'cinematic portrait of a Wookiee Guardian, Star Wars concept art' },
  ui: { color: '#4FC3F7' },
};

const pass = validate(doc);
if (pass) {
  console.log('GUARDRAIL: PASS — character_rrawrkhal is Character.schema-valid (zero violations)');
} else {
  console.log('GUARDRAIL: REJECTED');
  for (const e of validate.errors.slice(0, 10)) console.log(' ', e.instancePath || '/', e.message);
  process.exit(1);
}
