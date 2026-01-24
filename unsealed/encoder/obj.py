
class ObjEncoder:
  # TODO: Support other than geometry?
  def __init__(self, geometry):
    self.geometry = geometry

  # TODO: This should return binary instead
  def encode(self, path):
    with open(path, "w") as fobj:
      v_s = 0
      vt_s = 0
      vn_s = 0

      for mesh in self.geometry.meshes:
        fobj.write("\no " + mesh.name + "\n")

        for v in mesh.vertices:
          fobj.write("v " + str(round(v.position[0], 6)) + " " + str(
              round(v.position[1], 6)) + " " + str(round(v.position[2], 6)) + "\n")
          fobj.write(
              "vt " + str(round(v.texcoord[0], 6)) + " " + str(round(v.texcoord[1], 6)) + "\n")
          fobj.write("vn " + str(round(v.normal[0], 6)) + " " + str(
              round(v.normal[1], 6)) + " " + str(round(v.normal[2], 6)) + "\n")

        i_f = 0
        s_f = ""
        for f in mesh.indices:
          s_f += str(v_s+f+1) + "/" + str(vt_s+f+1) + \
              "/" + str(vn_s+f+1) + " "
          i_f += 1
          if i_f % 3 == 0:
            fobj.write("f " + s_f + "\n")
            s_f = ""

        v_s += len(mesh.vertices)
        vt_s += len(mesh.vertices)
        vn_s += len(mesh.vertices)
