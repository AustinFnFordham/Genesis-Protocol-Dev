// GENESIS//OS Tauri shell.
// Commands are the ONLY bridge between the deterministic backend and the UI:
//   load_registry  -> reads the Gold sandbox from disk, returns the boot payload
//   load_portrait  -> Master Reference Anchor contract (identity_constants -> anchor)
//   comfy_inpaint  -> identity-locked gear inpaint contract (SAM mask + gear_variables)
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

const SANDBOX: &str = r"E:\StarWars\SW5e_Data_Hub\forge_v3\data\sandbox_gold";
const ANCHOR_DIR: &str = r"E:\StarWars\app\genesis-os\anchors";
const COMFY_URL: &str = "http://localhost:8188";

#[tauri::command]
fn load_registry() -> Result<String, String> {
    let dir = PathBuf::from(SANDBOX);
    let mut registry: BTreeMap<String, serde_json::Value> = BTreeMap::new();
    let mut manifest: Vec<serde_json::Value> = Vec::new();

    for entry in fs::read_dir(&dir).map_err(|e| e.to_string())? {
        let p = entry.map_err(|e| e.to_string())?.path();
        let name = p.file_name().unwrap().to_string_lossy().to_string();
        if !name.ends_with(".sandbox.yml") {
            continue;
        }
        let schema = name.trim_end_matches(".sandbox.yml").to_string();
        let text = fs::read_to_string(&p).map_err(|e| e.to_string())?;
        let doc: serde_json::Value =
            serde_yaml::from_str(&text).map_err(|e| format!("{name}: {e}"))?;
        let urid = doc
            .pointer("/metadata/id")
            .or_else(|| doc.pointer("/id"))
            .and_then(|v| v.as_str())
            .map(String::from)
            .unwrap_or_else(|| format!("sandbox_{}", schema.to_lowercase()));
        let display = doc
            .pointer("/metadata/name")
            .or_else(|| doc.pointer("/name"))
            .and_then(|v| v.as_str())
            .map(String::from)
            .unwrap_or_else(|| schema.clone());
        manifest.push(serde_json::json!({
            "urid": urid, "schema": schema, "tier": "gold", "name": display
        }));
        registry.insert(urid, doc);
    }

    let payload = serde_json::json!({
        "registry": registry, "manifest": manifest,
        "campaign": registry.values().find(|v| v.pointer("/campaign_id").is_some()).cloned().unwrap_or(serde_json::json!({})),
        "pipeline": "Genesis Protocol / Forge V3 / sandbox_gold"
    });
    serde_json::to_string(&payload).map_err(|e| e.to_string())
}

/* ---------- ComfyUI contracts (gap #5 — exact payload structures) ---------- */

/// load_portrait REQUEST: everything needed to fetch-or-generate the Master
/// Reference Anchor. identity_constants are the immutable DNA half.
#[derive(Deserialize, Serialize)]
struct PortraitRequest {
    character_id: String,
    identity_constants: Vec<String>,
    /// existing anchor path from visual_dna.anchor_asset, if any
    anchor_asset: Option<String>,
    /// base style prompt from image_generation.base_prompt, if present
    base_prompt: Option<String>,
    negative_keywords: Option<Vec<String>>,
}

/// load_portrait RESPONSE
#[derive(Serialize)]
struct PortraitResponse {
    status: String,          // "cached" | "generate_queued" | "stub"
    anchor_asset: String,    // resolved or to-be-written path
    comfy_workflow: serde_json::Value, // the exact node graph the ComfyUI POST will carry
}

#[tauri::command]
fn load_portrait(req: PortraitRequest) -> Result<String, String> {
    let anchor_path = req.anchor_asset.clone().unwrap_or_else(|| {
        format!("{}\\{}.png", ANCHOR_DIR, req.character_id)
    });
    let cached = fs::metadata(&anchor_path).is_ok();

    // The contract: txt2img with identity_constants as the locked prompt core.
    // Once generated, EVERY subsequent render references this anchor via
    // IP-Adapter/PuLID — the face never drifts.
    let workflow = serde_json::json!({
        "endpoint": format!("{COMFY_URL}/prompt"),
        "pipeline": "txt2img_anchor",
        "prompt_core": req.identity_constants,
        "style_prompt": req.base_prompt,
        "negative": req.negative_keywords.unwrap_or_default(),
        "identity_lock": { "method": "PuLID", "strength": 0.95 },
        "output": anchor_path,
    });

    let resp = PortraitResponse {
        status: if cached { "cached".into() } else { "stub".into() },
        anchor_asset: anchor_path,
        comfy_workflow: workflow,
    };
    serde_json::to_string(&resp).map_err(|e| e.to_string())
}

/// comfy_inpaint REQUEST: gear swap. mask coords are NORMALIZED (0..1) in the
/// WebGPU viewport so the same rectangle works at any canvas resolution;
/// the Rust side multiplies by anchor resolution before SAM.
#[derive(Deserialize, Serialize)]
struct InpaintRequest {
    character_id: String,
    anchor_asset: String,
    /// the mutable DNA half — ONLY these strings drive the inpaint prompt
    gear_variables: Vec<String>,
    environment_context: Option<Vec<String>>,
    /// normalized viewport rect the player's gear change affects (SAM seed region)
    mask: MaskRect,
}

#[derive(Deserialize, Serialize)]
struct MaskRect {
    x: f64, // 0..1, left
    y: f64, // 0..1, top
    w: f64, // 0..1
    h: f64, // 0..1
    /// segmentation hint: "torso" | "head" | "arms" | "legs" | "weapon" | "auto"
    region_hint: String,
}

#[derive(Serialize)]
struct InpaintResponse {
    status: String, // "queued" | "stub"
    comfy_workflow: serde_json::Value,
}

#[tauri::command]
fn comfy_inpaint(req: InpaintRequest) -> Result<String, String> {
    let workflow = serde_json::json!({
        "endpoint": format!("{COMFY_URL}/prompt"),
        "pipeline": "sam_inpaint_identity_locked",
        "anchor": req.anchor_asset,
        "identity_lock": { "method": "IP-Adapter+PuLID", "strength": 0.95, "note": "face/identity region EXCLUDED from mask" },
        "sam": { "seed_rect_normalized": req.mask, "hint": req.mask.region_hint },
        "inpaint_prompt": req.gear_variables,
        "environment": req.environment_context.unwrap_or_default(),
        "denoise": 0.72
    });
    let resp = InpaintResponse { status: "stub".into(), comfy_workflow: workflow };
    serde_json::to_string(&resp).map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![load_registry, load_portrait, comfy_inpaint])
        .run(tauri::generate_context!())
        .expect("error while running GENESIS//OS");
}
