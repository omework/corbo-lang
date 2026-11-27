//! Semantic population from syntax only. No legacy frontend, rule verifier or
//! backend dependencies. Failure never returns a partially populated PostAST.
pub mod grammar;

mod resolver;
pub use crate::post_ast::integrity::{IntegrityError, validate_population};
pub use resolver::{
    Diagnostic, DiagnosticKind, ParsedModule, ResolvedPackage, ResolvedProgram, resolve,
    resolve_package, resolve_package_for_target,
};
