use corbo_frontend::{cpp_backend, memory_plan, parse_source, post_ast::*, rule_check, semantic};
use std::{fs, process::Command};

fn lower(source: &str) -> PlannedPostAst {
    let syntax = parse_source(source.to_owned()).unwrap();
    let resolved = semantic::resolve(syntax).unwrap();
    let checked = match rule_check::verify(resolved.logical) {
        RuleAnalysisResult::Established(checked) => checked,
        other => panic!("rule checking failed: {other:#?}"),
    };
    let planned = match memory_plan::plan(checked) {
        MemoryPlanningResult::Planned(planned) => planned,
        other => panic!("memory planning failed: {other:#?}"),
    };
    planned
}

#[test]
fn resolved_entry_is_carried_to_the_backend() {
    let lowered = lower("fn helper(){} fn main(){}");
    let post = &lowered.checked_flow.semantics.semantics.post_ast;
    let entry = post.entry_point.expect("semantic entry point");
    let symbol = post.declarations.functions
        [post.declarations.instances[entry.0 as usize].definition.0 as usize]
        .symbol;
    assert_eq!(post.symbols.entries[symbol.0 as usize].spelling, "main");
}

#[test]
fn emits_compilable_and_runnable_primitive_cpp() {
    let lowered = lower("fn main(){let left:i64=20;let right:i64=22;let result=left+right;}");
    let unit =
        cpp_backend::emit(&lowered).unwrap_or_else(|errors| panic!("backend errors: {errors:#?}"));
    let directory = tempfile::tempdir().unwrap();
    let source = directory.path().join("program.cpp");
    let executable = directory.path().join("program");
    fs::write(&source, unit.source).unwrap();
    let runtime = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("runtime");
    let compiler = if Command::new("c++").arg("--version").output().is_ok() {
        "c++"
    } else {
        "clang++"
    };
    let compiled = Command::new(compiler)
        .args(["-std=c++20", "-Wall", "-Wextra", "-pedantic"])
        .arg("-I")
        .arg(&runtime)
        .arg(&source)
        .arg("-o")
        .arg(&executable)
        .output()
        .unwrap();
    assert!(
        compiled.status.success(),
        "{}\n{}",
        String::from_utf8_lossy(&compiled.stdout),
        String::from_utf8_lossy(&compiled.stderr)
    );
    let executed = Command::new(&executable).output().unwrap();
    assert!(
        executed.status.success(),
        "status: {}\n{}\n{}",
        executed.status,
        String::from_utf8_lossy(&executed.stdout),
        String::from_utf8_lossy(&executed.stderr)
    );
}

fn compile_and_run(source_text: &str) {
    let lowered = lower(source_text);
    let unit =
        cpp_backend::emit(&lowered).unwrap_or_else(|errors| panic!("backend errors: {errors:#?}"));
    let directory = tempfile::tempdir().unwrap();
    let source = directory.path().join("program.cpp");
    let executable = directory.path().join("program");
    fs::write(&source, &unit.source).unwrap();
    let runtime = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("runtime");
    let compiled = Command::new("c++")
        .args(["-std=c++20", "-Wall", "-Wextra", "-pedantic"])
        .arg("-I")
        .arg(&runtime)
        .arg(&source)
        .arg("-o")
        .arg(&executable)
        .output()
        .unwrap();
    assert!(
        compiled.status.success(),
        "{}\n{}\n{}",
        String::from_utf8_lossy(&compiled.stdout),
        String::from_utf8_lossy(&compiled.stderr),
        unit.source
    );
    let executed = Command::new(&executable).output().unwrap();
    assert!(
        executed.status.success(),
        "status: {}\n{}\n{}\n{}",
        executed.status,
        String::from_utf8_lossy(&executed.stdout),
        String::from_utf8_lossy(&executed.stderr),
        unit.source
    );
}

#[test]
fn emits_resolved_branch_graph() {
    compile_and_run("fn main(){let condition=true;let result:i64=if condition {40+2}else{0};}");
}

#[test]
fn emits_resolved_calls_and_aggregate_offsets() {
    compile_and_run(
        "struct Pair{left:i64;right:i64;} fn make() Pair{Pair{left:20,right:22}} fn main(){let pair=make();let value=pair.left+pair.right;}",
    );
}

#[test]
fn emits_arrays_slices_and_indexing() {
    compile_and_run(
        "fn main(){let items:[i64;3]=[10,20,30];let view=&items[0..2];let value=view[1];}",
    );
}

#[test]
fn emits_enum_construction_and_match_control() {
    compile_and_run(
        "enum Choice{Empty;Value(i64);} fn main(){let choice=Choice::Value(42);let value=match choice {Choice::Empty=>{0},Choice::Value(item)=>{item}};}",
    );
}

#[test]
fn emits_resolved_loop_graph() {
    compile_and_run(
        "fn main(){let mut total:i64=0;let mut index:i64=0;while index<3 {total+=index;index+=1;}}",
    );
}

#[test]
fn emits_planned_cleanup_before_break_and_continue() {
    compile_and_run(
        "struct Marker{value:i64;fn drop(&mut self){}} fn main(){let mut index:i64=0;while index<3 {let marker=Marker{value:index};index+=1;if index==1 {continue;}break;}}",
    );
}

#[test]
fn emits_fixed_array_for_loop() {
    compile_and_run(
        "fn main(){let items:[i64;3]=[1,2,3];let mut total:i64=0;for item in &items[..] {total+=*item;}}",
    );
}

#[test]
fn emits_async_state_machine_definition() {
    compile_and_run("async fn work(value:i64) i64{yield;value} fn main(){}");
}

#[test]
fn emits_nested_await_state_machines() {
    compile_and_run(
        "async fn child(value:i64) i64{yield;value} async fn parent() i64{let future=child(42);let result=future.await;result} fn main(){}",
    );
}

#[test]
fn emits_closure_capture_and_callable_invocation() {
    compile_and_run(
        "fn call(f:fn(i64) i64) i64{f(40)} fn main(){let offset:i64=2;let closure=|value:i64| i64 {value+offset};let direct=closure(1);let indirect=call(closure);}",
    );
}
