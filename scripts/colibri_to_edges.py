# scripts/colibri_to_edges.py
import json, csv, os, re, sys, glob

# ---- paths ----
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PROJECT_ROOT)  # scripts/ -> project root
TARGET_DIR = os.path.join(PROJECT_ROOT, "target")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
MANIFEST_PATH = os.path.join(TARGET_DIR, "manifest.json")
CATALOG_PATH = os.path.join(TARGET_DIR, "catalog.json")

MODEL_EDGES_CSV = os.path.join(DIST_DIR, "colibri_edges.csv")
COLUMN_EDGES_CSV = os.path.join(DIST_DIR, "colibri_edges_columns.csv")
ALL_EDGES_CSV = os.path.join(DIST_DIR, "colibri_edges_all.csv")

DEBUG = ("--debug" in sys.argv)

# ---- regexes ----
FROM_JOIN_RE = re.compile(
    r'\b(from|join)\s+'
    r'((?:"?[A-Za-z_][\w$]*"?\.){0,2}"?[A-Za-z_][\w$]*"?)'  # 1-3 parts
    r'(?:\s+(?:as\s+)?("?([A-Za-z_][\w$]*)"?))?',            # optional alias
    re.IGNORECASE
)
AS_NEWCOL_RE = re.compile(r'\bas\s+"?([A-Za-z_][\w$]*)"?', re.IGNORECASE)
SCHEMA_TABLE_COL_RE = re.compile(
    r'"?([A-Za-z_][\w$]*)"?\s*\.\s*"?([A-Za-z_][\w$]*)"?\s*\.\s*"?([A-Za-z_][\w$]*)"?'
)
ALIAS_COL_RE = re.compile(r'"?([A-Za-z_][\w$]*)"?\s*\.\s*"?([A-Za-z_][\w$]*)"?')
QUOTED_IDENT_RE = re.compile(r'"([A-Za-z_][\w$]*)"')
BARE_IDENT_RE = re.compile(r'\b([A-Za-z_][A-Za-z0-9_$]*)\b')

SQL_KEYWORDS = {
    "select","from","join","left","right","inner","outer","on","where","group","by","having","order","limit","offset",
    "union","all","distinct","case","when","then","else","end","as","and","or","not","is","null","like","ilike",
    "in","between","exists","over","partition","rows","range","current","row","preceding","following",
    "cast","coalesce","greatest","least","extract","year","month","day","date","datetime","interval",
    "true","false"
}

def strip_q(s): return s.replace('"','').replace('`','').strip() if isinstance(s,str) else s

# ---- load/save helpers ----
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def rel_name(node):
    schema = node.get("schema") or node.get("database") or "main"
    name = node.get("alias") or node.get("identifier") or node.get("name") or node.get("resource_name") or "unknown"
    return f"{schema}.{name}"

def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "target", "relationship"])
        for r in rows:
            w.writerow([r["source"], r["target"], r.get("relationship", "ref")])

# ---- compiled SQL discovery (robust) ----
def compiled_sql_candidates(node):
    """Yield likely compiled sql file paths for a node."""
    compiled_rel = node.get("compiled_path") or node.get("path")
    pkg = node.get("package_name","")

    if compiled_rel:
        compiled_rel = compiled_rel.replace("/", os.sep).replace("\\", os.sep)
        # direct known locations
        yield os.path.join(TARGET_DIR, "compiled", compiled_rel)
        if pkg:
            yield os.path.join(TARGET_DIR, "compiled", pkg, compiled_rel)
            yield os.path.join(TARGET_DIR, "run", pkg, compiled_rel)

    # fallback: recursive search by filename under compiled & run
    base_name = None
    if compiled_rel:
        base_name = os.path.basename(compiled_rel)
    else:
        # last resort: model name
        base_name = (node.get("name") or "model") + ".sql"

    for root in ("compiled", "run"):
        pattern = os.path.join(TARGET_DIR, root, "**", base_name)
        for p in glob.glob(pattern, recursive=True):
            yield p

def compiled_sql_paths(manifest):
    nodes = manifest.get("nodes", {})
    for node_id, node in nodes.items():
        if node.get("resource_type") != "model":
            continue
        found_path = None
        tried = []
        for p in compiled_sql_candidates(node):
            tried.append(p)
            if os.path.isfile(p):
                found_path = p
                break
        if found_path:
            if DEBUG:
                print(f"[FOUND] {node_id} -> {found_path}")
            yield node_id, node, found_path
        else:
            if DEBUG:
                print(f"[MISS ] {node_id} (no compiled SQL). Tried:")
                for t in tried: print(f"        - {t}")

