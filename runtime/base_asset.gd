extends SceneTree
## Fixed pilot controller. Geometry, pivots and hierarchy come from the GLB.
var asset: Node3D
var parts := {}
var meshes := []
var triangles := 0
var checks := {}
var render_config := {}
var camera: Camera3D

func _initialize() -> void:
	call_deferred("run")
func frames(n: int) -> void:
	for _i in range(n):
		await physics_frame
func collect(node: Node) -> void:
	if node is Node3D:
		parts[str(node.name)] = node
	if node is MeshInstance3D:
		meshes.append(node)
		for surface in range(node.mesh.get_surface_count()):
			var arrays: Array = node.mesh.surface_get_arrays(surface)
			triangles += arrays[Mesh.ARRAY_INDEX].size()/3 if arrays[Mesh.ARRAY_INDEX] != null and arrays[Mesh.ARRAY_INDEX].size() > 0 else arrays[Mesh.ARRAY_VERTEX].size()/3
	for child in node.get_children():
		collect(child)
func near(a: Vector3, b: Vector3, tolerance := 0.06) -> bool:
	return a.distance_to(b) < tolerance
func poses() -> void:
	var available := true
	for name in ["YawPivot", "PitchPivot", "MuzzleLeft", "MuzzleRight", "BarrelLeft", "BarrelRight", "Base"]:
		available = available and parts.has(name)
	checks["required_parts"] = available
	checks["mesh_budget"] = triangles > 0 and triangles <= 3000
	if not available:
		for key in ["pitch_under_yaw", "barrels_follow_pitch", "yaw_pivot_position", "pitch_pivot_position"]:
			checks[key] = false
		for root_yaw in [0.0, 33.0]:
			var index := 0
			for pose in [{"yaw": 0.0, "pitch": 0.0}, {"yaw": 60.0, "pitch": 25.0}, {"yaw": -40.0, "pitch": 35.0}, {"yaw": 0.0, "pitch": 0.0}]:
				var prefix := "root_"+str(root_yaw)+"_step_"+str(index)+"_pose_"+str(pose.yaw)+"_"+str(pose.pitch)+"_"
				index += 1
				for suffix in ["muzzle_Left", "muzzle_Right", "barrel_collision_Left", "barrel_collision_Right", "base_fixed"]:
					checks[prefix+suffix] = false
		return
	var yaw: Node3D = parts.YawPivot
	var pitch: Node3D = parts.PitchPivot
	checks["pitch_under_yaw"] = yaw.is_ancestor_of(pitch)
	checks["barrels_follow_pitch"] = pitch.is_ancestor_of(parts.BarrelLeft) and pitch.is_ancestor_of(parts.BarrelRight)
	checks["yaw_pivot_position"] = near(asset.to_local(yaw.global_position), Vector3(0, 0.5, 0), 0.03)
	checks["pitch_pivot_position"] = near(yaw.to_local(pitch.global_position), Vector3(0, 0.68, 0), 0.03)
	var base_position: Vector3 = asset.to_local(parts.Base.global_position)
	for transform in [{"origin": Vector3.ZERO, "yaw": 0.0}, {"origin": Vector3(3, 0.4, -2), "yaw": 33.0}]:
		asset.position = transform.origin
		asset.rotation_degrees.y = transform.yaw
		var pose_index := 0
		for pose in [{"yaw": 0.0, "pitch": 0.0}, {"yaw": 60.0, "pitch": 25.0}, {"yaw": -40.0, "pitch": 35.0}, {"yaw": 0.0, "pitch": 0.0}]:
			yaw.rotation_degrees = Vector3(0, pose.yaw, 0)
			pitch.rotation_degrees = Vector3(pose.pitch, 0, 0)
			await frames(4)
			var prefix := "root_"+str(transform.yaw)+"_step_"+str(pose_index)+"_pose_"+str(pose.yaw)+"_"+str(pose.pitch)+"_"
			pose_index += 1
			for side in [{"name": "Left", "x": -0.26}, {"name": "Right", "x": 0.26}]:
				var expected: Vector3 = Vector3(0, 0.5, 0) + Basis(Vector3.UP, deg_to_rad(pose.yaw))*(Vector3(0, 0.68, 0)+Basis(Vector3.RIGHT, deg_to_rad(pose.pitch))*Vector3(side.x, 0, -1.73))
				checks[prefix+"muzzle_"+side.name] = near(asset.to_local(parts["Muzzle"+side.name].global_position), expected)
				var barrel: Node3D = parts["Barrel"+side.name]
				var center: Vector3 = barrel.to_global(barrel.get_aabb().get_center()) if barrel is MeshInstance3D else barrel.global_position
				var query := PhysicsRayQueryParameters3D.create(center+Vector3(0.4, 0, 0), center-Vector3(0.4, 0, 0), 1)
				checks[prefix+"barrel_collision_"+side.name] = not asset.get_world_3d().direct_space_state.intersect_ray(query).is_empty()
			checks[prefix+"base_fixed"] = near(asset.to_local(parts.Base.global_position), base_position, 0.01)
	asset.position = Vector3.ZERO
	asset.rotation_degrees = Vector3.ZERO
	yaw.rotation_degrees = Vector3.ZERO
	pitch.rotation_degrees = Vector3.ZERO

func render_views(output: String) -> void:
	var env_node := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.025, 0.035, 0.05)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color.WHITE
	env.ambient_light_energy = 0.65
	env_node.environment = env
	root.add_child(env_node)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-40, -25, 0)
	root.add_child(light)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 4.5
	root.add_child(camera)
	camera.make_current()
	var views := [{"id": "front", "position": Vector3(0, 1, -6)}, {"id": "side", "position": Vector3(6, 1, 0)}, {"id": "top", "position": Vector3(0, 7, -0.4)}, {"id": "iso", "position": Vector3(5, 4, -6)}]
	for mode in ["beauty", "mask"]:
		if mode == "mask":
			env.background_color = Color.BLACK
			var mat := StandardMaterial3D.new()
			mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			mat.albedo_color = Color.WHITE
			for mesh in meshes:
				mesh.material_override = mat
		for view in views:
			camera.position = view.position
			camera.look_at(Vector3(0, 0.95, -0.35), Vector3.FORWARD if view.id == "top" else Vector3.UP)
			await process_frame
			await RenderingServer.frame_post_draw
			var error := root.get_texture().get_image().save_png(output+"/"+view.id+"-"+mode+".png")
			if error != OK:
				push_error("Failed saving image")

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1:
		quit(2)
		return
	var job: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	render_config = job.get("spec", {})
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	var error := document.append_from_file(job.asset_path, state)
	if error != OK:
		push_error("GLB import failed: "+str(error))
		quit(2)
		return
	asset = document.generate_scene(state)
	root.add_child(asset)
	collect(asset)
	for mesh in meshes:
		mesh.create_convex_collision()
	await frames(4)
	await poses()
	if job.get("render", false):
		await render_views(job.output)
	var passed := 0
	for key in checks:
		if checks[key]:
			passed += 1
	print("BLENDER_ASSET_RESULT "+JSON.stringify({"engine": Engine.get_version_info().string, "checks": checks, "passed_checks": passed, "total_checks": checks.size(), "all_checks_pass": passed == checks.size(), "triangle_count": triangles, "mesh_count": meshes.size(), "controller": "fixed evaluator samples model-authored animation and builds convex collisions; it does not synthesize riding motion or solve leg IK"}))
	quit(0)
