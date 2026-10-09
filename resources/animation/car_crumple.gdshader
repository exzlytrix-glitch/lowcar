shader_type spatial;
render_mode diffuse_burley;
uniform vec4 paint : source_color = vec4(1.0);
uniform float roughness_value = 0.55;
uniform float metallic_value = 0.0;
uniform vec3 damage = vec3(0.0); // left, right, front
uniform mat4 local_to_body = mat4(1.0);

void vertex() {
	vec3 original = (local_to_body * vec4(VERTEX, 1.0)).xyz;
	vec3 deformed = original;
	float nose = smoothstep(0.55, 2.40, -original.z);
	deformed.z += damage.z * 0.43 * nose;
	deformed.y += damage.z * nose * (0.11 * (1.0 - nose) - 0.045);
	deformed.x += sign(original.x) * damage.z * nose * 0.025;
	float side = smoothstep(0.35, 1.08, abs(original.x));
	float doors = 1.0 - smoothstep(0.95, 1.70, abs(original.z));
	float below_windows = 1.0 - smoothstep(0.88, 1.02, original.y);
	float dent = (original.x < 0.0 ? damage.x : damage.y) * side * doors * below_windows;
	deformed.x -= sign(original.x) * dent * 0.23;
	deformed.y -= dent * 0.035;
	VERTEX = (inverse(local_to_body) * vec4(deformed, 1.0)).xyz;
}

void fragment() {
	ALBEDO = paint.rgb;
	ROUGHNESS = roughness_value;
	METALLIC = metallic_value;
	SPECULAR = 0.28;
}