# ---- model edges directly from parent_map ----
def build_model_edges(manifest):
    nodes = manifest.get("nodes", {})
    parent_map = manifest.get("parent_map", {})
    edges = []
    for child_id, parents in parent_map.items():
        child = nodes.get(child_id)
        if not child: 
            continue
        child_rel = rel_name(child)
        for parent_id in parents:
            parent = nodes.get(parent_id) or manifest.get("sources", {}).get(parent_id)
            if not parent:
                continue
            parent_rel = rel_name(parent)
            rel = "source" if (parent.get("resource_type") in ("seed", "source")) else "ref"
            edges.append({"source": parent_rel, "target": child_rel, "relationship": rel})
    uniq = {(e["source"], e["target"], e["relationship"]) for e in edges}
    return [{"source": s, "target": t, "relationship": r} for (s, t, r) in sorted(uniq)]

# ---- lineage helpers ----
def parse_qualified_to_schema_table(qual: str, default_schema: str):
    parts = [strip_q(p) for p in qual.split(".")]
    if len(parts) == 1:
        return (default_schema, parts[0])
    if len(parts) == 2:
        return (parts[0], parts[1])
    return (parts[-2], parts[-1])  # db.schema.table -> schema.table

def parents_as_sources(manifest, node_id):
    parents = manifest.get("parent_map", {}).get(node_id, [])
    out, seen = [], set()
    for pid in parents:
        p = manifest.get("nodes", {}).get(pid) or manifest.get("sources", {}).get(pid)
        if not p: 
            continue
        if p.get("resource_type") in ("model","seed","source"):
            rn = rel_name(p)
            if rn not in seen:
                seen.add(rn); out.append(rn)
    return out

def build_alias_map(sql_text, default_schema):
    amap = {}
    for m in FROM_JOIN_RE.finditer(sql_text):
        _, qual, _, alias = m.groups()
        qual = strip_q(qual)
        schema, table = parse_qualified_to_schema_table(qual, default_schema)
        fq = f"{schema}.{table}"
        if alias:
            amap[strip_q(alias)] = fq
        amap[table] = fq
        amap[f"{schema}.{table}"] = fq
    return amap

def find_select_item_window(sql, as_match_start):
    i = as_match_start - 1
    depth = 0
    while i >= 0:
        c = sql[i]
        if c == ')': depth += 1
        elif c == '(' and depth > 0: depth -= 1
        elif c == ',' and depth == 0:
            return i + 1, as_match_start
        i -= 1
    return 0, as_match_start

def strip_string_literals(text):
    return re.sub(r"'(?:''|[^'])*'", "", text)

def load_catalog_columns(catalog):
    """Return map: schema.table -> set(columns)"""
    out = {}
    merged = {}
    merged.update(catalog.get("nodes", {}))
    merged.update(catalog.get("sources", {}))
    for obj in merged.values():
        meta = obj.get("metadata", {})
        schema = meta.get("schema") or "main"
        name = meta.get("name") or obj.get("name") or obj.get("alias")
        if not name:
            continue
        rel = f"{schema}.{name}"
        cols = set((obj.get("columns") or {}).keys())
        out[rel] = cols
    return out

def choose_candidate_tables(alias_map, fallback_tables):
    vals = set(alias_map.values())
    filtered = [v for v in vals if not v.lower().endswith(".base")]
    if filtered:
        return sorted(set(filtered))
    if fallback_tables:
        return list(fallback_tables)
    return []

