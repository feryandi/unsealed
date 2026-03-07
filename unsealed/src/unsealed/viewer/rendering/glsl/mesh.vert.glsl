#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;

out vec3 vFragPos;
out vec3 vNormal;
out vec2 vTexCoord;

void main() {
    vec4 worldPos = uModel * vec4(aPos, 1.0);
    vFragPos = worldPos.xyz;
    vNormal = mat3(transpose(inverse(uModel))) * aNormal;
    // Pipeline provides top-to-bottom RGBA; upload flips rows so GL v=0=bottom.
    // Flip V here so game UVs (v=0 at top) map correctly.
    vTexCoord = vec2(aTexCoord.x, 1.0 - aTexCoord.y);
    gl_Position = uProjection * uView * worldPos;
}
