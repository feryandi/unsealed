#version 330 core
in vec2 vUV;

uniform sampler2D uTexture;
uniform bool uHasTexture;
uniform vec4 uBaseColor;

out vec4 fragColor;

void main() {
    vec4 col = uHasTexture ? texture(uTexture, vUV) : uBaseColor;
    if (col.a < 0.05) discard;
    fragColor = vec4(col.rgb, 1.0);
}
