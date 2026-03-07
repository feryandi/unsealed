#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 5) in mat4 aInstanceMatrix;
uniform mat4 uModel;
uniform mat4 uView;
uniform mat4 uProjection;
void main() {
    gl_Position = uProjection * uView * aInstanceMatrix * uModel * vec4(aPos, 1.0);
}
