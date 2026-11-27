use crate::{
    legacy_parser::{NodeId, Syntax},
    lexer::Token,
};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ScopeId(pub usize);
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct BindingId(pub usize);
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct PointId(pub usize);
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct CaptureId(pub usize);

#[derive(Debug)]
pub struct Scope {
    pub parent: Option<ScopeId>,
    pub children: Vec<ScopeId>,
    pub syntax: NodeId,
    pub entry: Option<PointId>,
    pub bindings: Vec<BindingId>,
    pub exits: Vec<PointId>,
}

#[derive(Debug)]
pub struct Binding {
    pub name: String,
    pub syntax: NodeId,
    pub scope: ScopeId,
    pub mutable: bool,
    pub ty: Option<NodeId>,
    pub initializer: Option<NodeId>,
}

#[derive(Debug)]
pub struct Point {
    pub syntax: NodeId,
    pub scope: ScopeId,
    pub operands: Vec<PointId>,
    pub fact: Fact,
}

#[derive(Debug)]
pub struct Capture {
    pub source: BindingId,
    pub closure: NodeId,
}

#[derive(Debug)]
pub enum Fact {
    Syntax,
    Use {
        binding: Option<BindingId>,
    },
    NamedMove {
        source: Option<BindingId>,
        destination: BindingId,
    },
    Borrow {
        mutable: bool,
        place: NodeId,
    },
    Pool {
        element_type: NodeId,
        capacity: NodeId,
    },
    AddressCandidate {
        pool: NodeId,
        arguments: Vec<NodeId>,
    },
    Collection {
        members: Vec<NodeId>,
    },
    Capture {
        fields: Vec<CaptureId>,
        moving: bool,
    },
    Exit {
        destination: Option<NodeId>,
        value: Option<NodeId>,
    },
    Await {
        subject: NodeId,
    },
    Propagate {
        subject: NodeId,
        destination: Option<NodeId>,
    },
    Projection {
        base: NodeId,
        selectors: Vec<NodeId>,
    },
    Call {
        callee_or_receiver: NodeId,
        arguments: Vec<NodeId>,
    },
    Write {
        place: NodeId,
        right: NodeId,
    },
    Branch {
        subject: NodeId,
        alternatives: Vec<NodeId>,
    },
    Suspend,
    EndOfScope,
}

#[derive(Debug)]
pub struct StaticTree {
    pub(crate) std_env_range: std::ops::Range<usize>,
    pub(crate) std_socket_wait_ranges: Vec<std::ops::Range<usize>>,
    pub(crate) std_async_io_ranges: Vec<std::ops::Range<usize>>,
    pub(crate) std_file_range: std::ops::Range<usize>,
    pub(crate) opaque_layouts: crate::package::OpaqueLayouts,
    pub(crate) target: crate::target::Target,
    pub tokens: Vec<Token>,
    pub syntax: Syntax,
    pub scopes: Vec<Scope>,
    pub bindings: Vec<Binding>,
    pub points: Vec<Point>,
    pub captures: Vec<Capture>,
}

impl StaticTree {
    pub fn from_syntax(source: &str, tokens: Vec<Token>, syntax: Syntax) -> Self {
        let mut tree = Self {
            std_env_range: 0..0,
            std_socket_wait_ranges: Vec::new(),
            std_async_io_ranges: Vec::new(),
            std_file_range: 0..0,
            opaque_layouts: Default::default(),
            target: crate::target::Target::host(),
            tokens,
            syntax,
            scopes: vec![],
            bindings: vec![],
            points: vec![],
            captures: vec![],
        };
        let root = tree.syntax.root;
        let scope = tree.scope(root, None, None);
        tree.visit(source, root, scope, &mut HashMap::new(), None, None);
        for (index, scope) in tree.scopes.iter_mut().enumerate().skip(1) {
            let end = PointId(tree.points.len());
            tree.points.push(Point {
                syntax: scope.syntax,
                scope: ScopeId(index),
                operands: vec![],
                fact: Fact::EndOfScope,
            });
            scope.exits.push(end);
        }
        tree
    }

    fn scope(
        &mut self,
        syntax: NodeId,
        parent: Option<ScopeId>,
        entry: Option<PointId>,
    ) -> ScopeId {
        let id = ScopeId(self.scopes.len());
        self.scopes.push(Scope {
            parent,
            syntax,
            entry,
            children: vec![],
            bindings: vec![],
            exits: vec![],
        });
        if let Some(parent) = parent {
            self.scopes[parent.0].children.push(id);
        }
        id
    }

