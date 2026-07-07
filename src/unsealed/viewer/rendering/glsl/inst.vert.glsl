#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;
// Per-instance world transform (mat4 occupies 4 consecutive attribute locations)
layout(location = 5) in mat4 aInstanceMatrix;

uniform mat4 uModel;       // base mesh-local transform
uniform mat4 uView;
uniform mat4 uProjection;

out vec3 vFragPos;
out vec3 vNormal;
out vec2 vTexCoord;

void main() {
    mat4 world    = aInstanceMatrix * uModel;
    vec4 worldPos = world * vec4(aPos, 1.0);
    vFragPos  = worldPos.xyz;
    vNormal   = mat3(transpose(inverse(world))) * aNormal;
    vTexCoord = vec2(aTexCoord.x, 1.0 - aTexCoord.y);
    gl_Position = uProjection * uView * worldPos;
}
