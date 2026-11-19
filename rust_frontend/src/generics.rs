//! Static specialization of structurally constrained record templates.
//! Concrete records are checked and lowered by the ordinary frontend.
use crate::{Error, Span, parser::NodeId, tree::{Fact, StaticTree}};
use std::collections::{BTreeMap, HashMap};

#[derive(Clone)]
struct Template {
    node: NodeId,
    name: String,
    parameters: Vec<String>,
    implementations: Vec<NodeId>,
}

pub(crate) struct Expansion {
    pub source: String,
    pub offsets: Vec<usize>,
    pub generated_ranges: Vec<(std::ops::Range<usize>, std::ops::Range<usize>)>,
    pub layouts: Vec<(String, String, std::ops::Range<usize>)>,
}

struct Resolver<'a> {
    source: &'a str,
    tree: &'a StaticTree,
    templates: Vec<Template>,
    uses: HashMap<NodeId, usize>,
}

impl Resolver<'_> {
    fn word(&self, token: usize) -> &str {
        let span = self.tree.tokens[token].span;
        &self.source[span.start..span.end]
    }
    fn name(&self, id: NodeId) -> &str {
        self.tree.syntax.nodes[id.0].name.map(|i| self.word(i)).unwrap_or("")
    }
    fn span(&self, id: NodeId) -> Span {
        let node = &self.tree.syntax.nodes[id.0];
        Span { start: self.tree.tokens[node.start].span.start,
            end: self.tree.tokens[node.end - 1].span.end }
    }
    fn text(&self, id: NodeId) -> String {
        let span = self.span(id);
        self.source[span.start..span.end].to_owned()
    }
    fn error(&self, id: NodeId, message: &'static str) -> Error {
        Error::new(self.span(id).start, message)
    }
    fn in_template(&self, id: NodeId) -> bool {
        let span = self.span(id);
        self.templates.iter().any(|template| std::iter::once(&template.node)
            .chain(template.implementations.iter()).any(|&part| {
                let outer = self.span(part);
                span.start >= outer.start && span.end <= outer.end
            }))
    }
    fn parent(&self, id: NodeId) -> Option<NodeId> {
        self.tree.syntax.nodes.iter().enumerate()
            .find_map(|(index, node)| node.children.contains(&id).then_some(NodeId(index)))
    }
    fn matched_type(&self, id: NodeId) -> Option<String> {
        let mut parent = id;
        while self.tree.syntax.nodes[parent.0].kind != "bras" { parent = self.parent(parent)?; }
        let selection = self.parent(parent)?;
        self.infer(self.tree.syntax.nodes[selection.0].children[0], 0)
    }

    fn function(&self, name: &str) -> Option<NodeId> {
        self.tree.syntax.nodes[self.tree.syntax.root.0].children.iter().copied()
            .find(|&id| matches!(self.tree.syntax.nodes[id.0].kind, "fn" | "async fn") && self.name(id) == name)
    }
    fn method(&self, owner: &str, name: &str) -> Option<NodeId> {
        self.tree.syntax.nodes[self.tree.syntax.root.0].children.iter().copied()
            .filter(|&id| self.tree.syntax.nodes[id.0].kind == "impl" && self.name(id) == owner)
            .flat_map(|id| self.tree.syntax.nodes[id.0].children.iter().copied())
            .find(|&id| matches!(self.tree.syntax.nodes[id.0].kind, "fn" | "async fn") && self.name(id) == name)
    }
    fn output(&self, function: NodeId) -> Option<NodeId> {
        self.tree.syntax.nodes[function.0].children.iter().copied()
            .find(|&id| self.tree.syntax.nodes[id.0].kind == "type")
    }
    fn infer(&self, id: NodeId, depth: usize) -> Option<String> {
        if depth > 128 { return None; }
        let node = &self.tree.syntax.nodes[id.0];
        match node.kind {
            "nom" => {
                let binding = &self.tree.bindings[*self.uses.get(&id)?];
                if let Some(ty) = binding.ty { Some(self.text(ty)) }
                else if binding.name == "self" {
                    self.tree.syntax.nodes.iter().find(|node| node.kind == "impl" && node.children.iter().any(|method| {
                        self.tree.syntax.nodes[method.0].children.contains(&binding.syntax)
                    })).and_then(|node| node.name).map(|token| {
                        let owner = self.word(token);
                        let parameter = self.text(binding.syntax);
                        if parameter.contains('&') {
                            format!("&{}{}", if parameter.contains("mut") { "mut " } else { "" }, owner)
                        } else { owner.to_owned() }
                    })
                } else if let Some(initializer) = binding.initializer {
                    self.infer(initializer, depth + 1)
                } else {
                    let mut parent = binding.syntax;
                    while self.tree.syntax.nodes[parent.0].kind != "bras" {
                        parent = self.parent(parent)?;
                    }
                    let arm = &self.tree.syntax.nodes[parent.0];
                    let selection = self.parent(parent)?;
                    let subject = self.tree.syntax.nodes[selection.0].children[0];
                    let ty = self.infer(subject, depth + 1)?;
                    let (owner, arguments) = generic_parts(&ty)?;
                    let pattern = &self.tree.syntax.nodes[arm.children[0].0];
                    let tag = self.word(pattern.start);
                    if owner == "Result" { arguments.get(if tag == "Err" { 1 } else { 0 }).cloned() }
                    else if owner == "Option" { arguments.first().cloned() } else { None }
                }
            }
            "construction" => Some(self.name(id).to_owned()),
            "match" => {
                let ty = self.infer(node.children[0], depth + 1)?;
                if let Some(inner) = ty.strip_prefix("Result<").and_then(|ty| ty.strip_suffix('>')) {
                    let mut nesting = 0;
                    let split = inner.char_indices().find_map(|(index, ch)| {
                        match ch { '<' | '[' | '(' => nesting += 1, '>' | ']' | ')' => nesting -= 1,
                            ',' if nesting == 0 => return Some(index), _ => {} }
                        None
                    })?;
                    Some(inner[..split].trim().to_owned())
                } else { None }
            }
            "indice" => {
                let base = self.infer(node.children[0], depth + 1)?;
                let base = strip_reference(&base);
                let inner = base.strip_prefix('[')?.strip_suffix(']')?;
                let element = inner.split(';').next()?.trim();
                if self.tree.syntax.nodes[node.children[1].0].kind == "plage" {
                    Some(format!("[{element}]"))
                } else { Some(element.to_owned()) }
            }
            "groupe" | "await" => self.infer(*node.children.first()?, depth + 1),
            "emprunt" => {
                let ty = self.infer(*node.children.first()?, depth + 1)?;
                let mutable = (node.start..self.tree.syntax.nodes[node.children[0].0].start)
                    .any(|i| self.word(i) == "mut");
                Some(format!("&{}{}", if mutable { "mut " } else { "" }, ty))
            }
            "indirection" => {
                let ty = self.infer(*node.children.first()?, depth + 1)?;
                Some(ty.strip_prefix('&')?.trim_start().strip_prefix("mut ").unwrap_or(ty.strip_prefix('&')?.trim()).to_owned())
            }
            "projection" => {
                let owner = self.infer(node.children[0], depth + 1)?;
                let owner = owner.trim_start_matches('&').trim_start().strip_prefix("mut ").unwrap_or(owner.trim_start_matches('&').trim());
                let record = self.tree.syntax.nodes[self.tree.syntax.root.0].children.iter().copied()
                    .find(|&id| self.tree.syntax.nodes[id.0].kind == "struct" && self.name(id) == owner)?;
                let field = self.tree.syntax.nodes[record.0].children.iter().copied()
                    .find(|&field| self.tree.syntax.nodes[field.0].kind == "champ" && self.name(field) == self.name(id))?;
                Some(self.text(self.tree.syntax.nodes[field.0].children[0]))
            }
            "appel" => {
                let callee = node.children[0];
                let parts = self.text(callee);
                let function = if let Some((owner, name)) = parts.rsplit_once("::") {
                    if let Some(template) = self.templates.iter().find(|template| template.name == owner) {
                        let method = self.method(owner, name)?;
                        let mapping = self.arguments(template, method, &node.children[1..]).ok()?;
                        let output = self.text(self.output(method)?);
                        return Some(substitute_type(&output, &mapping));
                    }
                    self.method(owner, name)?
                } else { self.function(&parts)? };
                self.output(function).map(|id| self.text(id))
            }
            "appel méthode" => {
                let owner = self.infer(node.children[0], depth + 1)?;
                let owner = strip_reference(&owner);
                if let Some((generic, arguments)) = generic_parts(owner) {
                    let template = self.templates.iter().find(|template| template.name == generic)?;
                    let mapping = template.parameters.iter().cloned().zip(arguments).collect();
                    return self.output(self.method(&template.name, self.name(id))?)
                        .map(|id| substitute_type(&self.text(id), &mapping));
                }
                self.output(self.method(owner, self.name(id))?).map(|id| self.text(id))
            }
            "littéral" => {
                let word = self.name(id);
                Some(if word == "true" || word == "false" { "bool" }
                    else if word.contains('.') { "f64" } else { "i64" }.to_owned())
            }
            _ => None,
        }
    }
    fn arguments(&self, template: &Template, method: NodeId, arguments: &[NodeId]) -> Result<BTreeMap<String, String>, Error> {
        let parameters = self.tree.syntax.nodes[method.0].children.iter().copied()
            .filter(|&id| self.tree.syntax.nodes[id.0].kind == "paramètre").collect::<Vec<_>>();
        if parameters.len() != arguments.len() { return Err(self.error(method, "nombre d’arguments incompatible")); }
        let mut mapping = BTreeMap::new();
        for (parameter, argument) in parameters.into_iter().zip(arguments) {
            let ty = self.tree.syntax.nodes[parameter.0].children[0];
            let actual = self.infer(*argument, 0).ok_or_else(|| self.error(*argument, "type concret du contrat indéterminé"))?;
            unify(&self.text(ty), &actual, &template.parameters, &mut mapping)
                .map_err(|message| self.error(*argument, message))?;
        }
        self.constraints(template, &mut mapping)?;
        if template.parameters.iter().any(|parameter| !mapping.contains_key(parameter)) {
            return Err(self.error(method, "paramètre de type indéterminé"));
        }
        Ok(mapping)
    }
    fn validate_body_contracts(&self, template: &Template) -> Result<(), Error> {
        for (index, node) in self.tree.syntax.nodes.iter().enumerate() {
            if node.kind != "appel méthode" { continue; }
            let id = NodeId(index);
            if !template.implementations.iter().any(|&implementation| {
                let outer = self.span(implementation);
                let inner = self.span(id);
                inner.start >= outer.start && inner.end <= outer.end
            }) { continue; }
            let Some(ty) = self.infer(node.children[0], 0) else { continue; };
            let owner = strip_reference(&ty);
            if !template.parameters.iter().any(|parameter| parameter == owner) { continue; }
            let guaranteed = self.tree.syntax.nodes[template.node.0].children.iter().copied()
                .filter(|&id| self.tree.syntax.nodes[id.0].kind == "annotation")
                .flat_map(|id| self.tree.syntax.nodes[id.0].children.iter().copied())
                .filter(|&id| matches!(self.tree.syntax.nodes[id.0].kind, "type avec" | "type exact") && self.name(id) == owner)
                .flat_map(|id| self.tree.syntax.nodes[id.0].children.iter().copied())
                .any(|method| self.name(method) == self.name(id));
            if !guaranteed { return Err(self.error(id, "méthode absente du contrat du type générique")); }
        }
        Ok(())
    }

    fn constraints(&self, template: &Template, mapping: &mut BTreeMap<String, String>) -> Result<(), Error> {
        for &annotation in &self.tree.syntax.nodes[template.node.0].children {
            let annotation_node = &self.tree.syntax.nodes[annotation.0];
            if annotation_node.kind != "annotation" { continue; }
            let contract = annotation_node.children.iter().copied()
                .find(|&id| matches!(self.tree.syntax.nodes[id.0].kind, "type avec" | "type exact"));
            let Some(contract) = contract else { continue; };
            let actual_type = mapping.get(self.name(contract)).cloned()
                .ok_or_else(|| self.error(contract, "type concret du contrat indéterminé"))?;
            let mut required_count = 0;
            for &required in &self.tree.syntax.nodes[contract.0].children {
                let concrete = self.method(&actual_type, self.name(required))
                    .ok_or_else(|| self.error(contract, "méthode exigée par le contrat absente"))?;
                required_count += 1;
                let required_node = &self.tree.syntax.nodes[required.0];
                let concrete_node = &self.tree.syntax.nodes[concrete.0];
                if required_node.kind != concrete_node.kind { return Err(self.error(concrete, "mode async du contrat incompatible")); }
                let expected = method_signature(self.source, self.tree, required);
                let actual = method_signature(self.source, self.tree, concrete);
                if expected.len() != actual.len() { return Err(self.error(concrete, "signature du contrat incompatible")); }
                for (expected, actual) in expected.iter().zip(&actual) {
                    unify(expected, actual, &template.parameters, mapping)
                        .map_err(|message| self.error(concrete, message))?;
                }
            }
            if self.tree.syntax.nodes[contract.0].kind == "type exact" {
                let count = self.tree.syntax.nodes[self.tree.syntax.root.0].children.iter().copied()
                    .filter(|&id| self.tree.syntax.nodes[id.0].kind == "impl" && self.name(id) == actual_type)
                    .flat_map(|id| &self.tree.syntax.nodes[id.0].children)
                    .filter(|id| matches!(self.tree.syntax.nodes[id.0].kind, "fn" | "async fn") && self.name(**id) != "drop").count();
                if count != required_count { return Err(self.error(contract, "méthodes supplémentaires interdites par le contrat exact")); }
            }
        }
        for &annotation in &self.tree.syntax.nodes[template.node.0].children {
            if self.tree.syntax.nodes[annotation.0].kind != "annotation" { continue; }
            for &property in &self.tree.syntax.nodes[annotation.0].children {
                let property_node = &self.tree.syntax.nodes[property.0];
                if property_node.kind != "paramètre de type" || property_node.children.is_empty() { continue; }
                let Some(actual) = mapping.get(self.name(property)) else { continue; };
                if !property_node.children.iter().any(|&id| normalize(&self.text(id)) == normalize(actual)) {
                    return Err(self.error(property, "type interdit par les alternatives du contrat"));
                }
            }
        }
        Ok(())
    }
    fn render(&self, id: NodeId, template: &Template, mapping: &BTreeMap<String, String>, name: &str) -> String {
        let node = &self.tree.syntax.nodes[id.0];
        let mut result = String::new();
        let mut cursor = self.span(id).start;
        let mut skip_until = 0;
        let annotations = node.children.iter().copied().filter(|&id| self.tree.syntax.nodes[id.0].kind == "annotation")
            .map(|id| self.span(id)).collect::<Vec<_>>();
        for token in node.start..node.end {
            let span = self.tree.tokens[token].span;
            if span.start < skip_until { continue; }
            if let Some(annotation) = annotations.iter().find(|annotation| annotation.start == span.start) {
                result.push_str(&self.source[cursor..span.start]);
                cursor = annotation.end;
                skip_until = cursor;
                continue;
            }
            let word = self.word(token);
            let is_owner = word == template.name || word == "Self"
                || mapping.get(word).is_some_and(|value| value.starts_with("__corbo_specialized_"));
            let replacement = if word == template.name || word == "Self" { Some(name) }
                else { mapping.get(word).map(String::as_str) };
            if let Some(replacement) = replacement {
                result.push_str(&self.source[cursor..span.start]);
                result.push_str(replacement);
                cursor = span.end;
                if is_owner && self.word(token + 1) == "<" {
                    let mut end = token + 2;
                    let mut depth = 1;
                    while depth > 0 {
                        match self.word(end) { "<" => depth += 1, ">" => depth -= 1, _ => {} }
                        end += 1;
                    }
                    cursor = self.tree.tokens[end - 1].span.end;
                    skip_until = cursor;
                }
            }
        }
        result.push_str(&self.source[cursor..self.span(id).end]);
        result
    }
}

