extends "res://base_asset.gd"
func poses() -> void:
	var rows := {}
	for mesh in meshes:
		var transform: Transform3D = asset.global_transform.affine_inverse()*mesh.global_transform
		var center: Vector3 = transform*mesh.get_aabb().get_center()
		rows[str(mesh.name)] = {"origin": vec(transform.origin), "x": vec(transform.basis.x), "y": vec(transform.basis.y), "z": vec(transform.basis.z), "center": vec(center), "local_size": vec(mesh.get_aabb().size)}
	var anchor: Vector3 = asset.to_local(parts.Neck.to_global(Vector3(0,-.265,0)))
	print("V2_METADATA "+JSON.stringify({"meshes": rows, "neck_anchor": vec(anchor)}))
func vec(v: Vector3) -> Array:
	return [v.x,v.y,v.z]
