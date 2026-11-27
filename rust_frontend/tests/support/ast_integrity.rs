//! Shared syntax-tree integrity checks; no semantic or rule analysis.
use corbo_frontend::ast::*;

pub fn audit(unit: &ParsedUnit) -> Result<(), String> {
    let ast = &unit.ast;
    if ast.root.0 >= ast.nodes.len() {
        return Err("invalid AST root".into());
    }
    let mut visited = vec![false; ast.nodes.len()];
    let mut pending = vec![ast.root];
    while let Some(id) = pending.pop() {
        if id.0 >= ast.nodes.len() {
            return Err(format!("invalid child {id:?}"));
        }
        if visited[id.0] {
            return Err(format!("shared or cyclic syntax node {id:?}"));
        }
        visited[id.0] = true;
        let node = &ast.nodes[id.0];
        let span = node.span;
        if span.start > span.end
            || span.end > unit.source.len()
            || !unit.source.is_char_boundary(span.start)
            || !unit.source.is_char_boundary(span.end)
        {
            return Err(format!("invalid source span for {id:?}: {span:?}"));
        }
        if node.tokens.start > node.tokens.end || node.tokens.end > unit.tokens.len() {
            return Err(format!("invalid token range for {id:?}"));
        }
        for reference in node.kind.token_refs() {
            let Some(token) = unit.tokens.get(reference.index) else {
                return Err(format!("invalid token reference in {id:?}"));
            };
            if reference.span.start < token.span.start
                || reference.span.end > token.span.end
                || reference.span.start >= reference.span.end
                || reference.span.start < span.start
                || reference.span.end > span.end
                || !unit.source.is_char_boundary(reference.span.start)
                || !unit.source.is_char_boundary(reference.span.end)
            {
                return Err(format!(
                    "token view {reference:?} outside owning node {id:?} ({span:?}) or token {:?}",
                    token.span
                ));
            }
        }
        for child in node.kind.children() {
            let Some(child_node) = ast.nodes.get(child.0) else {
                return Err(format!("invalid child of {id:?}: {child:?}"));
            };
            if child_node.span.start < span.start || child_node.span.end > span.end {
                return Err(format!(
                    "child {child:?} {:?} outside parent {id:?} {span:?}",
                    child_node.span
                ));
            }
            if child_node.tokens.start < node.tokens.start
                || child_node.tokens.end > node.tokens.end
            {
                return Err(format!("child token range outside parent {id:?}"));
            }
            pending.push(child);
        }
    }
    if let Some(orphan) = visited.iter().position(|seen| !seen) {
        return Err(format!(
            "syntax node {orphan} is disconnected from the root: {:?}",
            ast.nodes[orphan].kind
        ));
    }
    Ok(())
}