fn generic_parts(text: &str) -> Option<(String, Vec<String>)> {
    let (owner, rest) = text.split_once('<')?;
    let rest = rest.strip_suffix('>')?;
    let mut depth = 0;
    let mut start = 0;
    let mut arguments = Vec::new();
    for (index, ch) in rest.char_indices() {
        match ch {
            '<' | '[' | '(' => depth += 1,
            '>' | ']' | ')' => depth -= 1,
            ',' if depth == 0 => {
                arguments.push(rest[start..index].trim().to_owned());
                start = index + 1;
            }
            _ => {}
        }
    }
    arguments.push(rest[start..].trim().to_owned());
    Some((owner.trim().to_owned(), arguments))
}

fn strip_reference(ty: &str) -> &str {
    ty.strip_prefix('&').unwrap_or(ty).trim_start().strip_prefix("mut ").unwrap_or(ty.strip_prefix('&').unwrap_or(ty).trim_start())
}

fn spelling(source: &str, tree: &StaticTree, token: usize) -> String {
    let span = tree.tokens[token].span;
    source[span.start..span.end].to_owned()
}

fn method_signature(source: &str, tree: &StaticTree, id: NodeId) -> Vec<String> {
    let node = &tree.syntax.nodes[id.0];
    let mut types = Vec::new();
    for &child in &node.children {
        let child = &tree.syntax.nodes[child.0];
        if child.kind == "paramètre" {
            if let Some(ty) = child.children.first() {
                let ty = &tree.syntax.nodes[ty.0];
                types.push((ty.start..ty.end).map(|i| spelling(source, tree, i)).collect::<Vec<_>>().join(" "));
            } else {
                let receiver = (child.start..child.end).map(|i| spelling(source, tree, i)).collect::<Vec<_>>().join(" ");
                types.push(if receiver.contains("& mut") { "&mut Self" } else if receiver.contains('&') { "&Self" } else { "Self" }.to_owned());
            }
        } else if child.kind == "type" {
            types.push((child.start..child.end).map(|i| spelling(source, tree, i)).collect::<Vec<_>>().join(" "));
            return types;
        }
    }
    types.push("()".to_owned());
    types
}