def sources_from_window(window_text, candidate_tables, alias_map, new_col_name, catalog_cols):
    sources = []
    win = strip_string_literals(window_text)

    # db.schema.table.col
    for m in SCHEMA_TABLE_COL_RE.finditer(win):
        schema, table, col = map(strip_q, m.groups())
        fq = f"{schema}.{table}"
        if not catalog_cols or (fq in catalog_cols and col in catalog_cols[fq]):
            sources.append((fq, col))

    # alias.col or table.col
    for m in ALIAS_COL_RE.finditer(win):
        alias, col = map(strip_q, m.groups())
        if f"." in alias:
            fq = alias
        else:
            fq = alias_map.get(alias)
        if fq:
            if not catalog_cols or (fq in catalog_cols and col in catalog_cols[fq]):
                sources.append((fq, col))

    # bare identifiers -> map to all candidate tables if the col exists there
    if candidate_tables:
        idents = set(QUOTED_IDENT_RE.findall(win)) | set(BARE_IDENT_RE.findall(win))
        for col in idents:
            col_s = strip_q(col)
            if not col_s or col_s.lower() in SQL_KEYWORDS or col_s == new_col_name:
                continue
            if re.fullmatch(r'\d+(\.\d+)?', col_s):
                continue
            for fq in candidate_tables:
                if not catalog_cols or (fq in catalog_cols and col_s in catalog_cols[fq]):
                    sources.append((fq, col_s))

    out, seen = [], set()
    for t, c in sources:
        key = (t, c)
        if key not in seen:
            seen.add(key); out.append(key)
    return out

def build_column_edges(manifest, catalog):
    nodes = manifest.get("nodes", {})
    column_edges = []
    catalog_cols = load_catalog_columns(catalog) if catalog else {}

    any_processed = False

    for node_id, node, path in compiled_sql_paths(manifest):
        any_processed = True
        try:
            with open(path, "r", encoding="utf-8") as f:
                sql = f.read()
        except Exception as e:
            if DEBUG:
                print(f"[READ ] {node_id} -> failed to read {path}: {e}")
            continue

        target_rel = rel_name(node)
        default_schema = node.get("schema") or "main"

        alias_map = build_alias_map(sql, default_schema)
        fallback_tables = parents_as_sources(manifest, node_id)

        # map common CTE alias to first real parent if present
        if "base" in alias_map and fallback_tables:
            alias_map["base"] = fallback_tables[0]

        candidate_tables = choose_candidate_tables(alias_map, fallback_tables)

        matches = list(AS_NEWCOL_RE.finditer(sql))

        if DEBUG:
            print(f"[MODEL] {target_rel}")
            print(f"        file: {path}")
            print(f"        parents: {fallback_tables}")
            print(f"        alias_map: {alias_map}")
            print(f"        candidates: {candidate_tables}")
            print(f"        select items (AS …): {len(matches)}")

        for m in matches:
            new_col = strip_q(m.group(1))
            w_start, w_end = find_select_item_window(sql, m.start())
            window = sql[w_start:w_end]
            srcs = sources_from_window(window, candidate_tables, alias_map, new_col, catalog_cols)

            if DEBUG:
                preview = " ".join(window.strip().split())[:140]
                print(f"          → new_col: {new_col:>24} | srcs: {len(srcs)} | window: {preview}")

            for table_fq, src_col in srcs:
                column_edges.append({
                    "source": f"{table_fq}.{src_col}",
                    "target": f"{target_rel}.{new_col}",
                    "relationship": "column"
                })

    if DEBUG and not any_processed:
        print("[WARN ] No compiled SQL files were found under target/. Check your paths.")

    uniq = {(e["source"], e["target"], e["relationship"]) for e in column_edges}
    return [{"source": s, "target": t, "relationship": r} for (s, t, r) in sorted(uniq)]

def main():
    if not os.path.isfile(MANIFEST_PATH):
        print(f"manifest.json not found at: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)

    manifest = load_json(MANIFEST_PATH)
    catalog = load_json(CATALOG_PATH) if os.path.isfile(CATALOG_PATH) else None

    model_edges = build_model_edges(manifest)
    write_csv(MODEL_EDGES_CSV, model_edges)

    column_edges = build_column_edges(manifest, catalog)
    write_csv(COLUMN_EDGES_CSV, column_edges)

    all_edges = model_edges + column_edges
    uniq = {(e["source"], e["target"], e["relationship"]) for e in all_edges}
    all_edges = [{"source": s, "target": t, "relationship": r} for (s, t, r) in sorted(uniq)]
    write_csv(ALL_EDGES_CSV, all_edges)

    print(f"Wrote {MODEL_EDGES_CSV} with {len(model_edges)} model edges")
    print(f"Wrote {COLUMN_EDGES_CSV} with {len(column_edges)} column edges")
    print(f"Wrote {ALL_EDGES_CSV} with {len(all_edges)} total edges")

if __name__ == "__main__":
    main()
