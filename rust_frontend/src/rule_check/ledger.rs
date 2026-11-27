//! Exact accounting for semantic-rule obligations.
//!
//! Applicability is produced before verification. The ledger never infers a
//! missing obligation from the absence of a diagnostic. A checked program can
//! leave this module only after every declared obligation has evidence.
use crate::post_ast::*;
use std::collections::{HashMap, HashSet};

#[derive(Clone)]
pub(super) struct DeclaredObligation {
    pub id: ObligationId,
    pub rule: CoreRule,
    pub origin: SourceOriginId,
}

pub(super) struct ObligationLedger {
    declared: HashMap<ObligationId, DeclaredObligation>,
    accounted: HashSet<ObligationId>,
}

impl ObligationLedger {
    pub fn new(program: &PostAst) -> Self {
        let mut ledger = Self {
            declared: HashMap::new(),
            accounted: HashSet::new(),
        };
        macro_rules! declare {
            ($rule:ident, $items:expr) => {
                for obligation in $items {
                    ledger.insert(obligation.site.id, CoreRule::$rule, obligation.site.origin);
                }
            };
        }
        declare!(N1, &program.obligations.n1);
        declare!(N2, &program.obligations.n2);
        declare!(N3, &program.obligations.n3);
        declare!(N4, &program.obligations.n4);
        declare!(N5, &program.obligations.n5);
        declare!(N6, &program.obligations.n6);
        declare!(N7, &program.obligations.n7);
        declare!(N8, &program.obligations.n8);
        ledger
    }

    fn insert(&mut self, id: ObligationId, rule: CoreRule, origin: SourceOriginId) {
        let previous = self
            .declared
            .insert(id, DeclaredObligation { id, rule, origin });
        assert!(
            previous.is_none(),
            "duplicate semantic obligation ID {id:?}"
        );
    }

    pub fn account(&mut self, id: ObligationId) -> bool {
        self.declared.contains_key(&id) && self.accounted.insert(id)
    }

    pub fn is_accounted(&self, id: ObligationId) -> bool {
        self.accounted.contains(&id)
    }

    pub fn unresolved(&self) -> Vec<DeclaredObligation> {
        let mut unresolved = self
            .declared
            .values()
            .filter(|obligation| !self.accounted.contains(&obligation.id))
            .cloned()
            .collect::<Vec<_>>();
        unresolved.sort_by_key(|obligation| obligation.id.0);
        unresolved
    }
}
