# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/09_processors.ipynb.

# %% auto 0
__all__ = ['DEFAULT_FM_KEYS', 'add_links', 'strip_ansi', 'hide_', 'hide_line', 'filter_stream_', 'clean_magics', 'lang_identify',
           'rm_header_dash', 'rm_export', 'clean_show_doc', 'remove_widget_state', 'exec_show_docs', 'insert_warning',
           'add_show_docs', 'is_frontmatter', 'nb_fmdict', 'construct_fm', 'insert_frontmatter', 'infer_frontmatter']

# %% ../nbs/09_processors.ipynb 2
import ast

from .read import *
from .imports import *
from .process import *
from .lookup import *
from .showdoc import *

from execnb.nbio import *
from execnb.shell import *
from fastcore.imports import *
from fastcore.xtras import *

# %% ../nbs/09_processors.ipynb 9
def add_links(cell):
    "Add links to markdown cells"
    nl = NbdevLookup(libs())
    if cell.cell_type == 'markdown': cell.source = nl.linkify(cell.source)
    for o in cell.get('outputs', []):
        if hasattr(o, 'data') and hasattr(o['data'], 'text/markdown'):
            o.data['text/markdown'] = [nl.link_line(s) for s in o.data['text/markdown']]

# %% ../nbs/09_processors.ipynb 12
_re_ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(cell):
    "Strip Ansi Characters."
    for outp in cell.get('outputs', []):
        if outp.get('name')=='stdout': outp['text'] = [_re_ansi_escape.sub('', o) for o in outp.text]

# %% ../nbs/09_processors.ipynb 14
def hide_(nbp, cell):
    "Hide cell from output"
    del(cell['source'])

# %% ../nbs/09_processors.ipynb 16
_re_hideline = re.compile(r'#\|\s*hide_line\s*$', re.MULTILINE)
def hide_line(cell):
    "Hide lines of code in code cells with the directive `hide_line` at the end of a line of code"
    if cell.cell_type == 'code' and _re_hideline.search(cell.source):
        cell.source = '\n'.join([c for c in cell.source.splitlines() if not _re_hideline.search(c)])

# %% ../nbs/09_processors.ipynb 18
def filter_stream_(nbp, cell, *words):
    "Remove output lines containing any of `words` in `cell` stream output"
    if not words: return
    for outp in cell.get('outputs', []):
        if outp.output_type == 'stream':
            outp['text'] = [l for l in outp.text if not re.search('|'.join(words), l)]

# %% ../nbs/09_processors.ipynb 20
_magics_pattern = re.compile(r'^\s*(%%|%).*', re.MULTILINE)

def clean_magics(cell):
    "A preprocessor to remove cell magic commands"
    if cell.cell_type == 'code': cell.source = _magics_pattern.sub('', cell.source).strip()

# %% ../nbs/09_processors.ipynb 22
_langs = 'bash|html|javascript|js|latex|markdown|perl|ruby|sh|svg'
_lang_pattern = re.compile(rf'^\s*%%\s*({_langs})\s*$', flags=re.MULTILINE)

def lang_identify(cell):
    "A preprocessor to identify bash/js/etc cells and mark them appropriately"
    if cell.cell_type == 'code':
        lang = _lang_pattern.findall(cell.source)
        if lang:
            lang = lang[0]
            if lang=='js': lang='javascript'  # abbrev provided by jupyter
            cell.metadata.language = lang

# %% ../nbs/09_processors.ipynb 25
_re_hdr_dash = re.compile(r'^#+\s+.*\s+-\s*$', re.MULTILINE)

def rm_header_dash(cell):
    "Remove headings that end with a dash -"
    if cell.source:
        src = cell.source.strip()
        if cell.cell_type == 'markdown' and src.startswith('#') and src.endswith(' -'): del(cell['source'])

# %% ../nbs/09_processors.ipynb 27
_exp_dirs = {'export','exporti'}
_hide_dirs = {*_exp_dirs, 'hide','default_exp'}

def rm_export(cell):
    "Remove cells that are exported or hidden"
    if cell.directives_:
        if cell.directives_.keys() & _hide_dirs: del(cell['source'])

# %% ../nbs/09_processors.ipynb 29
_re_showdoc = re.compile(r'^show_doc', re.MULTILINE)
def _is_showdoc(cell): return cell['cell_type'] == 'code' and _re_showdoc.search(cell.source)

def clean_show_doc(cell):
    "Remove ShowDoc input cells"
    if not _is_showdoc(cell): return
    cell.source = '#| echo: false\n' + cell.source

# %% ../nbs/09_processors.ipynb 30
def remove_widget_state(cell):
    "Remove widgets in the output of `cells`"
    if cell['cell_type'] == 'code' and 'outputs' in cell:
        cell['outputs'] = [l for l in cell['outputs']
                           if not ('data' in l and 'application/vnd.jupyter.widget-view+json' in l.data)]

# %% ../nbs/09_processors.ipynb 32
_imps = {ast.Import, ast.ImportFrom}

def _show_docs(trees):
    return [t for t in trees if isinstance(t,ast.Expr) and nested_attr(t, 'value.func.id')=='show_doc']

