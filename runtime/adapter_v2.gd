extends "res://adapter_motion_v2.gd"
var current := {}
var peak := -INF
var anchor_error := 0.0
var joint_error := 0.0
var static_error := 0.0
var head_error := 0.0
var tip_error := 0.0
var scale_error := 0.0
var geometry_ready := false
var tip_local := Vector3.ZERO

func vector(a: Array) -> Vector3:
	return Vector3(a[0],a[1],a[2])
func center_of(name: String) -> Vector3:
	var mesh: MeshInstance3D = parts[name]
	return asset.to_local(mesh.to_global(mesh.get_aabb().get_center()))
func get_tip() -> void:
	var mesh: MeshInstance3D = parts.Beak
	var points := []
	var end_z := INF
	for surface in range(mesh.mesh.get_surface_count()):
		var arrays: Array = mesh.mesh.surface_get_arrays(surface)
		for point in arrays[Mesh.ARRAY_VERTEX]:
			points.append(point)
			end_z = minf(end_z,point.z)
	var n := 0
	for point in points:
		if absf(point.z-end_z) < 0.00001:
			tip_local += point
			n += 1
	tip_local /= max(1,n)
	geometry_ready = true

func sample(t: float) -> void:
	await super.sample(t)
	if not parts.get("PelicanHead") is MeshInstance3D or not parts.get("Beak") is MeshInstance3D or not parts.has("Neck"):
		anchor_error = INF
		return
	if not geometry_ready:
		get_tip()
	var head := center_of("PelicanHead")
	var tip: Vector3 = asset.to_local(parts.Beak.to_global(tip_local))
	var anchor: Vector3 = asset.to_local(parts.Neck.to_global(Vector3(0,-.265,0)))
	var top: Vector3 = asset.to_local(parts.Neck.to_global(Vector3(0,.265,0)))
	anchor_error = maxf(anchor_error,anchor.distance_to(vector(render_config.neck_anchor)))
	joint_error = maxf(joint_error,head.distance_to(top))
	if current.has("head_target"):
		head_error = maxf(head_error,head.distance_to(vector(current.head_target)))
	if current.has("tip_target"):
		tip_error = maxf(tip_error,tip.distance_to(vector(current.tip_target)))
	for name in render_config.static_meshes:
		if not parts.has(name):
			static_error = INF
			continue
		var transform: Transform3D = asset.global_transform.affine_inverse()*parts[name].global_transform
		var expected: Dictionary = render_config.static_meshes[name]
		static_error = maxf(static_error,transform.origin.distance_to(vector(expected.origin)))
		static_error = maxf(static_error,transform.basis.x.distance_to(vector(expected.x)))
		static_error = maxf(static_error,transform.basis.y.distance_to(vector(expected.y)))
		static_error = maxf(static_error,transform.basis.z.distance_to(vector(expected.z)))
	for mesh in meshes:
		var transform: Transform3D = asset.global_transform.affine_inverse()*mesh.global_transform
		var reference: Dictionary = render_config.meshes[str(mesh.name)]
		var rx := vector(reference.x)
		var ry := vector(reference.y)
		var rz := vector(reference.z)
		scale_error = maxf(scale_error,absf(transform.basis.x.length()-rx.length()))
		scale_error = maxf(scale_error,absf(transform.basis.y.length()-ry.length()))
		scale_error = maxf(scale_error,absf(transform.basis.z.length()-rz.length()))
		scale_error = maxf(scale_error,absf(transform.basis.determinant()-rx.cross(ry).dot(rz)))
		for surface in range(mesh.mesh.get_surface_count()):
			var arrays: Array = mesh.mesh.surface_get_arrays(surface)
			for vertex in arrays[Mesh.ARRAY_VERTEX]:
				var point: Vector3 = transform*vertex
				peak = maxf(peak,point.y)

func poses() -> void:
	var definitions := {}
	for scene in render_config.scenes:
		definitions[scene.id] = scene
	var visits := []
	var scene_pass := {}
	for id in render_config.sequence:
		current = definitions[id]
		render_config.clip = current.clip
		peak = -INF
		anchor_error = 0
		joint_error = 0
		static_error = 0
		head_error = 0
		tip_error = 0
		scale_error = 0
		checks = {}
		await super.poses()
		checks["neck_base_attached"] = anchor_error <= 0.015
		checks["neck_head_connected"] = joint_error <= 0.04
		checks["static_components_preserved"] = static_error <= 0.0001
		checks["metric_root_scale"] = asset.scale.is_equal_approx(Vector3.ONE)
		checks["mesh_scales_preserved"] = scale_error <= 0.0001
		checks["scene_ceiling"] = peak <= float(current.ceiling_height)-float(current.get("clearance_margin",0))+0.0001
		if current.has("head_target"):
			checks["scene_head_target"] = head_error <= float(current.head_tolerance)
		if current.has("tip_target"):
			checks["scene_beak_target"] = tip_error <= float(current.tip_tolerance)
		var failures := []
		for key in checks:
			if not checks[key]: failures.append(key)
		var passed := failures.is_empty()
		scene_pass[id] = passed and scene_pass.get(id,true)
		visits.append({"scene": id, "requested_clip": current.clip, "actual_clip": clip, "passed": passed, "failed_checks": failures, "metrics": {"peak_metres":peak,"neck_anchor_error":anchor_error,"neck_head_gap":joint_error,"static_transform_error":static_error,"head_target_error":head_error,"beak_target_error":tip_error}})
	checks = {}
	for id in scene_pass:
		checks["scene_"+str(id)] = scene_pass[id]
	print("ADAPTER_V2_RESULT "+JSON.stringify({"version":"v2.1","scene_pass":scene_pass,"visits":visits,"scope":"three model-authored animation adapters with seven switches; fixed geometry checked separately; no transition-blend or collision-complete semantic claim"}))
