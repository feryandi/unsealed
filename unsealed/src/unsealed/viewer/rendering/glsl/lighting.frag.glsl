#version 330 core
in vec2 vTexCoord;

uniform sampler2D gAlbedo;
uniform sampler2D gNormal;
uniform vec3      uLightDir;

out vec4 fragColor;

void main() {
    vec4 albedo = texture(gAlbedo, vTexCoord);
    if (albedo.a < 0.01) discard;

    vec3 norm     = normalize(texture(gNormal, vTexCoord).rgb * 2.0 - 1.0);
    vec3 lightDir = normalize(-uLightDir);

    float ambient = 0.60;
    float diff    = max(dot(norm, lightDir), 0.0) * 0.40;
    float light   = ambient + diff;

    fragColor = vec4(clamp(light, 0.0, 1.0) * albedo.rgb, 1.0);
}
