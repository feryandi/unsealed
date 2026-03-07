#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aTexCoord;

uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
uniform mat3 uTexMatrix;
uniform bool uTcGenEnv;

out vec2 vTexCoord;

void main() {
    vec4 worldPos = uModel * vec4(aPos, 1.0);

    vec2 rawUV;
    if (uTcGenEnv) {
        vec3 viewDir  = normalize(vec3(uView * worldPos));
        vec3 viewNorm = normalize(mat3(uView * uModel) * aNormal);
        vec3 refl     = reflect(viewDir, viewNorm);
        rawUV = refl.xy * 0.5 + 0.5;
    } else {
        // Match game UV convention: pipeline uploads rows top-to-bottom then
        // flips vertically in _upload_rgba, so v=0 is at the bottom in GL.
        // We flip V back so game texcoords (v=0 at top) render correctly.
        rawUV = vec2(aTexCoord.x, 1.0 - aTexCoord.y);
    }

    vTexCoord = (uTexMatrix * vec3(rawUV, 1.0)).xy;
    gl_Position = uProjection * uView * worldPos;
}
