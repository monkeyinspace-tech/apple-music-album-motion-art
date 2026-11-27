"""Registro de efeitos (embutidos + plugins do usuário).

Dois tipos:
  layer      -> processa os pixels de UMA camada de imagem (flow, boil, shine, blur, glow, tint, chroma, wave...)
  generator  -> desenha direto no quadro, como camada própria (embers, rings, sparkles, light_leaks...)

Para criar um efeito novo veja docs/14-criar-efeitos.md ou rode:  studio.py new-effect meu_efeito --kind generator
"""
import importlib.util, os

LAYER, GEN = {}, {}


def _reg(table, kind, name, params, doc):
    def deco(cls):
        cls.fx_name, cls.fx_kind, cls.fx_params, cls.fx_doc = name, kind, params, doc
        table[name] = cls
        return cls
    return deco


def layer_fx(name, params, doc):
    """params: {nome: (tipo, padrão, descrição)}"""
    return _reg(LAYER, 'layer', name, params, doc)


def generator(name, params, doc):
    return _reg(GEN, 'generator', name, params, doc)


def load_plugins(*dirs):
    """Importa todos os .py de cada pasta (plugins do projeto/usuário). Retorna os nomes carregados."""
    loaded = []
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith('.py') and not f.startswith('_'):
                spec = importlib.util.spec_from_file_location(f'amstudio_plugin_{f[:-3]}', os.path.join(d, f))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                loaded.append(f)
    return loaded


def catalog():
    out = []
    for table in (LAYER, GEN):
        for name, cls in sorted(table.items()):
            out.append({'name': name, 'kind': cls.fx_kind, 'doc': cls.fx_doc,
                        'params': {k: {'type': v[0], 'default': v[1], 'doc': v[2]} for k, v in cls.fx_params.items()}})
    return out


from . import builtin_layer as _l, builtin_gen as _g   # noqa: E402,F401  (registra os embutidos)