def _do_eval(cell):
    trees = cell.parsed_()
    if cell.cell_type != 'code' or not trees: return
    if cell.directives_.get('eval:', [''])[0].lower() == 'false': return
    if cell.directives_.keys() & _exp_dirs or filter_ex(trees, risinstance(_imps)): return True
    if _show_docs(trees): return True

# %% ../nbs/09_processors.ipynb 33
class exec_show_docs:
    "Execute cells needed for `show_docs` output, including exported cells and imports"
    def __init__(self, nb):
        self.k = CaptureShell()
        self.k.run_cell('from nbprocess.showdoc import show_doc')

    def __call__(self, cell):
        if _do_eval(cell): self.k.cell(cell)
        if self.k.exc: raise self.k.exc[1] from None

# %% ../nbs/09_processors.ipynb 36
def insert_warning(nb):
    "Insert Autogenerated Warning Into Notebook after the first cell."
    content = "<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->"
    nb.cells.insert(1, mk_cell(content, False))

# %% ../nbs/09_processors.ipynb 40
_def_types = (ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)
def _def_names(cell, shown):
    return [showdoc_nm(o) for o in concat(cell.parsed_()) if isinstance(o,_def_types) and o.name not in shown and o.name[0]!='_']

_re_exps = re.compile(r'^\s*#\|\s*(?:export|exporti)').search

def _get_nm(tree):
    i = tree.value.args[0]
    return f'{i.value.id}.{i.attr}' if isinstance(i, ast.Attribute) else i.id

# %% ../nbs/09_processors.ipynb 41
def add_show_docs(nb):
    "Add show_doc cells after exported cells, unless they are already documented"
    exports = L(cell for cell in nb.cells if cell.source and _re_exps(cell.source))
    trees = nb.cells.map(NbCell.parsed_).concat()
    shown_docs = {_get_nm(t) for t in _show_docs(trees)}
    for cell in reversed(exports):
        for nm in _def_names(cell, shown_docs):
            code = f'show_doc({nm})'
            nb.cells.insert(cell.idx_+1, mk_cell(code))

# %% ../nbs/09_processors.ipynb 45
_re_title = re.compile(r'^#\s+(.*)[\n\r]+(?:^>\s+(.*))?', flags=re.MULTILINE)
_re_fm = re.compile(r'^---.*\S+.*---', flags=re.DOTALL)
_re_defaultexp = re.compile(r'^\s*#\|\s*default_exp\s+(\S+)', flags=re.MULTILINE)

def _celltyp(nb, cell_type): return nb.cells.filter(lambda c: c.cell_type == cell_type)
def is_frontmatter(nb): return _celltyp(nb, 'raw').filter(lambda c: _re_fm.search(c.get('source', '')))
def _istitle(cell): 
    txt = cell.get('source', '')
    return bool(_re_title.search(txt)) if txt else False

# %% ../nbs/09_processors.ipynb 46
def _default_exp(nb):
    "get the default_exp from a notebook"
    code_src = nb.cells.filter(lambda x: x.cell_type == 'code').attrgot('source')
    default_exp = first(code_src.filter().map(_re_defaultexp.search).filter())
    return default_exp.group(1) if default_exp else None

# %% ../nbs/09_processors.ipynb 48
def nb_fmdict(nb, remove=True): 
    "Infer the front matter from a notebook's markdown formatting"
    md_cells = _celltyp(nb, 'markdown').filter(_istitle)
    if not md_cells: return {}
    cell = md_cells[0]
    title,desc=_re_title.match(cell.source).groups()
    if title:
        flags = re.findall('^-\s+(.*)', cell.source, flags=re.MULTILINE)
        flags = [s.split(':', 1) for s in flags if ':' in s] if flags else []
        flags = merge({k:v for k,v in flags if k and v}, 
                      {'title':title}, {'description':desc} if desc else {})
        if remove: cell['source'] = None
        return flags
    else: return {}

# %% ../nbs/09_processors.ipynb 51
DEFAULT_FM_KEYS = ['title', 'description', 'author', 'image', 'categories', 'output-file', 'aliases']

def construct_fm(fmdict:dict, keys = DEFAULT_FM_KEYS):
    "construct front matter from a dictionary, but only for `keys`"
    if not fmdict: return None
    return '---\n'+'\n'.join([f"{k}: {fmdict[k]}" for k in keys if k in fmdict])+'\n---'

# %% ../nbs/09_processors.ipynb 53
def insert_frontmatter(nb, fm_dict:dict, filter_keys:list=DEFAULT_FM_KEYS):
    "Add frontmatter into notebook based on `filter_keys` that exist in `fmdict`."
    fm = construct_fm(fm_dict, keys=filter_keys)
    if fm: nb.cells.insert(0, NbCell(0, dict(cell_type='raw', metadata={}, source=fm)))

# %% ../nbs/09_processors.ipynb 54
def infer_frontmatter(nb):
    "Insert front matter if it doesn't exist automatically from nbdev styled markdown."
    if is_frontmatter(nb): return
    _exp = _default_exp(nb)
    _fmdict = merge(nb_fmdict(nb), {'output-file': _exp} if _exp else {})
    if 'title' in _fmdict: insert_frontmatter(nb, fm_dict=_fmdict)
