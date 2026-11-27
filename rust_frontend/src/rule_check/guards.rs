//! Canonical shared decision graphs over resolved predicates. Unknowns remain
//! symbolic; neither path combinations nor generic specializations are enumerated.
use crate::post_ast::*;
use std::{
    cell::RefCell,
    collections::{HashMap, HashSet},
    hash::{Hash, Hasher},
    rc::Rc,
};
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub(super) enum Atom {
    Boolean(ValueId),
    Variant(ValueId, VariantId),
    Other(PredicateId),
    Copies(TypeId),
    VariantPath(ValueId, Vec<u64>, VariantId),
}
#[derive(Clone, Debug)]
struct Node {
    atom: Atom,
    low: u32,
    high: u32,
}
#[derive(Debug)]
struct Arena {
    nodes: Vec<Option<Node>>,
    unique: HashMap<(Atom, u32, u32), u32>,
    apply: HashMap<(bool, u32, u32), u32>,
    negative: HashMap<u32, u32>,
    satisfiable: HashMap<(u32, Option<Atom>), bool>,
    implication: HashMap<(u32, u32, Option<Atom>), bool>,
}
type ArenaRef = Rc<RefCell<Arena>>;
impl Arena {
    fn new() -> Self {
        Self {
            nodes: vec![None, None],
            unique: HashMap::new(),
            apply: HashMap::new(),
            negative: HashMap::new(),
            satisfiable: HashMap::new(),
            implication: HashMap::new(),
        }
    }
    fn node(&mut self, atom: Atom, low: u32, high: u32) -> u32 {
        if low == high {
            return low;
        }
        let key = (atom.clone(), low, high);
        if let Some(id) = self.unique.get(&key) {
            return *id;
        }
        let id = self.nodes.len() as u32;
        self.nodes.push(Some(Node { atom, low, high }));
        self.unique.insert(key, id);
        id
    }
    fn combine(&mut self, and: bool, mut a: u32, mut b: u32) -> u32 {
        if a > b {
            std::mem::swap(&mut a, &mut b);
        }
        if a == b {
            return a;
        }
        if and {
            if a == 0 {
                return 0;
            }
            if a == 1 {
                return b;
            }
        } else {
            if a == 0 {
                return b;
            }
            if a == 1 {
                return 1;
            }
        }
        let key = (and, a, b);
        if let Some(id) = self.apply.get(&key) {
            return *id;
        }
        let an = self.nodes[a as usize].as_ref().unwrap().clone();
        let bn = self.nodes[b as usize].as_ref().unwrap().clone();
        let top = std::cmp::min(&an.atom, &bn.atom).clone();
        let (al, ah) = if an.atom == top {
            (an.low, an.high)
        } else {
            (a, a)
        };
        let (bl, bh) = if bn.atom == top {
            (bn.low, bn.high)
        } else {
            (b, b)
        };
        let low = self.combine(and, al, bl);
        let high = self.combine(and, ah, bh);
        let id = self.node(top, low, high);
        self.apply.insert(key, id);
        id
    }
    fn negate(&mut self, id: u32) -> u32 {
        if id < 2 {
            return 1 - id;
        }
        if let Some(n) = self.negative.get(&id) {
            return *n;
        }
        let n = self.nodes[id as usize].as_ref().unwrap().clone();
        let low = self.negate(n.low);
        let high = self.negate(n.high);
        let result = self.node(n.atom, low, high);
        self.negative.insert(id, result);
        self.negative.insert(result, id);
        result
    }
    // Test implication directly on node pairs. Constructing a & !b merely to
    // ask this question retained enormous transient graphs during CFG queries.
    fn implies(&mut self, a: u32, b: u32, selected: Option<Atom>) -> bool {
        if a == 0 || b == 1 || a == b {
            return true;
        }
        if a == 1 && b == 0 {
            return false;
        }
        let an = self.nodes[a as usize].clone();
        let bn = self.nodes[b as usize].clone();
        let top = match (&an, &bn) {
            (Some(a), Some(b)) => std::cmp::min(&a.atom, &b.atom).clone(),
            (Some(a), None) => a.atom.clone(),
            (None, Some(b)) => b.atom.clone(),
            _ => unreachable!(),
        };
        let selected = selected.filter(|old| same_discriminator(old, &top));
        let key = (a, b, selected.clone());
        if let Some(answer) = self.implication.get(&key) {
            return *answer;
        }
        let (al, ah) = an
            .filter(|node| node.atom == top)
            .map(|node| (node.low, node.high))
            .unwrap_or((a, a));
        let (bl, bh) = bn
            .filter(|node| node.atom == top)
            .map(|node| (node.low, node.high))
            .unwrap_or((b, b));
        let low = self.implies(al, bl, selected.clone());
        let high = if !low {
            false
        } else if selected.as_ref().is_some_and(|old| old != &top) {
            true
        } else {
            let next = matches!(top, Atom::VariantPath(..)).then_some(top);
            self.implies(ah, bh, next)
        };
        let answer = low && high;
        self.implication.insert(key, answer);
        answer
    }
    // Variant tests on one resolved discriminator are mutually exclusive. Their
    // variables are contiguous in the canonical atom order, so only the active
    // discriminator needs to be retained during satisfiability traversal.
    fn possible(&mut self, id: u32, selected: Option<Atom>) -> bool {
        if id < 2 {
            return id == 1;
        }
        let node = self.nodes[id as usize].as_ref().unwrap().clone();
        let selected = selected.filter(|old| same_discriminator(old, &node.atom));
        let key = (id, selected.clone());
        if let Some(answer) = self.satisfiable.get(&key) {
            return *answer;
        }
        let low = self.possible(node.low, selected.clone());
        let compatible = selected.as_ref().is_none_or(|old| old == &node.atom);
        let high = if compatible && !low {
            let next = if matches!(node.atom, Atom::VariantPath(..)) {
                Some(node.atom.clone())
            } else {
                None
            };
            self.possible(node.high, next)
        } else {
            false
        };
        let answer = low || high;
        self.satisfiable.insert(key, answer);
        answer
    }
}
fn same_discriminator(a: &Atom, b: &Atom) -> bool {
    matches!((a,b),(Atom::VariantPath(av,ap,_),Atom::VariantPath(bv,bp,_))if av==bv&&ap==bp)
}
#[derive(Clone, Debug, Default)]
pub(super) struct Guard {
    id: u32,
    arena: Option<ArenaRef>,
}
impl PartialEq for Guard {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id
            && (self.id < 2
                || match (&self.arena, &other.arena) {
                    (Some(a), Some(b)) => Rc::ptr_eq(a, b),
                    _ => false,
                })
    }
}
impl Eq for Guard {}
impl Hash for Guard {
    fn hash<H: Hasher>(&self, h: &mut H) {
        self.id.hash(h);
        if self.id >= 2 {
            Rc::as_ptr(self.arena.as_ref().unwrap()).hash(h);
        }
    }
}
impl Guard {
    pub fn yes() -> Self {
        Self { id: 1, arena: None }
    }
    fn atom(arena: &ArenaRef, atom: Atom, positive: bool) -> Self {
        let atom = match atom {
            Atom::Variant(v, t) => Atom::VariantPath(v, vec![], t),
            other => other,
        };
        let id = arena.borrow_mut().node(atom, 0, 1);
        let id = if positive {
            id
        } else {
            arena.borrow_mut().negate(id)
        };
        Self {
            id,
            arena: Some(arena.clone()),
        }
    }
    pub fn possible(&self) -> bool {
        if self.id < 2 {
            return self.id == 1;
        }
        self.arena
            .as_ref()
            .unwrap()
            .borrow_mut()
            .possible(self.id, None)
    }
    fn combine(&self, r: &Self, and: bool) -> Self {
        if self.id < 2 && r.id < 2 {
            return Self {
                id: if and { self.id & r.id } else { self.id | r.id },
                arena: None,
            };
        }
        let arena = self.arena.as_ref().or(r.arena.as_ref()).unwrap();
        if let (Some(a), Some(b)) = (&self.arena, &r.arena) {
            assert!(
                Rc::ptr_eq(a, b),
                "guards belong to different verification runs"
            );
        }
        let id = arena.borrow_mut().combine(and, self.id, r.id);
        Self {
            id,
            arena: Some(arena.clone()),
        }
    }
    pub fn and(&self, r: &Self) -> Self {
        self.combine(r, true)
    }
    pub fn or(&self, r: &Self) -> Self {
        self.combine(r, false)
    }
    pub fn not(&self) -> Self {
        if self.id < 2 {
            return Self {
                id: 1 - self.id,
                arena: None,
            };
        }
        let arena = self.arena.as_ref().unwrap();
        let id = arena.borrow_mut().negate(self.id);
        Self {
            id,
            arena: Some(arena.clone()),
        }
    }
    pub fn implies(&self, r: &Self) -> bool {
        if self.id < 2 && r.id < 2 {
            return self.id == 0 || r.id == 1;
        }
        let arena = self.arena.as_ref().or(r.arena.as_ref()).unwrap();
        if let (Some(a), Some(b)) = (&self.arena, &r.arena) {
            assert!(Rc::ptr_eq(a, b));
        }
        arena.borrow_mut().implies(self.id, r.id, None)
    }
    pub fn support(&self) -> HashSet<Atom> {
        let Some(arena) = &self.arena else {
            return HashSet::new();
        };
        let arena = arena.borrow();
        let mut atoms = HashSet::new();
        let mut seen = HashSet::new();
        let mut pending = vec![self.id];
        while let Some(id) = pending.pop() {
            if id < 2 || !seen.insert(id) {
                continue;
            }
            let node = arena.nodes[id as usize].as_ref().unwrap();
            atoms.insert(node.atom.clone());
            pending.extend([node.low, node.high]);
        }
        atoms
    }
    /// Existential abstraction: erase predicates irrelevant to a local query.
    /// This enlarges the path set; it can never invent a proof of exclusion.
    pub fn project(&self, keep: &HashSet<Atom>) -> Self {
        fn visit(
            arena: &mut Arena,
            id: u32,
            keep: &HashSet<Atom>,
            memo: &mut HashMap<u32, u32>,
        ) -> u32 {
            if id < 2 {
                return id;
            }
            if let Some(result) = memo.get(&id) {
                return *result;
            }
            let node = arena.nodes[id as usize].as_ref().unwrap().clone();
            let low = visit(arena, node.low, keep, memo);
            let high = visit(arena, node.high, keep, memo);
            let result = if keep.contains(&node.atom) {
                arena.node(node.atom, low, high)
            } else {
                arena.combine(false, low, high)
            };
            memo.insert(id, result);
            result
        }
        let Some(arena) = &self.arena else {
            return self.clone();
        };
        let id = visit(&mut arena.borrow_mut(), self.id, keep, &mut HashMap::new());
        Self {
            id,
            arena: Some(arena.clone()),
        }
    }
    pub fn exported(&self) -> VerifiedPathCondition {
        VerifiedPathCondition {
            root: VerifiedConditionId(self.id),
        }
    }
    pub fn graph(&self) -> Vec<VerifiedConditionNode> {
        let Some(arena) = &self.arena else {
            return vec![VerifiedConditionNode::False, VerifiedConditionNode::True];
        };
        arena
            .borrow()
            .nodes
            .iter()
            .enumerate()
            .map(|(id, n)| match n {
                None if id == 0 => VerifiedConditionNode::False,
                None => VerifiedConditionNode::True,
                Some(n) => VerifiedConditionNode::Decision {
                    atom: export_atom(&n.atom),
                    when_false: VerifiedConditionId(n.low),
                    when_true: VerifiedConditionId(n.high),
                },
            })
            .collect()
    }
}
fn export_atom(atom: &Atom) -> VerifiedConditionAtom {
    match atom {
        Atom::Boolean(v) => VerifiedConditionAtom::Boolean(*v),
        Atom::Variant(v, t) => VerifiedConditionAtom::Variant(*v, *t),
        Atom::VariantPath(v, p, t) => VerifiedConditionAtom::VariantPath(*v, p.clone(), *t),
        Atom::Other(p) => VerifiedConditionAtom::Predicate(*p),
        Atom::Copies(t) => VerifiedConditionAtom::Copies(*t),
    }
}

