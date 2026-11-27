//! Test-only EBNF reader and bounded derivation generator. Never calls the
//! production parser to select expansions or manufacture expected acceptance.
use std::collections::{BTreeMap, BTreeSet, VecDeque};

#[derive(Clone, Debug)]
pub enum Form {
    Terminal(String),
    Reference(String),
    Sequence(Vec<usize>),
    Alternative(Vec<usize>),
    Optional(usize),
    Repeat(usize),
}
#[derive(Debug)]
pub struct Grammar {
    pub nodes: Vec<Form>,
    pub rules: BTreeMap<String, usize>,
    pub positions: Vec<usize>,
    pub lexical: BTreeMap<String, String>,
}
#[derive(Debug, Clone)]
enum Token {
    Name(String),
    Text(String),
    Mark(char),
}
struct Reader {
    tokens: Vec<(usize, Token)>,
    at: usize,
    nodes: Vec<Form>,
    positions: Vec<usize>,
}
impl Reader {
    fn node(&mut self, form: Form, offset: usize) -> usize {
        let id = self.nodes.len();
        self.nodes.push(form);
        self.positions.push(offset);
        id
    }
    fn mark(&mut self, c: char) -> bool {
        if matches!(self.tokens.get(self.at), Some((_,Token::Mark(m))) if *m == c) {
            self.at += 1;
            true
        } else {
            false
        }
    }
    fn expect(&mut self, c: char) {
        assert!(
            self.mark(c),
            "expected {c} at {:?}",
            self.tokens.get(self.at)
        );
    }
    fn choice(&mut self) -> usize {
        let offset = self.tokens[self.at].0;
        let mut children = vec![self.sequence()];
        while self.mark('|') {
            children.push(self.sequence());
        }
        if children.len() == 1 {
            children[0]
        } else {
            self.node(Form::Alternative(children), offset)
        }
    }
    fn sequence(&mut self) -> usize {
        let offset = self.tokens[self.at].0;
        let mut children = vec![self.atom()];
        while self.mark(',') {
            children.push(self.atom());
        }
        if children.len() == 1 {
            children[0]
        } else {
            self.node(Form::Sequence(children), offset)
        }
    }
    fn atom(&mut self) -> usize {
        let (offset, token) = self.tokens[self.at].clone();
        self.at += 1;
        let form = match token {
            Token::Name(name) => Form::Reference(name),
            Token::Text(text) => Form::Terminal(text),
            Token::Mark(open @ ('[' | '{' | '(')) => {
                let child = self.choice();
                self.expect(match open {
                    '[' => ']',
                    '{' => '}',
                    _ => ')',
                });
                match open {
                    '[' => Form::Optional(child),
                    '{' => Form::Repeat(child),
                    _ => return child,
                }
            }
            other => panic!("unexpected {other:?} at {offset}"),
        };
        self.node(form, offset)
    }
}
impl Grammar {
    pub fn read(source: &str) -> Self {
        let mut tokens = Vec::new();
        let mut at = 0;
        while at < source.len() {
            let rest = &source[at..];
            if rest.starts_with("(*") {
                let end = rest.find("*)").expect("unclosed grammar comment");
                at += end + 2;
                continue;
            }
            let b = source.as_bytes()[at];
            if b.is_ascii_whitespace() {
                at += 1;
                continue;
            }
            let start = at;
            let token = if b == b'"' {
                at += 1;
                let begin = at;
                while source.as_bytes()[at] != b'"' {
                    at += 1;
                }
                let text = source[begin..at].to_owned();
                at += 1;
                Token::Text(text)
            } else if b.is_ascii_alphabetic() || b == b'_' {
                at += 1;
                while at < source.len()
                    && (source.as_bytes()[at].is_ascii_alphanumeric()
                        || source.as_bytes()[at] == b'_')
                {
                    at += 1;
                }
                Token::Name(source[start..at].to_owned())
            } else {
                at += 1;
                Token::Mark(b as char)
            };
            tokens.push((start, token));
        }
        let mut reader = Reader {
            tokens,
            at: 0,
            nodes: Vec::new(),
            positions: Vec::new(),
        };
        let mut rules = BTreeMap::new();
        while reader.at < reader.tokens.len() {
            let Token::Name(name) = reader.tokens[reader.at].1.clone() else {
                panic!("expected rule name")
            };
            reader.at += 1;
            reader.expect('=');
            let root = reader.choice();
            reader.expect(';');
            assert!(
                rules.insert(name.clone(), root).is_none(),
                "duplicate production {name}"
            );
        }
        let lexical = [
            ("nom", "item"),
            ("identifiant", "item"),
            ("nom_structure", "Item"),
            ("nom_enum", "Choice"),
            ("entier", "1"),
            ("decimal_positif", "1"),
            ("flottant", "1.5"),
            ("texte", "\"text\""),
            ("abi_c", "\"C\""),
            ("texte_assembleur", "nop"),
            ("texte_c", "int native_value = 0;"),
            ("texte_cpp", "int native_value = 0;"),
        ]
        .into_iter()
        .map(|(a, b)| (a.to_owned(), b.to_owned()))
        .collect();
        Self {
            nodes: reader.nodes,
            rules,
            positions: reader.positions,
            lexical,
        }
    }
    pub fn children(&self, id: usize) -> Vec<usize> {
        match &self.nodes[id] {
            Form::Sequence(c) | Form::Alternative(c) => c.clone(),
            Form::Optional(c) | Form::Repeat(c) => vec![*c],
            _ => vec![],
        }
    }
    pub fn descendants(&self, id: usize) -> BTreeSet<usize> {
        let mut out = BTreeSet::new();
        let mut pending = vec![id];
        while let Some(id) = pending.pop() {
            if out.insert(id) {
                pending.extend(self.children(id));
            }
        }
        out
    }
    pub fn undefined(&self) -> BTreeSet<String> {
        self.nodes
            .iter()
            .filter_map(|n| match n {
                Form::Reference(name)
                    if !self.rules.contains_key(name) && !self.lexical.contains_key(name) =>
                {
                    Some(name.clone())
                }
                _ => None,
            })
            .collect()
    }
    pub fn costs(&self) -> Vec<usize> {
        const INF: usize = 1_000_000;
        let mut costs = vec![INF; self.nodes.len()];
        loop {
            let mut changed = false;
            for (id, form) in self.nodes.iter().enumerate() {
                let value = match form {
                    Form::Terminal(_) => 1,
                    Form::Reference(name) => self.rules.get(name).map(|r| costs[*r]).unwrap_or(
                        if self.lexical.contains_key(name) {
                            1
                        } else {
                            INF
                        },
                    ),
                    Form::Sequence(c) => c.iter().map(|c| costs[*c]).sum::<usize>().min(INF),
                    Form::Alternative(c) => c.iter().map(|c| costs[*c]).min().unwrap(),
                    Form::Optional(_) | Form::Repeat(_) => 0,
                };
                if value < costs[id] {
                    costs[id] = value;
                    changed = true;
                }
            }
            if !changed {
                break;
            }
        }
        costs
    }
    // Each goal chooses one EBNF alternative, optional presence or repeat count.
    pub fn goals(&self, root: usize) -> Vec<(usize, usize)> {
        let mut out = vec![];
        for id in self.descendants(root) {
            match &self.nodes[id] {
                Form::Alternative(c) => out.extend((0..c.len()).map(|i| (id, i))),
                Form::Optional(_) => out.extend([(id, 0), (id, 1)]),
                Form::Repeat(_) => out.extend([(id, 0), (id, 1), (id, 2)]),
                _ => {}
            }
        }
        out
    }
    pub fn expand(
        &self,
        id: usize,
        costs: &[usize],
        goal: Option<(usize, usize)>,
        replacement: Option<(usize, &[String])>,
        depth: usize,
    ) -> Vec<String> {
        assert!(depth < 256, "nonterminating generation at {id}");
        if let Some((target, tokens)) = replacement {
            if id == target {
                return tokens.to_vec();
            }
        }
        let targeted = |child: usize| {
            goal.is_some_and(|(target, _)| self.descendants(child).contains(&target))
                || replacement.is_some_and(|(target, _)| self.descendants(child).contains(&target))
        };
        let expand = |child| self.expand(child, costs, goal, replacement, depth + 1);
        match &self.nodes[id] {
            Form::Terminal(text) => vec![text.clone()],
            Form::Reference(name) => {
                if let Some(root) = self.rules.get(name) {
                    // A goal/replacement belongs to the current production only.
                    let tokens = self.expand(*root, costs, None, None, depth + 1);
                    tokens
                } else {
                    vec![self.lexical[name].clone()]
                }
            }
            Form::Sequence(c) => c.iter().flat_map(|c| expand(*c)).collect(),
            Form::Alternative(c) => {
                let choice = if let Some((target, index)) = goal.filter(|(target, _)| *target == id)
                {
                    let _ = target;
                    index
                } else {
                    c.iter().position(|c| targeted(*c)).unwrap_or_else(|| {
                        c.iter()
                            .enumerate()
                            .min_by_key(|(_, c)| costs[**c])
                            .unwrap()
                            .0
                    })
                };
                expand(c[choice])
            }
            Form::Optional(child) | Form::Repeat(child) => {
                let count = goal
                    .filter(|(target, _)| *target == id)
                    .map(|(_, n)| n)
                    .unwrap_or(usize::from(targeted(*child)));
                (0..count).flat_map(|_| expand(*child)).collect()
            }
        }
    }
    // Shortest reference path from a complete program to every production.
    // Wrappers come from the EBNF itself, never a handwritten snippet catalog.
    pub fn contexts_from(&self, root: &str) -> BTreeMap<String, Vec<(String, usize)>> {
        let mut paths = BTreeMap::from([(root.to_owned(), vec![])]);
        let mut queue = VecDeque::from([root.to_owned()]);
        while let Some(owner) = queue.pop_front() {
            for id in self.descendants(self.rules[&owner]) {
                if let Form::Reference(name) = &self.nodes[id] {
                    if self.rules.contains_key(name) && !paths.contains_key(name) {
                        let mut path = paths[&owner].clone();
                        path.push((owner.clone(), id));
                        paths.insert(name.clone(), path);
                        queue.push_back(name.clone());
                    }
                }
            }
        }
        paths
    }
    pub fn contexts(&self) -> BTreeMap<String, Vec<(String, usize)>> {
        let mut paths = self.contexts_from("programme");
        // The grammar explicitly requires lexical unchecked enclosure for
        // foreign blocks. Select that legal derivation context, not the
        // shorter instruction_simple route which omits the premise.
        let checked_path = paths["bloc_unchecked"].clone();
        let enclosed = self.contexts_from("bloc_unchecked");
        for name in [
            "bloc_asm",
            "bloc_c",
            "bloc_cpp",
            "chemin_entete",
            "operande_asm",
            "instruction_simple",
        ] {
            let mut path = checked_path.clone();
            path.extend(enclosed[name].clone());
            paths.insert(name.to_owned(), path);
        }
        paths
    }
    pub fn program_tokens(
        &self,
        owner: &str,
        goal: Option<(usize, usize)>,
        costs: &[usize],
        context: &[(String, usize)],
    ) -> Vec<String> {
        let mut tokens = self.expand(self.rules[owner], costs, goal, None, 0);
        for (parent, reference) in context.iter().rev() {
            tokens = self.expand(
                self.rules[parent],
                costs,
                None,
                Some((*reference, &tokens)),
                0,
            );
        }
        tokens
    }
    pub fn render(tokens: &[String]) -> String {
        let mut parts = Vec::new();
        let mut at = 0;
        while at < tokens.len() {
            if tokens[at] == "${" {
                let start = at;
                while tokens[at] != "}" {
                    at += 1;
                }
                at += 1;
                parts.push(tokens[start..at].concat());
            } else if tokens[at] == "."
                && tokens
                    .get(at + 1)
                    .is_some_and(|s| s.len() == 1 && s.as_bytes()[0].is_ascii_digit())
            {
                parts.push(".".to_owned());
                at += 1;
                let start = at;
                while tokens
                    .get(at)
                    .is_some_and(|s| s.len() == 1 && s.as_bytes()[0].is_ascii_digit())
                {
                    at += 1;
                }
                parts.push(tokens[start..at].concat());
            } else {
                parts.push(tokens[at].clone());
                at += 1;
            }
        }
        parts.join(" ")
    }
}

