//! Through-result exclusivity is released by destruction, not last reference use.
use super::*;
impl Checker<'_> {
    fn value_alias(&self, a: ValueId, b: ValueId, seen: &mut HashSet<ValueId>) -> bool {
        if a == b {
            return true;
        }
        if !seen.insert(b) {
            return false;
        }
        let av = &self.p.values.entries[a.0 as usize];
        let bv = &self.p.values.entries[b.0 as usize];
        let ao = &self.p.values.placement_summaries[av.placement.0 as usize].origins;
        let bo = &self.p.values.placement_summaries[bv.placement.0 as usize].origins;
        if ao.iter().any(|a| bo.contains(a)) {
            return true;
        }
        match &self.p.values.provenance[bv.provenance.0 as usize].kind {
            ProvenanceKind::Forward { source, .. } | ProvenanceKind::Move { source, .. } => {
                self.value_alias(a, *source, seen)
            }
            ProvenanceKind::Merge(values) => std::iter::once(&values.first)
                .chain(&values.rest)
                .any(|v| self.value_alias(a, v.value, seen)),
            _ => false,
        }
    }
    pub(super) fn lock_interval_checks(&mut self) {
        let locks = self
            .p
            .contracts
            .applications
            .iter()
            .filter_map(|a| {
                if let ContractApplication::Lock {
                    identity,
                    begins,
                    ends,
                    carried_by,
                    ..
                } = a
                {
                    Some((*identity, *begins, *ends, *carried_by))
                } else {
                    None
                }
            })
            .collect::<Vec<_>>();
        for (identity, start, end, carrier) in &locks {
            let info = &self.p.contracts.lock_identities[identity.0 as usize];
            let start_site = self.site_at(*start);
            let targets = self
                .facts
                .dependencies(info.receiver, *start, &HashMap::new());
            let mut releases = HashMap::new();
            if let Some(end) = end {
                releases.insert(*end, Guard::yes());
            }
            if let Some(value) = carrier {
                for op in self.p.bodies.iter().flat_map(|b| &b.operations) {
                    let dropped = match op {
                        Operation::DropValue(x) => Some(x.value),
                        Operation::DiscardResult(x) => Some(x.value),
                        _ => None,
                    };
                    if dropped.is_some_and(|d| {
                        self.facts
                            .holds_lock(d, *identity, op.site().execution_moments.first)
                            || self.value_alias(*value, d, &mut HashSet::new())
                    }) {
                        releases.insert(
                            op.site().execution_moments.first,
                            self.flow.predicate(op.site().guard),
                        );
                    }
                }
                for final_ in &self.input.finals {
                    let at = match final_.cleanup_exit {
                        LogicalCleanupSite::Exit(exit) => {
                            self.p.scopes.exits[exit.0 as usize].event
                        }
                        _ => *start,
                    };
                    if self.facts.holds_lock(final_.value, *identity, at)
                        || self.value_alias(*value, final_.value, &mut HashSet::new())
                    {
                        if let LogicalCleanupSite::Exit(exit) = final_.cleanup_exit {
                            let e = &self.p.scopes.exits[exit.0 as usize];
                            releases.insert(e.event, self.flow.predicate(final_.guard));
                        }
                    }
                }
            }
            for (other, at, _, _) in &locks {
                if start == at {
                    continue;
                }
                let next_site = self.site_at(*at);
                let other = &self.p.contracts.lock_identities[other.0 as usize];
                let next_targets = self
                    .facts
                    .dependencies(other.receiver, *at, &HashMap::new());
                if targets
                    .iter()
                    .any(|a| next_targets.iter().any(|b| Facts::overlaps(a, b)))
                    && self.flow.path_avoiding(
                        *start,
                        *at,
                        &self.guard(&start_site).and(&self.guard(&next_site)),
                        &releases,
                    )
                {
                    self.reject_access_obligations_at(&next_site,"same-object lock acquisition can occur before the previous lock is released",vec![start_site.origin]);
                }
            }
        }
    }
}
