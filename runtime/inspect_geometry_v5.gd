extends SceneTree
## Checks generated mesh and rig hierarchy after GLB import; not a physics Judge.
var nodes := {}
var players := []
var mesh_count := 0
var triangles := 0

func _initialize() -> void:
	call_deferred("run")

func collect(node: Node) -> void:
	if node is Node3D:
		nodes[str(node.name)] = node
	if node is AnimationPlayer:
		players.append(node)
	if node is MeshInstance3D:
		mesh_count += 1
		for i in range(node.mesh.get_surface_count()):
			var arrays: Array = node.mesh.surface_get_arrays(i)
			triangles += arrays[Mesh.ARRAY_INDEX].size()/3 if arrays[Mesh.ARRAY_INDEX] != null and arrays[Mesh.ARRAY_INDEX].size() > 0 else arrays[Mesh.ARRAY_VERTEX].size()/3
	for child in node.get_children():
		collect(child)

func run() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() != 1:
		quit(2)
		return
	var job: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	if document.append_from_file(job.asset_path,state) != OK:
		push_error("GLB import failed")
		quit(2)
		return
	var asset: Node3D = document.generate_scene(state,240.0,false,false)
	root.add_child(asset)
	collect(asset)
	if players.size() != 1:
		push_error("Expected one animation player")
		quit(2)
		return
	var player: AnimationPlayer = players[0]
	var failures := []
	var checked := 0
	var max_error := 0.0
	for sample in job.samples:
		if not player.has_animation(sample.clip):
			failures.append("Missing clip: "+str(sample.clip))
			continue
		player.play(sample.clip)
		player.seek(float(sample.time),true)
		player.advance(0.0)
		for pid in sample.nodes:
			if not nodes.has(pid):
				failures.append("Missing node: "+str(pid))
				continue
			var expected: Array = sample.nodes[pid]
			var actual: Transform3D = nodes[pid].global_transform
			var rows := [[actual.basis.x.x,actual.basis.y.x,actual.basis.z.x,actual.origin.x],[actual.basis.x.y,actual.basis.y.y,actual.basis.z.y,actual.origin.y],[actual.basis.x.z,actual.basis.y.z,actual.basis.z.z,actual.origin.z]]
			var error := 0.0
			for i in range(3):
				for j in range(4):
					error = maxf(error,absf(float(rows[i][j])-float(expected[i][j])))
			max_error = maxf(max_error,error)
			checked += 1
			if error > 0.0001:
				failures.append(str(sample.clip)+"/"+str(pid)+"/"+str(sample.time)+": "+str(error))
	if mesh_count != int(job.mesh_count) or triangles != int(job.triangle_count):
		failures.append("Mesh/triangle count changed")
	for pid in job.parents:
		var parent: String = job.parents[pid]
		if not nodes.has(pid) or not nodes.has(parent) or nodes[pid].get_parent() != nodes[parent]:
			failures.append("Joint hierarchy changed: "+str(pid))
	var result := {"engine":Engine.get_version_info().string,"mesh_count":mesh_count,"triangles":triangles,"clips":Array(player.get_animation_list()),"checked_transforms":checked,"max_transform_error":max_error,"failures":failures,"passed":failures.is_empty()}
	print("GEOMETRY_V5_ROUNDTRIP "+JSON.stringify(result))
	quit(0 if failures.is_empty() else 1)
