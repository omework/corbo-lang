//! Canonical stage contracts; this entry point remains standalone-checkable.
#![allow(dead_code)]
#[path = "../../rust_frontend/src/post_ast/model.rs"]
pub mod model;
#[path = "../../rust_frontend/src/post_ast/passes.rs"]
pub mod passes;
pub use passes::*;
