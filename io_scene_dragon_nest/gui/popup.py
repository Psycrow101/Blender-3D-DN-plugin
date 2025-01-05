def invalid_skn_type(self, context):
    self.layout.label(text='Invalid skn type')


def invalid_msh_type(self, context):
    self.layout.label(text='Invalid msh type')


def invalid_ani_type(self, context):
    self.layout.label(text='Invalid ani type')


def missing_msh(self, context):
    self.layout.label(text='MSH File not found')


def invalid_armature(self, context):
    self.layout.label(text='Invalid armature')


def need_armature_to_export(self, context):
    self.layout.label(text='Make the armature (Scene Root) active for export')


def missing_material(self, context):
    self.layout.label(text='Missing material')


def too_many_materials(self, context):
    self.layout.label(text='Only one material per mesh is supported')
