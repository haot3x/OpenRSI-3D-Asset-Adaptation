extends SceneTree
## Convex shapes on frozen RigidBody3Ds; posed sphere queries, not dynamics.

func _initialize() -> void:
	call_deferred("run")

func vector(values: Array) -> Vector3:
	return Vector3(float(values[0]), float(values[1]), float(values[2]))

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 2:
		quit(2)
		return
	var input: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var rows := []
	var engine_mismatches := 0
	var checked := 0
	var started := Time.get_ticks_usec()
	var sphere := SphereShape3D.new()
	sphere.radius = float(input.radius)
	sphere.margin = 0.0
	var poses := [Transform3D.IDENTITY, Transform3D(Basis(Vector3(1, 2, 3).normalized(), 0.7), Vector3(0.3, -0.2, 0.1))]
	for job in input.jobs:
		var body := RigidBody3D.new()
		body.freeze = true
		body.freeze_mode = RigidBody3D.FREEZE_MODE_KINEMATIC
		body.gravity_scale = 0.0
		body.collision_layer = 1
		for points in job.hulls:
			var convex := ConvexPolygonShape3D.new()
			convex.margin = 0.0
			var vertices := PackedVector3Array()
			for p in points:
				vertices.append(vector(p))
			convex.points = vertices
			var child := CollisionShape3D.new()
			child.shape = convex
			body.add_child(child)
		root.add_child(body)
		for pose_index in range(poses.size()):
			var pose: Transform3D = poses[pose_index]
			body.global_transform = pose
			await physics_frame
			await physics_frame
			var space := body.get_world_3d().direct_space_state
			var mismatch := 0
			var false_free := 0
			var false_blocked := 0
			var query_usec := 0
			for q in job.queries:
				var parameters := PhysicsShapeQueryParameters3D.new()
				parameters.shape = sphere
				parameters.margin = 0.0
				parameters.collision_mask = 1
				parameters.transform = Transform3D(Basis.IDENTITY, pose * vector(q.point))
				var query_start := Time.get_ticks_usec()
				var blocked := not space.intersect_shape(parameters, 1).is_empty()
				query_usec += Time.get_ticks_usec() - query_start
				checked += 1
				if blocked != bool(q.proxy_blocked):
					mismatch += 1
				if blocked and not bool(q.source_blocked):
					false_blocked += 1
				if not blocked and bool(q.source_blocked):
					false_free += 1
			engine_mismatches += mismatch
			rows.append({"asset": job.asset, "part": job.part, "pose": pose_index, "hulls": job.hulls.size(), "queries": job.queries.size(), "analytic_mismatches": mismatch, "source_false_free": false_free, "source_false_blocked": false_blocked, "query_usec": query_usec})
		body.free()
		await physics_frame
	var result := {"engine": Engine.get_version_info().string, "physics_engine": ProjectSettings.get_setting("physics/3d/physics_engine"), "kind": "Posed convex sphere queries on frozen RigidBody3Ds; not dynamics", "checked": checked, "analytic_mismatches": engine_mismatches, "rows": rows, "wall_seconds": float(Time.get_ticks_usec() - started) / 1000000.0, "passed": engine_mismatches == 0}
	var file := FileAccess.open(args[1], FileAccess.WRITE)
	file.store_string(JSON.stringify(result, "  "))
	file.close()
	print("CONVEX_V6_ENGINE "+JSON.stringify({"checked": checked, "analytic_mismatches": engine_mismatches, "wall_seconds": result.wall_seconds, "passed": result.passed}))
	quit(0 if engine_mismatches == 0 else 1)