fn unify(pattern: &str, actual: &str, parameters: &[String], mapping: &mut BTreeMap<String, String>) -> Result<(), &'static str> {
    let pattern_tokens = crate::lexer::lex(pattern).map_err(|_| "type du contrat invalide")?;
    let actual_tokens = crate::lexer::lex(actual).map_err(|_| "type concret invalide")?;
    fn unify_tokens(pattern: &str, p: &[crate::lexer::Token], actual: &str, a: &[crate::lexer::Token], parameters: &[String], mapping: &mut BTreeMap<String, String>) -> Result<(), &'static str> {
        let p = p.iter().filter(|token| token.span.start != token.span.end).collect::<Vec<_>>();
        let a = a.iter().filter(|token| token.span.start != token.span.end).collect::<Vec<_>>();
        let mut pi = 0;
        let mut ai = 0;
        while pi < p.len() {
            let word = &pattern[p[pi].span.start..p[pi].span.end];
            if parameters.iter().any(|parameter| parameter == word) {
                let mut end = ai;
                let mut depth: i32 = 0;
                while end < a.len() {
                    let next = &actual[a[end].span.start..a[end].span.end];
                    if depth == 0 && matches!(next, "," | ">" | "]" | ";" | ")") { break; }
                    if matches!(next, "<" | "[" | "(") { depth += 1; }
                    if matches!(next, ">" | "]" | ")") { depth -= 1; }
                    end += 1;
                }
                if end == ai { return Err("type du contrat incompatible"); }
                let value = actual[a[ai].span.start..a[end - 1].span.end].to_owned();
                if let Some(previous) = mapping.get(word) {
                    if normalize(previous) != normalize(&value) { return Err("types du contrat incohérents"); }
                } else { mapping.insert(word.to_owned(), value); }
                ai = end;
            } else {
                let Some(token) = a.get(ai) else { return Err("type du contrat incompatible"); };
                if word != &actual[token.span.start..token.span.end] && word != "Self" { return Err("type du contrat incompatible"); }
                ai += 1;
            }
            pi += 1;
        }
        if ai != a.len() { return Err("type du contrat incompatible"); }
        Ok(())
    }
    unify_tokens(pattern, &pattern_tokens, actual, &actual_tokens, parameters, mapping)
}
fn normalize(text: &str) -> String { text.chars().filter(|c| !c.is_whitespace()).collect() }
fn substitute_type(text: &str, mapping: &BTreeMap<String, String>) -> String {
    let Ok(tokens) = crate::lexer::lex(text) else { return text.to_owned(); };
    let mut result = String::new();
    let mut cursor = 0;
    for token in tokens {
        if let Some(replacement) = mapping.get(&text[token.span.start..token.span.end]) {
            result.push_str(&text[cursor..token.span.start]);
            result.push_str(replacement);
            cursor = token.span.end;
        }
    }
    result.push_str(&text[cursor..]);
    result
}

