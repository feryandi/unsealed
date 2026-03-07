#version 330 core
in vec2 vTexCoord;

uniform sampler2D uTexture;
uniform bool      uHasTexture;
uniform vec4      uBaseColor;

out vec4 fragColor;

void main() {
    vec4 color = uHasTexture ? texture(uTexture, vTexCoord) : uBaseColor;
    // Do not discard on alpha: glow/additive textures encode brightness in RGB with
    // alpha = 0 everywhere.  Black fragments contribute nothing with GL_ONE blending
    // anyway, so discarding on alpha would silently kill the entire glow billboard.
    fragColor = color;
}
