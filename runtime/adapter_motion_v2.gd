extends "res://adapter_base_v2.gd"
var animator: AnimationPlayer
var clip := ""
func position_of(name: String) -> Vector3:
	return asset.to_local(parts[name].global_position)
func collision_between(name: String, a: Vector3, b: Vector3) -> bool:
	var midpoint := asset.to_global((a+b)/2)
	var offset := asset.global_basis*Vector3(0.12, 0, 0)
	var q := PhysicsRayQueryParameters3D.create(midpoint+offset, midpoint-offset, 1)
	var hit: Dictionary = asset.get_world_3d().direct_space_state.intersect_ray(q)
	return not hit.is_empty() and str(hit.collider.get_parent().name) == name
func sample(t: float) -> void:
	if animator != null and clip != "":
		animator.seek(t, true)
	await frames(4)
func poses() -> void:
	animator = null
	clip = ""
	var roles := ["WheelFront", "WheelRear", "Crank", "PedalLeft", "PedalRight", "HipLeft", "HipRight", "KneeLeft", "KneeRight", "FootLeft", "FootRight", "ThighLeft", "ThighRight", "ShinLeft", "ShinRight", "TyreFront", "TyreRear", "PelicanBody", "PelicanHead", "Beak", "Pouch", "SpokeMarkFront", "SpokeMarkRear"]
	var ready := true
	for name in roles:
		ready = ready and parts.has(name)
	for node in asset.find_children("*", "AnimationPlayer", true, false):
		for name in node.get_animation_list():
			if str(name).to_lower().ends_with(str(render_config.clip).to_lower()):
				animator = node
				clip = str(name)
	checks["required_roles"] = ready
	checks["triangle_limit"] = triangles > 0 and triangles <= int(render_config.triangle_limit)
	checks["ride_animation"] = animator != null
	checks["two_second_cycle"] = animator != null and absf(animator.get_animation(clip).length-2) < 0.03
	var mesh_roles := true
	for name in ["TyreFront", "TyreRear", "ThighLeft", "ThighRight", "ShinLeft", "ShinRight", "FootLeft", "FootRight", "PelicanBody", "PelicanHead", "Beak", "Pouch"]:
		mesh_roles = mesh_roles and parts.get(name) is MeshInstance3D
	checks["visible_required_parts"] = mesh_roles
	if animator != null:
		animator.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		animator.play(clip)
		animator.speed_scale = 1
	await sample(0)
	for side in ["Front", "Rear"]:
		var bounds := AABB()
		if ready and parts["Tyre"+side] is MeshInstance3D:
			bounds = (parts["Wheel"+side].global_transform.affine_inverse()*parts["Tyre"+side].global_transform)*parts["Tyre"+side].get_aabb()
		checks["wheel_dimensions_"+side] = ready and absf(bounds.size.y-1) < 0.04 and absf(bounds.size.z-1) < 0.04 and bounds.size.x < 0.18 and bounds.size.x > 0.02
	for root_index in range(2):
		asset.position = Vector3.ZERO if root_index == 0 else Vector3(2.3, 0.3, -1.8)
		asset.rotation_degrees.y = 0 if root_index == 0 else 37
		for i in range(8):
			var t := float(i)*0.25
			await sample(t)
			var theta := PI*t
			var prefix := "root_"+str(root_index)+"_phase_"+str(i)+"_"
			for side in [{"name": "Left", "sign": -1.0}, {"name": "Right", "sign": 1.0}]:
				var suffix: String = side.name
				var sign_value: float = side.sign
				var angle := theta + (0.0 if sign_value < 0 else PI)
				var pedal := Vector3(sign_value*0.2, 0.52+0.2*sin(angle), 0.1-0.2*cos(angle))
				var hip := Vector3(sign_value*0.15, 1.45, 0.28)
				checks[prefix+"pedal_path_"+suffix] = ready and near(position_of("Pedal"+suffix), pedal, 0.025)
				checks[prefix+"foot_contact_"+suffix] = ready and position_of("Foot"+suffix).distance_to(position_of("Pedal"+suffix)) < 0.065
				checks[prefix+"hip_stationary_"+suffix] = ready and near(position_of("Hip"+suffix), hip, 0.025)
				checks[prefix+"thigh_length_"+suffix] = ready and absf(position_of("Hip"+suffix).distance_to(position_of("Knee"+suffix))-0.65) < 0.025
				checks[prefix+"shin_length_"+suffix] = ready and absf(position_of("Knee"+suffix).distance_to(position_of("Foot"+suffix))-0.65) < 0.025
				checks[prefix+"thigh_collision_"+suffix] = ready and collision_between("Thigh"+suffix, position_of("Hip"+suffix), position_of("Knee"+suffix))
				checks[prefix+"shin_collision_"+suffix] = ready and collision_between("Shin"+suffix, position_of("Knee"+suffix), position_of("Foot"+suffix))
			for wheel in [{"name": "Front", "z": -0.85}, {"name": "Rear", "z": 0.85}]:
				var center := Vector3(0, 0.5, wheel.z)
				var expected := center + Basis(Vector3.RIGHT, 2*theta)*Vector3(0, 0, -0.4)
				checks[prefix+"wheel_center_"+wheel.name] = ready and near(position_of("Wheel"+wheel.name), center, 0.025)
				checks[prefix+"wheel_rotation_"+wheel.name] = ready and near(position_of("SpokeMark"+wheel.name), expected, 0.025)
	asset.position = Vector3.ZERO
	asset.rotation_degrees = Vector3.ZERO
	await sample(1.99)
	var before := {}
	for name in ["FootLeft", "FootRight", "KneeLeft", "KneeRight", "SpokeMarkFront", "SpokeMarkRear"]:
		if ready:
			before[name] = position_of(name)
	await sample(0)
	for name in ["FootLeft", "FootRight", "KneeLeft", "KneeRight", "SpokeMarkFront", "SpokeMarkRear"]:
		checks["cycle_seam_"+name] = ready and position_of(name).distance_to(before[name]) < 0.08
	for speed in [0.5, 1.5]:
		if animator != null:
			animator.speed_scale = speed
			animator.play(clip)
			animator.seek(0, true)
			animator.advance(0.25)
		await frames(4)
		var theta: float = PI*0.25*speed
		var expected := Vector3(-0.2, 0.52+0.2*sin(theta), 0.1-0.2*cos(theta))
		checks["speed_playback_"+str(speed)] = ready and animator != null and near(position_of("PedalLeft"), expected, 0.025)
	if animator != null:
		animator.speed_scale = 1
	await sample(0)
