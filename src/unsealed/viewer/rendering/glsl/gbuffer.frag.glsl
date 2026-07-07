#version 330 core
in vec3 vFragPos;
in vec3 vNormal;
in vec2 vTexCoord;

uniform bool      uHasTexture;
uniform sampler2D uTexture;
uniform vec4      uBaseColor;

layout(location = 0) out vec4 gAlbedo;   // RGBA8
layout(location = 1) out vec4 gNormal;   // RGBA16F, normal encoded [0,1]

void main() {
    vec4 base;
    if (uHasTexture) {
        vec4 tex = texture(uTexture, vTexCoord);
        base = tex * uBaseColor;
        // Alpha-test: discard fully-transparent holes (cutouts, fences, foliage, doors).
        // Pixels with 0.05 <= alpha < 1.0 (anti-aliased edges) are treated as opaque here;
        // truly transparent primitives (base_color.a < 1) never reach the G-Buffer pass.
        if (base.a < 0.05) discard;
    } else {
        base = uBaseColor;
    }

    gAlbedo = vec4(base.rgb, 1.0);
    gNormal = vec4(normalize(vNormal) * 0.5 + 0.5, 1.0);
}
