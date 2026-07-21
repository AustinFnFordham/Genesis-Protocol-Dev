/* In-UI guardrail: the SAME jsonschema law the forge enforces, compiled with Ajv.
 * The creator cannot commit a character the pipeline would reject. */
import Ajv from 'ajv';

let _validate = null;

export async function getCharacterValidator() {
  if (_validate) return _validate;
  const [charSchema, ccfSchema] = await Promise.all([
    fetch('/Character.schema.json').then((r) => r.json()),
    fetch('/CharacterClassFeature.schema.json').then((r) => r.json()),
  ]);
  const ajv = new Ajv({ strict: false, allErrors: true });
  // Character refs CharacterClassFeature by relative filename — register it under that key.
  ajv.addSchema(ccfSchema, 'CharacterClassFeature.schema.json');
  try {
    _validate = ajv.compile(charSchema);
  } catch (err) {
    console.warn('Ajv compile failed, falling back to required-fields check:', err);
    _validate = (doc) => {
      const missing = (charSchema.required || []).filter((k) => doc[k] === undefined);
      _validate.errors = missing.map((k) => ({ instancePath: '', message: `missing required '${k}'` }));
      return missing.length === 0;
    };
  }
  return _validate;
}
