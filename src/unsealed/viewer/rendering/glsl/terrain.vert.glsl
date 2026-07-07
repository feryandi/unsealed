#version 330 core
layout(location = 0) in vec3 aPos;   // (x, height, z)
layout(location = 1) in vec2 aUv;    // UV for terrain_layer_a (path, rotated)
layout(location = 2) in vec2 aUv2;   // UV for terrain_layer_b (base terrain, original)

uniform mat4 uView;
uniform mat4 uProjection;

out vec2 vUv;
out vec2 vUv2;

void main() {
    vUv  = vec2(aUv.x,  1.0 - aUv.y);
    vUv2 = vec2(aUv2.x, 1.0 - aUv2.y);
    gl_Position = uProjection * uView * vec4(aPos, 1.0);
}
