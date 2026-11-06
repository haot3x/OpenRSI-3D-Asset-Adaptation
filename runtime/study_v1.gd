extends "res://animation_case.gd"
var peak := -INF
var minimum := INF
var max_abs_x := 0.0

func sample(t: float) -> void:
	await super.sample(t)
	for mesh in meshes:
		var transform: Transform3D = asset.global_transform.affine_inverse() * mesh.global_transform
		for surface in range(mesh.mesh.get_surface_count()):
			var arrays: Array = mesh.mesh.surface_get_arrays(surface)
			for vertex in arrays[Mesh.ARRAY_VERTEX]:
				var point: Vector3 = transform * vertex
				peak = maxf(peak, point.y)
				minimum = minf(minimum, point.y)
				max_abs_x = maxf(max_abs_x, absf(point.x))

func poses() -> void:
	await super.poses()
	checks["metric_root_scale"] = asset.scale.is_equal_approx(Vector3.ONE)
	checks["ceiling_clearance"] = peak <= float(render_config.ceiling_height) - float(render_config.clearance_margin)
	checks["ground_clearance"] = minimum >= -0.02
	checks["identity_head_volume"] = part_volume("PelicanHead") > 0.02
	checks["identity_beak_volume"] = part_volume("Beak") > 0.008
	checks["identity_body_volume"] = part_volume("PelicanBody") > 0.15
	if render_config.has("inner_width"):
		checks["aisle_clearance"] = max_abs_x <= float(render_config.inner_width)/2 - float(render_config.side_margin)
	if render_config.get("dock", false):
		var socket := Vector3(render_config.dock_socket[0], render_config.dock_socket[1], render_config.dock_socket[2])
		checks["dock_socket"] = parts.has("DockSocket") and near(asset.to_local(parts.DockSocket.global_position), socket, 0.015)
		checks["dock_visible_plate"] = parts.get("DockPlate") is MeshInstance3D
		for i in range(4):
			var offset := Vector3(-0.10 if i%2 == 0 else 0.10, 0, -0.08 if i < 2 else 0.08)
			var point := asset.to_global(socket+offset)
			var query := PhysicsRayQueryParameters3D.create(point+Vector3.UP*0.04, point-Vector3.UP*0.06, 1)
			var hit: Dictionary = asset.get_world_3d().direct_space_state.intersect_ray(query)
			checks["dock_support_"+str(i)] = not hit.is_empty() and str(hit.collider.get_parent().name) == "DockPlate" and absf(asset.to_local(hit.position).y-socket.y) < 0.02 and hit.normal.dot(Vector3.UP) > 0.9
	print("STUDY_V1_DIAGNOSTICS "+JSON.stringify({"scene_id": render_config.scene_id, "sampled_peak_height_metres": peak, "sampled_minimum_height_metres": minimum, "sampled_half_width_metres": max_abs_x, "triangle_count": triangles, "scope": "sampled surface-vertex envelope and four docking support rays, not full traversal, continuous collision or full semantic identity"}))

func part_volume(name: String) -> float:
	if not parts.get(name) is MeshInstance3D:
		return 0.0
	var mesh: MeshInstance3D = parts[name]
	var size: Vector3 = mesh.get_aabb().size
	return absf(size.x*size.y*size.z*mesh.global_basis.determinant())
