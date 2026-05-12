#version 330 core
in vec2 vUv;   // layer_a UV (rotated)
in vec2 vUv2;  // layer_b UV (original)
out vec4 fragColor;

uniform sampler2D uTextures[12];
uniform sampler2D uLightmap;
uniform bool      uHasLightmap;
uniform int       uLayerA[64];
uniform int       uLayerB[64];

// Safe per-slot sampling to avoid dynamic sampler-array indexing.
// Index 0 and anything outside 1-12 fall back to textures[0] (matches viewer.js).
vec4 sampleTex(int idx, vec2 uv) {
    if (idx ==  1) return texture(uTextures[ 0], uv);
    if (idx ==  2) return texture(uTextures[ 1], uv);
    if (idx ==  3) return texture(uTextures[ 2], uv);
    if (idx ==  4) return texture(uTextures[ 3], uv);
    if (idx ==  5) return texture(uTextures[ 4], uv);
    if (idx ==  6) return texture(uTextures[ 5], uv);
    if (idx ==  7) return texture(uTextures[ 6], uv);
    if (idx ==  8) return texture(uTextures[ 7], uv);
    if (idx ==  9) return texture(uTextures[ 8], uv);
    if (idx == 10) return texture(uTextures[ 9], uv);
    if (idx == 11) return texture(uTextures[10], uv);
    if (idx == 12) return texture(uTextures[11], uv);
    return texture(uTextures[0], uv);  // fallback to first texture (matches viewer.js)
}

void main() {
    // Tile the detail textures 128× across the terrain.
    // Both layers share one UV and one tile index — viewer.js createGround().
    // vUv = (x/511, z/511), matches viewer.js's vUv after its vertex y-flip.
    vec2 uv1  = fract(vUv * 128.0);
    int  tile = clamp(int(floor(vUv.y * 8.0)) * 8 + int(floor(vUv.x * 8.0)), 0, 63);

    vec4 terrain = sampleTex(uLayerB[tile], uv1);
    vec4 path    = sampleTex(uLayerA[tile], uv1);

    vec3 color;
    if (uHasLightmap) {
        // Lightmap: original UV (360° = no rotation)
        vec2 lm_uv = vUv2;
        vec4 lm = texture(uLightmap, lm_uv);

        // Matches viewer.js createGround() fragment shader exactly.
        vec3 combined_path    = mix(path.rgb, lm.rgb,
                                    lm.a + (path.rgb * (1.0 - lm.a)) / 1.5);
        vec3 combined_terrain = mix(terrain.rgb, combined_path,
                                    vec3(1.0 - lm.a) + (terrain.rgb * lm.a) / 1.5);
        color = combined_terrain;
    } else {
        color = mix(terrain.rgb, path.rgb, 0.3);
    }

    // viewer.js: mix(combined_terrain * 1.25, mix(vec4(1), combined_terrain, 2.25), 0.5)
    vec3 combined = mix(color * 1.25, mix(vec3(1.0), color, 2.25), 0.5);
    fragColor = vec4(clamp(combined, 0.0, 1.0), 1.0);
}
