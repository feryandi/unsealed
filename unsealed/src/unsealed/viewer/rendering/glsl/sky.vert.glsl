#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 2) in vec2 aUV;

uniform mat4 uView;
uniform mat4 uProjection;
uniform mat4 uModel;

out vec2 vUV;

void main() {
    // Rotation-only view is pre-applied in Python (translation stripped).
    // xyww forces depth = w/w = 1.0 so sky is always behind everything.
    vec4 clip = uProjection * uView * uModel * vec4(aPos, 1.0);
    gl_Position = clip.xyww;
    vUV = vec2(aUV.x, 1.0 - aUV.y);
}