fn emit_instance(resolver: &Resolver<'_>, template_index: usize, mapping: &BTreeMap<String, String>,
    instances: &mut Vec<(usize, BTreeMap<String, String>, String)>, generated: &mut String,
    ranges: &mut Vec<(std::ops::Range<usize>, std::ops::Range<usize>)>,
    layouts: &mut Vec<(String, String, std::ops::Range<usize>)>, depth: usize) -> Result<String, Error> {
    let template = &resolver.templates[template_index];
    if depth >= 128 { return Err(resolver.error(template.node, "spécialisation générique récursive hors limites")); }
    if let Some((_, _, name)) = instances.iter().find(|(index, old, _)| *index == template_index
        && old.len() == mapping.len() && old.iter().all(|(key, value)| mapping.get(key).is_some_and(|new| normalize(value) == normalize(new)))) {
        return Ok(name.clone());
    }
    let name = format!("__corbo_specialized_{}_{}", template.name, instances.len());
    instances.push((template_index, mapping.clone(), name.clone()));
    let mut substitutions = mapping.clone();
    for (index, node) in resolver.tree.syntax.nodes.iter().enumerate() {
        let id = NodeId(index);
        if node.kind != "type" || node.children.is_empty() { continue; }
        let span = resolver.span(id);
        let belongs = std::iter::once(&template.node).chain(template.implementations.iter()).any(|&part| {
            let part = resolver.span(part);
            span.start >= part.start && span.end <= part.end
        });
        if !belongs { continue; }
        let Some((dependency_index, dependency)) = resolver.templates.iter().enumerate()
            .find(|(index, other)| *index != template_index && other.name == resolver.name(id)) else { continue; };
        if node.children.len() != dependency.parameters.len() { return Err(resolver.error(id, "nombre de paramètres de type incompatible")); }
        let mut types = dependency.parameters.iter().cloned().zip(node.children.iter()
            .map(|&id| substitute_type(&resolver.text(id), mapping))).collect();
        resolver.constraints(dependency, &mut types)?;
        let concrete = emit_instance(resolver, dependency_index, &types, instances, generated, ranges, layouts, depth + 1)?;
        if substitutions.get(&dependency.name).is_some_and(|old| old != &concrete) {
            return Err(resolver.error(id, "plusieurs spécialisations du même type dans un gabarit à distinguer"));
        }
        substitutions.insert(dependency.name.clone(), concrete);
    }
    generated.push('\n');
    let start = generated.len();
    generated.push_str(&resolver.render(template.node, template, &substitutions, &name));
    let layout_index = layouts.len();
    layouts.push((template.name.clone(), name.clone(), start..generated.len()));
    for &implementation in &template.implementations {
        generated.push('\n');
        let start = generated.len();
        generated.push_str(&resolver.render(implementation, template, &substitutions, &name));
        let original = resolver.span(implementation);
        ranges.push((start..generated.len(), original.start..original.end));
    }
    layouts[layout_index].2.end = generated.len();
    Ok(name)
}

