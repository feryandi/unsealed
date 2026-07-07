#version 330 core
in vec3 vFragPos;
in vec3 vNormal;
in vec2 vTexCoord;

uniform vec3  uLightDir;
uniform vec3  uViewPos;
uniform bool  uHasTexture;
uniform sampler2D uTexture;
uniform vec4  uBaseColor;

out vec4 fragColor;

void main() {
    vec3 norm     = normalize(vNormal);
    vec3 lightDir = normalize(-uLightDir);

    float ambient = 0.60;
    float diff    = max(dot(norm, lightDir), 0.0) * 0.40;
    float light   = ambient + diff;

    vec4 base;
    if (uHasTexture) {
        vec4 texColor = texture(uTexture, vTexCoord);
        base = texColor * uBaseColor;

        if (base.a < 0.05)
            discard;
    } else {
        base = uBaseColor;
    }

    fragColor = vec4(clamp(light, 0.0, 1.0) * base.rgb, base.a);
}