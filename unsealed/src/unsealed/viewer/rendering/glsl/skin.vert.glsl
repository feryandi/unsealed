#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;
layout(location = 3) in vec4 aJoints;   // bone indices packed as floats
layout(location = 4) in vec4 aWeights;  // blend weights

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform mat4 uBoneMatrices[128];

out vec3 vFragPos;
out vec3 vNormal;
out vec2 vTexCoord;

void main() {
    mat4 skin = uBoneMatrices[int(aJoints.x)] * aWeights.x
              + uBoneMatrices[int(aJoints.y)] * aWeights.y
              + uBoneMatrices[int(aJoints.z)] * aWeights.z
              + uBoneMatrices[int(aJoints.w)] * aWeights.w;

    vec4 localPos  = skin * vec4(aPos, 1.0);
    vec3 localNorm = mat3(skin) * aNormal;

    vec4 worldPos = uModel * localPos;
    vFragPos  = worldPos.xyz;
    vNormal   = mat3(transpose(inverse(uModel))) * localNorm;
    vTexCoord = vec2(aTexCoord.x, 1.0 - aTexCoord.y);
    gl_Position = uProjection * uView * worldPos;
}