pub(crate) fn specialize(source: &str, tree: &StaticTree) -> Result<Option<Expansion>, Error> {
    let mut resolver = Resolver { source, tree, templates: vec![], uses: tree.points.iter().filter_map(|point| {
        if let Fact::Use { binding: Some(binding) } = point.fact { Some((point.syntax, binding.0)) } else { None }
    }).collect() };
    let items = &tree.syntax.nodes[tree.syntax.root.0].children;
    for &id in items {
        let node = &tree.syntax.nodes[id.0];
        if !matches!(node.kind, "struct" | "enum") { continue; }
        let mut parameters = node.children.iter().copied().filter(|&id| tree.syntax.nodes[id.0].kind == "type libre")
            .map(|id| resolver.name(id).to_owned()).collect::<Vec<_>>();
        if parameters.is_empty() {
            for &annotation in &node.children {
                if tree.syntax.nodes[annotation.0].kind != "annotation" { continue; }
                for &property in &tree.syntax.nodes[annotation.0].children {
                    if matches!(tree.syntax.nodes[property.0].kind, "type libre" | "type avec" | "type exact") {
                        let name = resolver.name(property).to_owned();
                        if !parameters.contains(&name) { parameters.push(name); }
                    }
                }
            }
        }
        if parameters.is_empty() { continue; }
        let name = resolver.name(id).to_owned();
        let implementations = items.iter().copied().filter(|&id| tree.syntax.nodes[id.0].kind == "impl" && resolver.name(id) == name).collect();
        resolver.templates.push(Template { node: id, name, parameters, implementations });
    }
    if resolver.templates.is_empty() { return Ok(None); }
    for template in &resolver.templates { resolver.validate_body_contracts(template)?; }
    let mut edits = BTreeMap::new();
    let mut generated = String::new();
    let mut instances = Vec::<(usize, BTreeMap<String, String>, String)>::new();
    let mut generated_ranges = Vec::new();
    let mut layouts = Vec::new();
    for (index, node) in tree.syntax.nodes.iter().enumerate() {
        let id = NodeId(index);
        if resolver.in_template(id) { continue; }
        let (template_index, _template, mapping, selected_span, suffix) = if node.kind == "appel" {
            let callee = node.children[0];
            if tree.syntax.nodes[callee.0].kind != "nom qualifié" { continue; }
            let parts = resolver.text(callee);
            let Some((owner, method)) = parts.rsplit_once("::") else { continue; };
            let explicit = generic_parts(owner);
            let generic_name = explicit.as_ref().map_or(owner, |(name, _)| name.as_str());
            let Some((template_index, template)) = resolver.templates.iter().enumerate().find(|(_, t)| t.name == generic_name) else { continue; };
            let method_node = resolver.method(generic_name, method).ok_or_else(|| resolver.error(callee, "méthode du type générique absente"))?;
            let mapping = resolver.arguments(template, method_node, &node.children[1..])?;
            if let Some((_, explicit)) = explicit {
                if explicit.len() != template.parameters.len() || template.parameters.iter().zip(explicit).any(|(name, ty)| {
                    mapping.get(name).is_none_or(|actual| normalize(actual) != normalize(&ty))
                }) { return Err(resolver.error(callee, "arguments de type incompatibles avec le constructeur")); }
            }
            (template_index, template, mapping, resolver.span(callee), format!("::{method}"))
        } else if node.kind == "construction" {
            let Some((index, template)) = resolver.templates.iter().enumerate().find(|(_, template)| {
                resolver.tree.syntax.nodes[template.node.0].kind == "struct" && template.name == resolver.name(id)
            }) else { continue; };
            let mut mapping = BTreeMap::new();
            for &field in &node.children {
                if tree.syntax.nodes[field.0].kind != "champ" { continue; }
                let declared = tree.syntax.nodes[template.node.0].children.iter().copied()
                    .find(|&member| tree.syntax.nodes[member.0].kind == "champ" && resolver.name(member) == resolver.name(field))
                    .ok_or_else(|| resolver.error(field, "champ inconnu"))?;
                let value = tree.syntax.nodes[field.0].children[0];
                let actual = resolver.infer(value, 0).ok_or_else(|| resolver.error(value, "type du champ générique indéterminé"))?;
                unify(&resolver.text(tree.syntax.nodes[declared.0].children[0]), &actual, &template.parameters, &mut mapping)
                    .map_err(|message| resolver.error(field, message))?;
            }
            resolver.constraints(template, &mut mapping)?;
            if template.parameters.iter().any(|parameter| !mapping.contains_key(parameter)) {
                return Err(resolver.error(id, "paramètre de type indéterminé"));
            }
            (index, template, mapping, tree.tokens[node.start].span, String::new())
        } else if node.kind == "type" && !node.children.is_empty() {
            let Some((index, template)) = resolver.templates.iter().enumerate().find(|(_, template)| template.name == resolver.name(id)) else { continue; };
            if node.children.len() != template.parameters.len() { return Err(resolver.error(id, "nombre de paramètres de type incompatible")); }
            let mut mapping = template.parameters.iter().cloned().zip(node.children.iter().map(|&id| resolver.text(id))).collect();
            resolver.constraints(template, &mut mapping)?;
            (index, template, mapping, resolver.span(id), String::new())
        } else if matches!(node.kind, "motif variante" | "motif variante positionnelle" | "motif unité") {
            let Some((index, template)) = resolver.templates.iter().enumerate()
                .find(|(_, template)| resolver.tree.syntax.nodes[template.node.0].kind == "enum"
                    && template.name == resolver.word(node.start)) else { continue; };
            let ty = resolver.matched_type(id).ok_or_else(|| resolver.error(id, "type du motif générique indéterminé"))?;
            let (owner, arguments) = generic_parts(&ty).ok_or_else(|| resolver.error(id, "type du motif générique incompatible"))?;
            if owner != template.name || arguments.len() != template.parameters.len() {
                return Err(resolver.error(id, "type du motif générique incompatible"));
            }
            let mapping = template.parameters.iter().cloned().zip(arguments).collect();
            (index, template, mapping, tree.tokens[node.start].span, String::new())
        } else { continue; };
        let name = emit_instance(&resolver, template_index, &mapping, &mut instances,
            &mut generated, &mut generated_ranges, &mut layouts, 0)?;
        edits.insert(selected_span.start, (selected_span.end, format!("{name}{suffix}")));
    }
    for template in &resolver.templates {
        for &id in std::iter::once(&template.node).chain(template.implementations.iter()) {
            let span = resolver.span(id);
            edits.insert(span.start, (span.end, String::new()));
        }
    }
    let mut result = Vec::new();
    let mut offsets = vec![0; source.len() + 1];
    let mut cursor = 0;
    for (start, (end, replacement)) in edits {
        if start < cursor { continue; }
        for position in cursor..start {
            offsets[position] = result.len();
            result.push(source.as_bytes()[position]);
        }
        for offset in &mut offsets[start..end] { *offset = result.len(); }
        result.extend_from_slice(replacement.as_bytes());
        cursor = end;
    }
    for position in cursor..source.len() {
        offsets[position] = result.len();
        result.push(source.as_bytes()[position]);
    }
    offsets[source.len()] = result.len();
    let start = result.len();
    for (range, _) in &mut generated_ranges { range.start += start; range.end += start; }
    for (_, _, range) in &mut layouts { range.start += start; range.end += start; }
    result.extend_from_slice(generated.as_bytes());
    Ok(Some(Expansion {
        source: String::from_utf8(result).expect("token-boundary substitutions preserve UTF-8"),
        offsets, generated_ranges, layouts,
    }))
}
