//! Control flow and backward binding liveness for the synchronous verifier.

use crate::{
    parser::NodeId,
    tree::{BindingId, Fact, StaticTree},
};
use std::collections::{HashMap, HashSet, VecDeque};

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
struct FlowId(usize);

#[derive(Default)]
struct Point {
    successors: Vec<FlowId>,
    reads: Vec<(BindingId, NodeId)>,
    defines: Vec<BindingId>,
}

#[derive(Clone, Copy)]
struct Targets {
    repeat: FlowId,
    exit: FlowId,
}

pub(crate) struct Flow {
    before: HashMap<NodeId, FlowId>,
    write: HashMap<NodeId, FlowId>,
    live: Vec<HashSet<(BindingId, NodeId)>>,
}

impl Flow {
    pub(crate) fn build(tree: &StaticTree, source: &str) -> Self {
        let mut builder = Builder {
            tree,
            source,
            points: vec![Point::default()],
            before: HashMap::new(),
            write: HashMap::new(),
            uses: tree
                .points
                .iter()
                .filter_map(|point| match point.fact {
                    Fact::Use {
                        binding: Some(binding),
                    } => Some((point.syntax, binding)),
                    _ => None,
                })
                .collect(),
            bindings: tree
                .bindings
                .iter()
                .enumerate()
                .map(|(index, binding)| (binding.syntax, BindingId(index)))
                .collect(),
            moves: tree
                .points
                .iter()
                .filter_map(|point| match point.fact {
                    Fact::NamedMove {
                        source,
                        destination,
                    } => Some((point.syntax, (source, destination))),
                    _ => None,
                })
                .collect(),
        };
        let functions = tree.syntax.nodes[tree.syntax.root.0].children.iter().flat_map(|id| {
            let node = &tree.syntax.nodes[id.0];
            if node.kind == "impl" {
                node.children.as_slice()
            } else {
                std::slice::from_ref(id)
            }
        });
        for &function in functions {
            let node = &tree.syntax.nodes[function.0];
            if matches!(node.kind, "fn" | "async fn") {
                if let Some(&body) = node.children.last() {
                    builder.node(body, FlowId(0), None);
                }
            }
        }
        let live = solve(&builder.points);
        Self {
            before: builder.before,
            write: builder.write,
            live,
        }
    }

    pub(crate) fn live_at(
        &self,
        node: NodeId,
        binding: BindingId,
        write: bool,
        relevant: impl Fn(NodeId) -> bool,
    ) -> bool {
        let points = if write { &self.write } else { &self.before };
        points.get(&node).is_none_or(|point| {
            self.live[point.0]
                .iter()
                .any(|&(candidate, use_id)| candidate == binding && relevant(use_id))
        })
    }
}

struct Builder<'a> {
    tree: &'a StaticTree,
    source: &'a str,
    points: Vec<Point>,
    before: HashMap<NodeId, FlowId>,
    write: HashMap<NodeId, FlowId>,
    uses: HashMap<NodeId, BindingId>,
    bindings: HashMap<NodeId, BindingId>,
    moves: HashMap<NodeId, (Option<BindingId>, BindingId)>,
}

