//! Confinement of raw addresses to the unchecked block that creates them.

use super::*;
use std::collections::HashSet;

impl Checker<'_> {
    pub(super) fn check_raw_addresses(&self) -> Result<(), Error> {
        let mut users: HashMap<BindingId, Vec<NodeId>> = HashMap::new();
        for (&use_node, &binding) in &self.uses {
            users.entry(binding).or_default().push(use_node);
        }
        for (&node, &(source, _)) in &self.moves {
            users.entry(source).or_default().push(node);
        }
        let mut pending = Vec::new();
        for (index, call) in self.tree.syntax.nodes.iter().enumerate() {
            if call.kind != "appel" {
                continue;
            }
            let callee = call.children[0];
            if self.node(callee).kind == "nom"
                && self.name(callee) == Some("addr")
                && !self.uses.contains_key(&callee)
            {
                let site = NodeId(index);
                let scope = self
                    .raw_address_block(site)
                    .ok_or_else(|| self.error(site, "addr exige un bloc @unchecked"))?;
                pending.push((site, scope));
            }
        }
        let mut seen = HashSet::new();
        while let Some((value, boundary)) = pending.pop() {
            if !seen.insert((value, boundary)) {
                continue;
            }
            let escape = |at| {
                self.error(
                    at,
                    "l’adresse brute ne peut pas sortir de son bloc @unchecked",
                )
            };
            let Some(&parent) = self.syntax_parents.get(&value) else {
                return Err(escape(value));
            };
            if parent == boundary {
                return Err(escape(value));
            }
            let node = self.node(parent);
            let mut bindings = Vec::new();
            if let Some(&(_, destination)) = self.moves.get(&value) {
                bindings.push(destination);
            } else {
                match node.kind {
                    "liaison" => bindings.push(self.bindings[&parent]),
                    "tuple let" => {
                        bindings.extend(
                            node.children
                                .iter()
                                .filter_map(|name| self.bindings.get(name).copied()),
                        );
                    }
                    "affectation" => {
                        let mut place = node.children[0];
                        while matches!(self.node(place).kind, "projection" | "indice" | "groupe") {
                            place = self.node(place).children[0];
                        }
                        bindings.push(*self.uses.get(&place).ok_or_else(|| escape(parent))?);
                    }
                    "return" | "closure" | "fn" | "async fn" | "yield" | "await" => {
                        return Err(escape(parent));
                    }
                    "break" => {
                        let mut target = parent;
                        loop {
                            target = *self
                                .syntax_parents
                                .get(&target)
                                .ok_or_else(|| escape(parent))?;
                            if target == boundary {
                                return Err(escape(parent));
                            }
                            if self.node(target).kind == "loop" {
                                pending.push((target, boundary));
                                break;
                            }
                        }
                    }
                    "appel" => {
                        let callee = node.children[0];
                        let primitive = self.node(callee).kind == "nom"
                            && !self.uses.contains_key(&callee)
                            && self.function_index(parent).is_none();
                        if primitive && self.name(callee) == Some("copy") {
                            pending.push((parent, boundary));
                        } else if !(primitive && self.name(callee) == Some("drop"))
                            && !self.runtime_call(parent, "complete_socket")
                        {
                            return Err(escape(parent));
                        }
                    }
                    "appel méthode" => return Err(escape(parent)),
                    "asm" | "instruction" => {}
                    "match" if node.children[0] == value => {
                        let mut patterns = node.children[1..]
                            .iter()
                            .map(|&arm| self.node(arm).children[0])
                            .collect::<Vec<_>>();
                        while let Some(pattern) = patterns.pop() {
                            if let Some(&binding) = self.bindings.get(&pattern) {
                                bindings.push(binding);
                            }
                            patterns.extend(&self.node(pattern).children);
                        }
                        pending.push((parent, boundary));
                    }
                    _ => pending.push((parent, boundary)),
                }
            }
            for binding in bindings {
                if !self.raw_address_within(self.tree.bindings[binding.0].syntax, boundary) {
                    return Err(escape(parent));
                }
                if let Some(uses) = users.get(&binding) {
                    pending.extend(uses.iter().map(|&id| (id, boundary)));
                }
            }
        }
        Ok(())
    }

    fn raw_address_block(&self, mut node: NodeId) -> Option<NodeId> {
        while let Some(&parent) = self.syntax_parents.get(&node) {
            match self.node(parent).kind {
                "unchecked" => return Some(parent),
                "fn" | "async fn" | "closure" => return None,
                _ => node = parent,
            }
        }
        None
    }

    fn raw_address_within(&self, mut node: NodeId, boundary: NodeId) -> bool {
        while let Some(&parent) = self.syntax_parents.get(&node) {
            if parent == boundary {
                return true;
            }
            if matches!(self.node(parent).kind, "fn" | "async fn" | "closure") {
                return false;
            }
            node = parent;
        }
        false
    }
}