/// Build the predicate graph once. The table is owned by this verification run;
/// no process-global/source-pointer cache can leak facts between programs.
pub(super) fn all(p: &PostAst) -> Vec<Guard> {
    struct Context<'a> {
        p: &'a PostAst,
        arena: ArenaRef,
        raw: Vec<Option<Guard>>,
        domain: Vec<Option<Guard>>,
        active: HashSet<PredicateId>,
        ops: std::collections::HashMap<OperationId, &'a Operation>,
        boolean: std::collections::HashMap<ValueId, Guard>,
        boolean_active: HashSet<ValueId>,
    }
    impl Context<'_> {
        fn boolean(&mut self, v: ValueId) -> Guard {
            if let Some(g) = self.boolean.get(&v) {
                return g.clone();
            }
            if !self.boolean_active.insert(v) {
                return Guard::atom(&self.arena, Atom::Boolean(v), true);
            }
            let value = &self.p.values.entries[v.0 as usize];
            let constant = match &value.definition {
                ValueDefinition::Constant(c) => {
                    Some(&self.p.declarations.constants[c.0 as usize].value)
                }
                ValueDefinition::ConfiguredConstant { value, .. } => Some(value),
                _ => None,
            };
            let result = if let Some(ConstantValue::Boolean(b)) = constant {
                if *b { Guard::yes() } else { Guard::default() }
            } else {
                match &self.p.values.provenance[value.provenance.0 as usize].kind {
                    ProvenanceKind::Copy { source, .. }
                    | ProvenanceKind::Forward { source, .. }
                    | ProvenanceKind::Move { source, .. } => self.boolean(*source),
                    ProvenanceKind::Merge(values) => {
                        let mut g = Guard::default();
                        for value in std::iter::once(&values.first).chain(&values.rest) {
                            g = g.or(&self.raw(value.guard).and(&self.boolean(value.value)));
                        }
                        g
                    }
                    _ => {
                        let op = match value.definition {
                            ValueDefinition::OperationResult { operation, .. }
                            | ValueDefinition::ConditionalResult { operation, .. } => {
                                self.ops.get(&operation).copied()
                            }
                            _ => None,
                        };
                        match op {
                            Some(Operation::BooleanLiteral(x)) => {
                                if x.value {
                                    Guard::yes()
                                } else {
                                    Guard::default()
                                }
                            }
                            Some(Operation::CopyPrimitive(x)) => self.boolean(x.source),
                            Some(Operation::BooleanNot(x)) => self.boolean(x.operand).not(),
                            _ => Guard::atom(&self.arena, Atom::Boolean(v), true),
                        }
                    }
                }
            };
            self.boolean_active.remove(&v);
            self.boolean.insert(v, result.clone());
            result
        }
        fn raw(&mut self, id: PredicateId) -> Guard {
            if let Some(g) = &self.raw[id.0 as usize] {
                return g.clone();
            }
            if !self.active.insert(id) {
                return Guard::atom(&self.arena, Atom::Other(id), true);
            }
            let result = match &self.p.execution.predicates[id.0 as usize].kind {
                PredicateKind::Always => Guard::yes(),
                PredicateKind::All(ids) => {
                    ids.iter().fold(Guard::yes(), |g, id| g.and(&self.raw(*id)))
                }
                PredicateKind::Any(ids) => ids
                    .iter()
                    .fold(Guard::default(), |g, id| g.or(&self.raw(*id))),
                PredicateKind::Not(id) => self.raw(*id).not(),
                PredicateKind::Boolean { value, expected } => {
                    let b = self.boolean(*value);
                    if *expected { b } else { b.not() }
                }
                PredicateKind::Pattern { subject, test } => {
                    pattern_formula(self.p, *subject, test, &self.arena).0
                }
                PredicateKind::Variant { value, variant } => {
                    Guard::atom(&self.arena, Atom::Variant(*value, *variant), true)
                }
                PredicateKind::TypeCopiesByValue(ty) => {
                    Guard::atom(&self.arena, Atom::Copies(*ty), true)
                }
                _ => Guard::atom(&self.arena, Atom::Other(id), true),
            };
            self.active.remove(&id);
            self.raw[id.0 as usize] = Some(result.clone());
            result
        }
        fn domain(&mut self, id: PredicateId) -> Guard {
            if let Some(g) = &self.domain[id.0 as usize] {
                return g.clone();
            }
            self.domain[id.0 as usize] = Some(Guard::yes());
            let result = match &self.p.execution.predicates[id.0 as usize].kind {
                PredicateKind::Pattern { subject, test } => {
                    pattern_formula(self.p, *subject, test, &self.arena).1
                }
                PredicateKind::All(ids) | PredicateKind::Any(ids) => ids
                    .iter()
                    .fold(Guard::yes(), |g, id| g.and(&self.domain(*id))),
                PredicateKind::Not(id) => self.domain(*id),
                _ => Guard::yes(),
            };
            self.domain[id.0 as usize] = Some(result.clone());
            result
        }
    }
    let n = p.execution.predicates.len();
    let ops = p
        .bodies
        .iter()
        .flat_map(|b| &b.operations)
        .map(|o| (o.site().id, o))
        .collect();
    let mut c = Context {
        p,
        arena: Rc::new(RefCell::new(Arena::new())),
        raw: vec![None; n],
        domain: vec![None; n],
        active: HashSet::new(),
        ops,
        boolean: Default::default(),
        boolean_active: HashSet::new(),
    };
    (0..n)
        .map(|i| {
            let id = PredicateId(i as u32);
            c.raw(id).and(&c.domain(id))
        })
        .collect()
}
/// Pattern coverage is a finite symbolic discriminator formula. Nested payload
/// positions remain paths; combinations of runtime payloads are not enumerated.
fn pattern_formula(
    p: &PostAst,
    subject: ValueId,
    test: &PatternTest,
    arena: &ArenaRef,
) -> (Guard, Guard) {
    fn go(
        p: &PostAst,
        subject: ValueId,
        test: &PatternTest,
        path: &[u64],
        domains: &mut Guard,
        arena: &ArenaRef,
    ) -> Guard {
        match test {
            PatternTest::Any | PatternTest::Unit => Guard::yes(),
            PatternTest::Dereference(test) => go(p, subject, test, path, domains, arena),
            PatternTest::Tuple(parts) => {
                parts
                    .iter()
                    .enumerate()
                    .fold(Guard::yes(), |out, (i, test)| {
                        let mut at = path.to_vec();
                        at.push((1u64 << 63) | i as u64);
                        out.and(&go(p, subject, test, &at, domains, arena))
                    })
            }
            PatternTest::Variant { variant, fields } => {
                let owner = p.declarations.variants[variant.0 as usize].owner;
                let alternatives = p
                    .declarations
                    .enums
                    .iter()
                    .find(|e| e.ty == owner)
                    .expect("resolved variant owner");
                let domain = std::iter::once(alternatives.variants.first)
                    .chain(alternatives.variants.rest.iter().copied())
                    .fold(Guard::default(), |g, v| {
                        g.or(&Guard::atom(
                            arena,
                            Atom::VariantPath(subject, path.to_vec(), v),
                            true,
                        ))
                    });
                *domains = domains.and(&domain);
                fields.iter().fold(
                    Guard::atom(
                        arena,
                        Atom::VariantPath(subject, path.to_vec(), *variant),
                        true,
                    ),
                    |out, (field, test)| {
                        let mut at = path.to_vec();
                        at.push(field.0 as u64);
                        out.and(&go(p, subject, test, &at, domains, arena))
                    },
                )
            }
        }
    }
    let mut domain = Guard::yes();
    let result = go(p, subject, test, &[], &mut domain, arena);
    (result, domain)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn decision_graph_boolean_operations_match_truth_table() {
        let arena = Rc::new(RefCell::new(Arena::new()));
        let a = Guard::atom(&arena, Atom::Boolean(ValueId(0)), true);
        let b = Guard::atom(&arena, Atom::Boolean(ValueId(1)), true);
        let c = Guard::atom(&arena, Atom::Boolean(ValueId(2)), true);
        let formula = a.or(&b).and(&a.not().or(&c));
        for assignment in 0..8 {
            let mut id = formula.id;
            loop {
                if id < 2 {
                    break;
                }
                let arena = arena.borrow();
                let n = arena.nodes[id as usize].as_ref().unwrap();
                let Atom::Boolean(ValueId(bit)) = n.atom else {
                    unreachable!()
                };
                id = if assignment & (1 << bit) != 0 {
                    n.high
                } else {
                    n.low
                };
            }
            assert_eq!(
                id == 1,
                ((assignment & 1) != 0 || (assignment & 2) != 0)
                    && ((assignment & 1) == 0 || (assignment & 4) != 0)
            );
        }
        assert!(!formula.and(&formula.not()).possible());
    }
    #[test]
    fn implication_matches_truth_table_without_allocating_nodes() {
        let arena = Rc::new(RefCell::new(Arena::new()));
        let a = Guard::atom(&arena, Atom::Boolean(ValueId(0)), true);
        let b = Guard::atom(&arena, Atom::Boolean(ValueId(1)), true);
        let formulas = vec![
            Guard::default(),
            Guard::yes(),
            a.clone(),
            b.clone(),
            a.not(),
            b.not(),
            a.and(&b),
            a.or(&b),
        ];
        let eval = |guard: &Guard, assignment: u32| {
            let mut id = guard.id;
            while id >= 2 {
                let arena = arena.borrow();
                let node = arena.nodes[id as usize].as_ref().unwrap();
                let Atom::Boolean(ValueId(bit)) = node.atom else {
                    unreachable!()
                };
                id = if assignment & (1 << bit) == 0 {
                    node.low
                } else {
                    node.high
                };
            }
            id == 1
        };
        let count = arena.borrow().nodes.len();
        for left in &formulas {
            for right in &formulas {
                assert_eq!(
                    left.implies(right),
                    (0..4).all(|assignment| !eval(left, assignment) || eval(right, assignment))
                );
            }
        }
        assert_eq!(arena.borrow().nodes.len(), count);
        let first = Guard::atom(&arena, Atom::Variant(ValueId(7), VariantId(1)), true);
        let second = Guard::atom(&arena, Atom::Variant(ValueId(7), VariantId(2)), true);
        assert!(first.implies(&second.not()));
    }
    #[test]
    fn existential_projection_keeps_relevant_conditions() {
        let arena = Rc::new(RefCell::new(Arena::new()));
        let a = Guard::atom(&arena, Atom::Boolean(ValueId(0)), true);
        let b = Guard::atom(&arena, Atom::Boolean(ValueId(1)), true);
        let c = Guard::atom(&arena, Atom::Boolean(ValueId(2)), true);
        let keep = HashSet::from([Atom::Boolean(ValueId(0))]);
        assert_eq!(a.and(&b.or(&c)).project(&keep), a);
        assert_eq!(a.and(&b).project(&HashSet::new()), Guard::yes());
        assert!(!a.and(&a.not()).project(&HashSet::new()).possible());
    }
    #[test]
    fn variant_tests_of_one_discriminator_are_exclusive() {
        let arena = Rc::new(RefCell::new(Arena::new()));
        let a = Guard::atom(
            &arena,
            Atom::VariantPath(ValueId(0), vec![], VariantId(0)),
            true,
        );
        let b = Guard::atom(
            &arena,
            Atom::VariantPath(ValueId(0), vec![], VariantId(1)),
            true,
        );
        assert!(!a.and(&b).possible());
        assert!(a.or(&b).possible());
        let other = Guard::atom(
            &arena,
            Atom::VariantPath(ValueId(1), vec![], VariantId(1)),
            true,
        );
        assert!(a.and(&other).possible());
    }
}
