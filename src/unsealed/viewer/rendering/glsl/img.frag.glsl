#version 330 core
in vec2 vUV;
uniform sampler2D uTexture;
out vec4 fragColor;
void main() {
    vec4 col = texture(uTexture, vUV);
    // Photoshop-style checkerboard background for transparent areas.
    // gl_FragCoord is in window pixels so the pattern is always screen-sized.
    int check = (int(gl_FragCoord.x / 8.0) + int(gl_FragCoord.y / 8.0)) & 1;
    vec3 bg = (check == 0) ? vec3(0.78) : vec3(0.58);
    fragColor = vec4(mix(bg, col.rgb, col.a), 1.0);
}