// Independent chart recognition of the EBNF after mechanical EBNF-to-BNF
// expansion. This operates on derivation terminal fragments, not lexer tokens
// or the production AST. Lexical samples and contextual premises stay explicit.
#[derive(Clone, Debug)]
enum Symbol {
    Nonterminal(usize),
    Terminal(String),
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
struct State {
    rule: usize,
    dot: usize,
    origin: usize,
}
pub struct Recognizer {
    rules: Vec<(usize, Vec<Symbol>)>,
    by_left: Vec<Vec<usize>>,
    start: usize,
}
impl Recognizer {
    pub fn new(grammar: &Grammar) -> Self {
        let mut rules = vec![];
        for (id, node) in grammar.nodes.iter().enumerate() {
            let alternatives = match node {
                Form::Terminal(text) => vec![vec![Symbol::Terminal(text.clone())]],
                Form::Reference(name) => vec![vec![if let Some(root) = grammar.rules.get(name) {
                    Symbol::Nonterminal(*root)
                } else {
                    Symbol::Terminal(grammar.lexical[name].clone())
                }]],
                Form::Sequence(children) => {
                    vec![children.iter().map(|id| Symbol::Nonterminal(*id)).collect()]
                }
                Form::Alternative(children) => children
                    .iter()
                    .map(|id| vec![Symbol::Nonterminal(*id)])
                    .collect(),
                Form::Optional(child) => vec![vec![], vec![Symbol::Nonterminal(*child)]],
                Form::Repeat(child) => vec![
                    vec![],
                    vec![Symbol::Nonterminal(*child), Symbol::Nonterminal(id)],
                ],
            };
            for rhs in alternatives {
                rules.push((id, rhs));
            }
        }
        let start = rules.len();
        rules.push((
            grammar.nodes.len(),
            vec![Symbol::Nonterminal(grammar.rules["programme"])],
        ));
        let mut by_left = vec![vec![]; grammar.nodes.len() + 1];
        for (index, (left, _)) in rules.iter().enumerate() {
            by_left[*left].push(index);
        }
        Self {
            rules,
            by_left,
            start,
        }
    }
    pub fn accepts(&self, tokens: &[String]) -> bool {
        fn add(chart: &mut [Vec<State>], seen: &mut [BTreeSet<State>], at: usize, state: State) {
            if seen[at].insert(state) {
                chart[at].push(state);
            }
        }
        let mut chart = vec![Vec::new(); tokens.len() + 1];
        let mut seen = vec![BTreeSet::new(); tokens.len() + 1];
        let mut waiters = vec![BTreeMap::<usize, Vec<State>>::new(); tokens.len() + 1];
        add(
            &mut chart,
            &mut seen,
            0,
            State {
                rule: self.start,
                dot: 0,
                origin: 0,
            },
        );
        for at in 0..=tokens.len() {
            let mut predicted = BTreeSet::new();
            let mut nullable = BTreeSet::new();
            let mut next = 0;
            while next < chart[at].len() {
                let state = chart[at][next];
                next += 1;
                let (left, rhs) = &self.rules[state.rule];
                match rhs.get(state.dot) {
                    Some(Symbol::Nonterminal(id)) => {
                        waiters[at].entry(*id).or_default().push(state);
                        if predicted.insert(*id) {
                            for rule in &self.by_left[*id] {
                                add(
                                    &mut chart,
                                    &mut seen,
                                    at,
                                    State {
                                        rule: *rule,
                                        dot: 0,
                                        origin: at,
                                    },
                                );
                            }
                        }
                        if nullable.contains(id) {
                            add(
                                &mut chart,
                                &mut seen,
                                at,
                                State {
                                    dot: state.dot + 1,
                                    ..state
                                },
                            );
                        }
                    }
                    Some(Symbol::Terminal(text)) => {
                        if tokens.get(at) == Some(text) {
                            add(
                                &mut chart,
                                &mut seen,
                                at + 1,
                                State {
                                    dot: state.dot + 1,
                                    ..state
                                },
                            );
                        }
                    }
                    None => {
                        if state.origin == at {
                            nullable.insert(*left);
                        }
                        if let Some(parents) = waiters[state.origin].get(left) {
                            for parent in parents {
                                add(
                                    &mut chart,
                                    &mut seen,
                                    at,
                                    State {
                                        dot: parent.dot + 1,
                                        ..*parent
                                    },
                                );
                            }
                        }
                    }
                }
            }
        }
        seen[tokens.len()].contains(&State {
            rule: self.start,
            dot: 1,
            origin: 0,
        })
    }
}
