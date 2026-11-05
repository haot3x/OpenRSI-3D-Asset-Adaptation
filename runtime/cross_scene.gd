extends "res://animation_case.gd"
## Two public fixtures. This checks an axis-aligned ceiling envelope, not full traversal.
func poses() -> void:
	await super.poses()
	var peak := -INF
	var minimum := INF
	# The animation evaluator returns the root to neutral and the clip to t=0.
	# Measure geometry in the fixture's metric frame; don't normalize away scale.
	for mesh in meshes:
		# A transformed AABB overestimates rotated parts and can falsely reject
		# geometry that fits. Measure the actual exported surface vertices.
		for surface in range(mesh.mesh.get_surface_count()):
			var arrays: Array = mesh.mesh.surface_get_arrays(surface)
			for vertex in arrays[Mesh.ARRAY_VERTEX]:
				var point: Vector3 = mesh.to_global(vertex)
				peak = maxf(peak, point.y)
				minimum = minf(minimum, point.y)
	checks["metric_root_scale"] = asset.scale.is_equal_approx(Vector3.ONE)
	checks["ceiling_clearance"] = peak <= float(render_config.ceiling_height) - float(render_config.clearance_margin)
	checks["ground_clearance"] = minimum >= -0.02
	checks["identity_head_volume"] = part_volume("PelicanHead") > 0.02
	checks["identity_beak_volume"] = part_volume("Beak") > 0.008
	checks["identity_body_volume"] = part_volume("PelicanBody") > 0.15
	print("CROSS_SCENE_DIAGNOSTICS "+JSON.stringify({"scene_id": render_config.scene_id, "peak_height_metres": peak, "minimum_height_metres": minimum, "ceiling_height_metres": render_config.ceiling_height, "required_margin_metres": render_config.clearance_margin, "scope": "neutral-pose geometric envelope plus inherited animation diagnostics; no traversal, contact force, style or full identity metric"}))

func part_volume(name: String) -> float:
	if not parts.get(name) is MeshInstance3D:
		return 0.0
	var mesh: MeshInstance3D = parts[name]
	var size: Vector3 = mesh.get_aabb().size
	return absf(size.x * size.y * size.z * mesh.global_basis.determinant())