    fn text<'a>(&self, source: &'a str, token: usize) -> &'a str {
        let span = self.tokens[token].span;
        &source[span.start..span.end]
    }

    fn bind(
        &mut self,
        source: &str,
        syntax: NodeId,
        scope: ScopeId,
        env: &mut HashMap<String, BindingId>,
    ) -> Option<BindingId> {
        let node = &self.syntax.nodes[syntax.0];
        let name_token = node.name?;
        let name = self.text(source, name_token);
        if name == "_" {
            return None;
        }
        let mutable = (node.start..name_token).any(|token| self.text(source, token) == "mut");
        let ty = node
            .children
            .iter()
            .find(|id| self.syntax.nodes[id.0].kind == "type")
            .copied();
        let initializer = (node.kind == "liaison")
            .then(|| node.children.last().copied())
            .flatten();
        let id = BindingId(self.bindings.len());
        self.bindings.push(Binding {
            name: name.to_owned(),
            syntax,
            scope,
            mutable,
            ty,
            initializer,
        });
        self.scopes[scope.0].bindings.push(id);
        env.insert(name.to_owned(), id);
        Some(id)
    }

    fn visit(
        &mut self,
        source: &str,
        id: NodeId,
        scope: ScopeId,
        env: &mut HashMap<String, BindingId>,
        function: Option<NodeId>,
        loop_target: Option<NodeId>,
    ) -> PointId {
        let node = &self.syntax.nodes[id.0];
        let (kind, start, name, children) =
            (node.kind, node.start, node.name, node.children.clone());
        let name = name
            .map(|token| self.text(source, token))
            .or_else(|| node.asm_operand.map(|span| &source[span.start..span.end]));
        let point = PointId(self.points.len());
        self.points.push(Point {
            syntax: id,
            scope,
            operands: vec![],
            fact: Fact::Syntax,
        });
        let mut scope = scope;
        let mut function = function;
        let mut loop_target = loop_target;
        let mut local;
        let env = if matches!(
            kind,
            "scope" | "fn" | "async fn" | "extern" | "closure" | "bras" | "while" | "loop"
        ) {
            if kind == "scope"
                && (self.scopes[scope.0].syntax == id
                    || (self.syntax.nodes[self.scopes[scope.0].syntax.0].kind == "while"
                        && self.syntax.nodes[self.scopes[scope.0].syntax.0]
                            .children
                            .last()
                            == Some(&id)))
            {
                env
            } else {
                let scope_node = if kind == "while" || kind == "scope" {
                    id
                } else {
                    children
                        .last()
                        .copied()
                        .filter(|child| self.syntax.nodes[child.0].kind == "scope")
                        .unwrap_or(id)
                };
                scope = self.scope(scope_node, Some(scope), Some(point));
                local = env.clone();
                &mut local
            }
        } else {
            env
        };
        self.points[point.0].scope = scope;
        if matches!(kind, "fn" | "async fn" | "closure") {
            function = Some(id);
            loop_target = None;
        }
        if matches!(kind, "while" | "loop") {
            loop_target = Some(id);
        }
        if kind == "move nommé" {
            let from = name.and_then(|name| env.get(name)).copied();
            if let Some(destination) = self.bind(source, id, scope, env) {
                self.points[point.0].fact = Fact::NamedMove {
                    source: from,
                    destination,
                };
            }
            return point;
        }
        let first_child_point = self.points.len();
        let operands = children
            .iter()
            .map(|child| self.visit(source, *child, scope, env, function, loop_target))
            .collect();
        let fact = match kind {
            "nom" | "opérande asm" => Fact::Use {
                binding: name.and_then(|name| env.get(name)).copied(),
            },
            "liaison" | "paramètre" | "tuple binding" => {
                self.bind(source, id, scope, env);
                Fact::Syntax
            }
            "motif nom"
                if self.syntax.nodes[id.0].children.is_empty()
                    && name
                        .is_some_and(|name| name.starts_with(|c: char| c.is_ascii_lowercase())) =>
            {
                self.bind(source, id, scope, env);
                Fact::Syntax
            }
            "emprunt" => Fact::Borrow {
                mutable: self.text(source, start + 1) == "mut",
                place: children[0],
            },
            "pool" => Fact::Pool {
                element_type: children[0],
                capacity: children[1],
            },
            "appel méthode" if name == Some("new") => Fact::AddressCandidate {
                pool: children[0],
                arguments: children[1..].to_vec(),
            },
            "appel" | "appel méthode" => Fact::Call {
                callee_or_receiver: children[0],
                arguments: children[1..].to_vec(),
            },
            "affectation" => Fact::Write {
                place: children[0],
                right: children[1],
            },
            "if" | "match" | "while" => Fact::Branch {
                subject: children[0],
                alternatives: children[1..].to_vec(),
            },
            "yield" => Fact::Suspend,
            "tableau" | "tableau répété" | "construction" => Fact::Collection {
                members: children.clone(),
            },
            "indice" | "projection" | "indirection" => Fact::Projection {
                base: children[0],
                selectors: children[1..].to_vec(),
            },
            "closure" => {
                let mut sources = self.points[first_child_point..]
                    .iter()
                    .filter_map(|point| match point.fact {
                        Fact::Use {
                            binding: Some(binding),
                        } if self.bindings[binding.0].scope.0 < scope.0 => Some(binding),
                        _ => None,
                    })
                    .collect::<Vec<_>>();
                sources.sort_by_key(|binding| binding.0);
                sources.dedup();
                let fields = sources
                    .into_iter()
                    .map(|source| {
                        let capture = CaptureId(self.captures.len());
                        self.captures.push(Capture {
                            source,
                            closure: id,
                        });
                        capture
                    })
                    .collect();
                Fact::Capture {
                    fields,
                    moving: name == Some("move"),
                }
            }
            "return" | "break" | "continue" | "résultat" => {
                self.scopes[scope.0].exits.push(point);
                Fact::Exit {
                    destination: match kind {
                        "return" => function,
                        "break" | "continue" => loop_target,
                        _ => None,
                    },
                    value: children.first().copied(),
                }
            }
            "await" => Fact::Await {
                subject: children[0],
            },
            "propagation" => {
                self.scopes[scope.0].exits.push(point);
                Fact::Propagate {
                    subject: children[0],
                    destination: function,
                }
            }
            _ => Fact::Syntax,
        };
        self.points[point.0].operands = operands;
        self.points[point.0].fact = fact;
        point
    }
}