impl Builder<'_> {
    fn point(
        &mut self,
        successors: Vec<FlowId>,
        reads: Vec<(BindingId, NodeId)>,
        defines: Vec<BindingId>,
    ) -> FlowId {
        let id = FlowId(self.points.len());
        self.points.push(Point {
            successors,
            reads,
            defines,
        });
        id
    }

    fn sequence(&mut self, children: &[NodeId], next: FlowId, targets: Option<Targets>) -> FlowId {
        children
            .iter()
            .rev()
            .fold(next, |next, &child| self.node(child, next, targets))
    }

    fn node(&mut self, id: NodeId, next: FlowId, targets: Option<Targets>) -> FlowId {
        let node = &self.tree.syntax.nodes[id.0];
        let children = &node.children;
        let entry = match node.kind {
            "nom" | "opérande asm" => self.point(
                vec![next],
                self.uses
                    .get(&id)
                    .map(|&binding| (binding, id))
                    .into_iter()
                    .collect(),
                vec![],
            ),
            "liaison" => {
                let definition = self.point(
                    vec![next],
                    vec![],
                    self.bindings.get(&id).copied().into_iter().collect(),
                );
                self.sequence(children, definition, targets)
            }
            "move nommé" => {
                let (source, destination) = self.moves.get(&id).copied().unzip();
                self.point(
                    vec![next],
                    source
                        .flatten()
                        .map(|binding| (binding, id))
                        .into_iter()
                        .collect(),
                    destination.into_iter().collect(),
                )
            }
            "affectation" => {
                let direct = self.uses.get(&children[0]).copied();
                let indirect = if self.tree.syntax.nodes[children[0].0].kind == "indirection" {
                    self.tree.syntax.nodes[children[0].0]
                        .children
                        .first()
                        .and_then(|operand| self.uses.get(operand))
                        .copied()
                } else {
                    None
                };
                let write = self.point(
                    vec![next],
                    indirect.map(|binding| (binding, id)).into_iter().collect(),
                    direct.into_iter().collect(),
                );
                self.write.insert(id, write);
                let right = self.node(children[1], write, targets);
                if direct.is_some() {
                    right
                } else {
                    self.node(children[0], right, targets)
                }
            }
            "binaire" if node.name.is_some_and(|token| {
                let span = self.tree.tokens[token].span;
                matches!(&self.source[span.start..span.end], "&&" | "||")
            }) => {
                let right = self.node(children[1], next, targets);
                let branch = self.point(vec![right, next], vec![], vec![]);
                self.node(children[0], branch, targets)
            }
            "if" => {
                let yes = self.node(children[1], next, targets);
                let no = children
                    .get(2)
                    .map_or(next, |&child| self.node(child, next, targets));
                let branch = self.point(vec![yes, no], vec![], vec![]);
                self.node(children[0], branch, targets)
            }
            "match" => {
                let arms = children[1..]
                    .iter()
                    .map(|&arm| self.node(arm, next, targets))
                    .collect();
                let branch = self.point(arms, vec![], vec![]);
                self.node(children[0], branch, targets)
            }
            "while" | "loop" => {
                let header = self.point(vec![], vec![], vec![]);
                let inner = Some(Targets {
                    repeat: header,
                    exit: next,
                });
                let body = self.node(*children.last().unwrap(), header, inner);
                let head = if node.kind == "while" {
                    let branch = self.point(vec![body, next], vec![], vec![]);
                    self.node(children[0], branch, inner)
                } else {
                    body
                };
                self.points[header.0].successors.push(head);
                header
            }
            "propagation" => {
                let branch = self.point(vec![next, FlowId(0)], vec![], vec![]);
                self.node(children[0], branch, targets)
            }
            "return" => self.sequence(children, FlowId(0), targets),
            "break" => self.sequence(
                children,
                targets.map_or(FlowId(0), |target| target.exit),
                targets,
            ),
            "continue" => targets.map_or(FlowId(0), |target| target.repeat),
            _ => self.sequence(children, next, targets),
        };
        self.before.insert(id, entry);
        entry
    }
}

fn solve(points: &[Point]) -> Vec<HashSet<(BindingId, NodeId)>> {
    let mut predecessors = vec![vec![]; points.len()];
    for (index, point) in points.iter().enumerate() {
        for successor in &point.successors {
            predecessors[successor.0].push(index);
        }
    }
    let mut live = vec![HashSet::new(); points.len()];
    let mut work = (0..points.len()).collect::<VecDeque<_>>();
    let mut queued = vec![true; points.len()];
    while let Some(index) = work.pop_front() {
        queued[index] = false;
        let point = &points[index];
        let mut next = point.reads.iter().copied().collect::<HashSet<_>>();
        next.extend(
            point
                .successors
                .iter()
                .flat_map(|id| live[id.0].iter().copied())
                .filter(|(binding, _)| !point.defines.contains(binding)),
        );
        if next == live[index] {
            continue;
        }
        live[index] = next;
        for &predecessor in &predecessors[index] {
            if !queued[predecessor] {
                queued[predecessor] = true;
                work.push_back(predecessor);
            }
        }
    }
    live
}
