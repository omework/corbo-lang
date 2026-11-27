//! Verification starts from resolved PostAST; these fixtures inspect verdicts,
//! not target execution. No legacy checker/backend is involved.
use corbo_frontend::{parse_source, post_ast::*, rule_check, semantic};
fn verify(source: &str) -> RuleAnalysisResult {
    let syntax = parse_source(source.to_owned()).unwrap();
    let semantic =
        semantic::resolve(syntax).unwrap_or_else(|e| panic!("semantic input failed: {e:#?}"));
    rule_check::verify(semantic.logical)
}
fn accepts(source: &str) {
    match verify(source) {
        RuleAnalysisResult::Established(_) => {}
        RuleAnalysisResult::Rejected(r) => {
            panic!("unexpected rule diagnostics: {:?}", r.diagnostics)
        }
        RuleAnalysisResult::MissingSemanticInput(r) => panic!("missing facts: {:?}", r.missing),
    }
}
fn rejects(source: &str, rule: CoreRule) {
    match verify(source) {
        RuleAnalysisResult::Rejected(r) => assert!(
            std::iter::once(&r.diagnostics.first)
                .chain(&r.diagnostics.rest)
                .any(|d| d.rule == rule),
            "wrong rule: {:?}",
            r.diagnostics
        ),
        RuleAnalysisResult::Established(_) => panic!("expected rejection for {rule:?}: {source}"),
        RuleAnalysisResult::MissingSemanticInput(r) => panic!("missing facts: {:?}", r.missing),
    }
}
#[test]
fn ordinary_primitive_flow() {
    accepts("fn main(){let mut n:i64=1;n=2;let observed=n;}");
}
#[test]
fn move_ends_source_availability() {
    rejects(
        "struct Item{n:i64;} fn main(){let a=Item{n:1};let b=a;let observed=a.n;}",
        CoreRule::N6,
    );
}
#[test]
fn moved_destination_remains_usable() {
    accepts("struct Item{n:i64;} fn main(){let a=Item{n:1};let b=a;let observed=b.n;}");
}
#[test]
fn borrowed_local_cannot_escape() {
    rejects(
        "fn invalid() &i64{let a:i64=1;&a} fn main(){}",
        CoreRule::N4,
    );
}
#[test]
fn returned_parameter_borrow_retains_external_lifetime() {
    accepts("fn identity(a:&i64) &i64{a} fn main(){}");
}
#[test]
fn mutable_borrow_ends_at_last_use() {
    accepts("fn main(){let mut a:i64=1;let r=&mut a;*r=2;a=3;let observed=a;}");
}
#[test]
fn overlapping_mutable_borrows_conflict() {
    rejects(
        "fn main(){let mut a:i64=1;let r=&mut a;let s=&mut a;*r=2;*s=3;}",
        CoreRule::N5,
    );
}
#[test]
fn disjoint_fields_share_no_borrow() {
    accepts(
        "struct Pair{a:i64;b:i64;} fn main(){let mut p=Pair{a:1,b:2};let a=&mut p.a;let b=&mut p.b;*a=3;*b=4;}",
    );
}

#[test]
fn sequential_slice_reborrows_end_after_each_call() {
    accepts(
        "fn consume(value:&mut [u8]){} fn work(output:&mut [u8]){consume(&mut output[0..output.len()]);consume(&mut output[0..output.len()]);} fn main(){}",
    );
}

#[test]
fn sequential_calls_reborrow_two_mutable_parameters() {
    accepts(
        "struct Bits{bit:u64;} fn consume(output:&mut [u8],bits:&mut Bits){} fn work(output:&mut [u8],bits:&mut Bits){consume(&mut output[0..output.len()],&mut *bits);consume(&mut output[0..output.len()],&mut *bits);} fn main(){}",
    );
}

#[test]
fn call_site_rejects_two_mutable_arguments_for_the_same_place() {
    rejects(
        "fn consume(left:&mut i64,right:&mut i64){} fn main(){let mut value:i64=1;consume(&mut value,&mut value);}",
        CoreRule::N5,
    );
}

#[test]
fn generic_loop_replaces_and_returns_one_accumulator_owner() {
    accepts(
        "#(type:V) #(type:T<V> with {fn next(&mut self) Option<V>;}) struct Reduce<T,V>{previous:T;mapper:fn(V,V) V;fn remaining(&mut self,mut accumulator:V) V{while true{match self.previous.next(){Some(item)=>{accumulator=(self.mapper)(accumulator,item);},None=>{return accumulator;},}}accumulator}} fn main(){}",
    );
}
#[test]
fn invalid_copy_repetition_is_a_rule_violation() {
    rejects(
        "struct Item{a:&i64;} fn main(){let a:i64=1;let items=[Item{a:&a};2];}",
        CoreRule::N3,
    );
}
#[test]
fn mutually_exclusive_moves_are_valid() {
    accepts(
        "struct Item{n:i64;} fn take(a:Item) i64{a.n} fn choose(flag:bool) i64{let a=Item{n:1};if flag{take(a)}else{take(a)}} fn main(){}",
    );
}
#[test]
fn conditional_move_does_not_restore_availability() {
    rejects(
        "struct Item{n:i64;} fn take(a:Item) i64{a.n} fn f(flag:bool){let a=Item{n:1};if flag{let n=take(a);}let n=a.n;} fn main(){}",
        CoreRule::N6,
    );
}
#[test]
fn loop_back_edge_preserves_move_state() {
    rejects(
        "struct Item{n:i64;} fn take(a:Item) i64{a.n} fn f(flag:bool){let a=Item{n:1};while flag{let n=take(a);}} fn main(){}",
        CoreRule::N6,
    );
}
#[test]
fn primitive_assignment_before_and_inside_loops_preserves_availability() {
    accepts(
        "fn work(count:u64){let mut i:u64=0;while i<count{i=i+1;}i=0;while i<count{i=i+1;}let observed=i;} fn main(){}",
    );
}

#[test]
fn conditional_assignment_preserves_primitive_availability_before_loop() {
    accepts(
        "fn main(){let mut used:u64=0;if used==1{used=2;}let mut merged:u64=1;while merged<used{merged=merged+1;}}",
    );
}

#[test]
fn gzip_entropy_module_satisfies_core_rules() {
    let source = format!(
        "struct Bits{{bit:u64;error:i64;}} fn reverse(value:u64,width:u64) u64{{value}} fn set_bits(bits:&mut Bits,count:u64,error:i64){{}} fn write_bits(output:&mut [u8],bits:&mut Bits,value:u64,count:u64){{}} {}",
        include_str!("../../stdlib/src/compression/gzip/entropy.crb")
    );
    accepts(&source);
}
#[test]
fn nested_branch_locals_remain_available_in_their_own_branch_loop() {
    accepts(
        "fn work(code:u64){let mut i:u64=0;if code<16{i=i+1;}else{let mut value:u64=0;let mut repeats:u64=0;if code==16{if i==0{return;}value=7;repeats=3;}else if code==17{repeats=4;}else{return;}let end=i+repeats;while i<end{let observed=value;i=i+1;}}}fn main(){}",
    );
}
#[test]
fn returned_wrapper_keeps_the_external_mutable_reference_not_the_local_wrapper() {
    accepts(
        "struct Wrapper{source:&mut i64;fn new(source:&mut i64) Wrapper{Wrapper{source:source}}}fn make(source:&mut i64) Wrapper{let wrapper=Wrapper::new(source);wrapper}fn main(){}",
    );
}
#[test]
fn generic_result_wrapper_keeps_only_the_external_reference_dependency() {
    accepts(
        "#(type:E)#(type:R<E> with {fn read(&mut self,output:&mut [u8]) Result<usize,E>;})struct Wrapper<R,E>{source:&mut R;fn new(source:&mut R) Wrapper<R,E>{Wrapper{source:source}}}#(type:E)#(type:R<E> with {fn read(&mut self,output:&mut [u8]) Result<usize,E>;})fn make(source:&mut R) Result<Wrapper<R,E>,E>{let wrapper:Wrapper<R,E>=Wrapper::new(source);Ok(wrapper)}fn main(){}",
    );
}
#[test]
fn disjoint_fields_through_a_mutable_receiver_remain_disjoint() {
    accepts(
        "struct Pair{a:i64;b:i64;fn update(&mut self){let left=&mut (*self).a;let right=&mut (*self).b;*left=3;*right=4;}}fn main(){}",
    );
}
#[test]
fn disjoint_receiver_fields_and_external_slice_do_not_conflict() {
    accepts(
        "struct Reader{buffer:&mut [u8];start:u64;end:u64;fn read(&mut self,output:&mut [u8]){let next=&mut (*self).start;let filled=&mut (*self).end;let buffer=&mut *(*self).buffer;let mut i:u64=0;while i<*filled{output[i]=buffer[*next+i];i=i+1;}*next=*filled;}}fn main(){}",
    );
}

#[test]
fn abstract_result_from_one_field_does_not_borrow_a_disjoint_field() {
    accepts(
        "#(type: V) #(type: T<V> with {fn next(&mut self) Option<V>;}) struct Reader<T,V>{source:T;marker:i64; fn inspect(&mut self) i64{match (*self).source.next(){Some(item)=>{let marker=(*self).marker;marker},None=>{0}}}} fn main(){}",
    );
}

#[test]
fn callable_in_disjoint_field_can_borrow_abstract_result() {
    accepts(
        "#(type: V) #(type: T<V> with {fn next(&mut self) Option<V>;}) struct Filter<T,V>{source:T;predicate:fn(&V) bool; fn next(&mut self) Option<V>{while true{match (*self).source.next(){Some(item)=>{let accepted=((*self).predicate)(&item);if accepted{return Some(item);}},None=>{return None;}}}None}} fn main(){}",
    );
}

#[test]
fn loop_carried_buffer_references_allow_sequential_slice_reborrows() {
    accepts(
        "fn encode(input:&[u8],output:&mut [u8],workspace:&mut [u8]) usize{0} fn process(input:&mut [u8],output:&mut [u8],workspace:&mut [u8]){let mut used:usize=1;let mut iteration:usize=0;while iteration<2{let encoded=encode(&input[0..used],&mut output[0..output.len()],&mut workspace[0..workspace.len()]);iteration+=1;used=encoded;}} fn main(){}",
    );
}

#[test]
fn receiver_buffer_fields_allow_sequential_slice_reborrows_in_a_loop() {
    accepts(
        "fn encode(input:&[u8],output:&mut [u8],workspace:&mut [u8]) usize{0} struct Stream{input:&mut [u8];output:&mut [u8];workspace:&mut [u8];used:usize;fn process(&mut self){let input=&mut *(*self).input;let output=&mut *(*self).output;let workspace=&mut *(*self).workspace;let mut used=(*self).used;let mut iteration:usize=0;while iteration<2{let encoded=encode(&input[0..used],&mut output[0..output.len()],&mut workspace[0..workspace.len()]);iteration+=1;used=encoded;}}} fn main(){}",
    );
}

#[test]
fn receiver_buffer_reborrows_do_not_cover_a_disjoint_error_field() {
    accepts(
        "enum Error{Failed;} fn encode(input:&[u8],output:&mut [u8],workspace:&mut [u8]) Result<usize,Error>{Ok(0)} struct Stream{input:&mut [u8];output:&mut [u8];workspace:&mut [u8];used:usize;failed:bool;fn process(&mut self) Result<usize,Error>{let input=&mut *(*self).input;let output=&mut *(*self).output;let workspace=&mut *(*self).workspace;let mut used=(*self).used;let mut iteration:usize=0;while iteration<2{let encoded=match encode(&input[0..used],&mut output[0..output.len()],&mut workspace[0..workspace.len()]){Ok(value)=>{value},Err(error)=>{let failed=&mut (*self).failed;*failed=true;return Err(error);}};iteration+=1;used=encoded;}Ok(used)}} fn main(){}",
    );
}

#[test]
fn foreign_write_through_an_address_invalidates_the_previous_constant() {
    accepts(
        "fn main(){let mut divisor:u64=0;@unchecked{let address=addr(&mut divisor);@asm{mov rax, ${address}}}if divisor==0{return;}let quotient=10/divisor;}",
    );
}
#[test]
fn call_borrow_ends_before_a_conditional_move_of_the_argument() {
    accepts(
        "struct Item{value:i64;}fn accepted(item:&Item) bool{item.value>0}fn choose(item:Item) Item{let keep=accepted(&item);if keep{return item;}item}fn main(){}",
    );
}
#[test]
fn replacement_requires_a_live_receiver() {
    rejects(
        "struct Item{n:i64;} fn main(){let mut a=Item{n:1};let b=a;a=Item{n:2};let n=a.n;}",
        CoreRule::N6,
    );
}
#[test]
fn immutable_binding_write_is_rejected() {
    rejects("fn main(){let a:i64=1;a=2;}", CoreRule::N3);
}
#[test]
fn shared_reference_does_not_grant_write_permission() {
    rejects("fn main(){let a:i64=1;let r=&a;*r=2;}", CoreRule::N3);
}
#[test]
fn parent_reborrow_is_suspended_while_child_is_live() {
    rejects(
        "fn main(){let mut a:i64=1;let r=&mut a;let s=&mut *r;*r=2;*s=3;}",
        CoreRule::N5,
    );
}
#[test]
fn ordered_child_reborrow_is_valid() {
    accepts("fn main(){let mut a:i64=1;let r=&mut a;let s=&mut *r;*s=2;*r=3;}");
}
#[test]
fn synchronous_await_is_a_boundary_violation() {
    rejects(
        "async fn task() i64{1} fn main(){let n=task().await;}",
        CoreRule::N8,
    );
}
#[test]
fn joined_borrowed_task_is_valid() {
    accepts(
        "async fn child(value:&i64) i64{*value} fn main(){let value:i64=1;let execution=runtime::spawn(child(&value));let n=execution.join()!;}",
    );
}
#[test]
fn unfinished_borrowed_branch_is_rejected() {
    rejects(
        "async fn child(value:&i64) i64{*value} fn main(){let value:i64=1;let execution=runtime::spawn(child(&value));}",
        CoreRule::N4,
    );
}
#[test]
fn exhaustive_match_is_valid() {
    accepts(
        "enum State{On;Off;} fn f(x:State) i64{match x{State::On=>{1},State::Off=>{2}}} fn main(){}",
    );
}
#[test]
fn non_exhaustive_match_is_rejected() {
    rejects(
        "enum State{On;Off;} fn f(x:State) i64{match x{State::On=>{1}}} fn main(){}",
        CoreRule::N6,
    );
}
#[test]
fn nested_patterns_do_not_accept_only_diagonal_payloads() {
    rejects(
        "enum B{On;Off;} enum Pair{Values(B,B);} fn f(x:Pair) i64{match x{Pair::Values(B::On,B::On)=>{1},Pair::Values(B::Off,B::Off)=>{2}}} fn main(){}",
        CoreRule::N6,
    );
}
#[test]
fn move_while_borrow_is_live_is_rejected() {
    rejects(
        "struct Item{n:i64;} fn main(){let a=Item{n:1};let r=&a.n;let b=a;let n=*r;}",
        CoreRule::N5,
    );
}
#[test]
fn borrowing_a_moved_value_is_rejected() {
    rejects(
        "struct Item{n:i64;} fn main(){let a=Item{n:1};let b=a;let r=&a;}",
        CoreRule::N6,
    );
}
#[test]
fn mutable_borrow_requires_permission() {
    rejects("fn main(){let a:i64=1;let r=&mut a;}", CoreRule::N3);
}
#[test]
fn zero_divisor_is_refused_statically() {
    rejects("fn main(){let n:i64=1/0;}", CoreRule::N1);
}
#[test]
fn known_shift_count_is_checked() {
    rejects("fn main(){let n:u8=1;let result=n<<8;}", CoreRule::N1);
}
#[test]
fn shared_argument_lifetime_is_not_copied_into_scalar_result() {
    accepts("fn read(x:&i64) i64{*x} fn main(){let value={let n:i64=1;read(&n)};}");
}
#[test]
fn object_lock_reentry_is_refused() {
    rejects(
        "#(lock) struct Counter{pub fn first(&self) i64{self.second()} pub fn second(&self) i64{1}} fn main(){}",
        CoreRule::N5,
    );
}
#[test]
fn indirect_object_lock_reentry_is_refused() {
    rejects(
        "#(lock) struct Counter{pub fn first(&self) i64{relay(self)} pub fn second(&self) i64{1}} fn relay(x:&Counter) i64{x.second()} fn main(){}",
        CoreRule::N5,
    );
}
#[test]
fn borrowed_task_result_keeps_its_dependency_after_join() {
    rejects(
        "async fn borrow(x:&i64) &i64{x} fn main(){let r={let n:i64=1;let h=runtime::spawn(borrow(&n));h.join()!};let n=*r;}",
        CoreRule::N4,
    );
}
#[test]
fn borrowed_task_result_from_an_external_target_is_valid() {
    accepts(
        "async fn borrow(x:&i64) &i64{x} fn main(){let n:i64=1;let r={let h=runtime::spawn(borrow(&n));h.join()!};let value=*r;}",
    );
}
#[test]
fn borrowed_async_result_keeps_its_dependency_after_await() {
    rejects(
        "async fn borrow(x:&i64) &i64{x} async fn run(){let r={let n:i64=1;borrow(&n).await};let n=*r;} fn main(){}",
        CoreRule::N4,
    );
}
#[test]
fn unused_reference_cannot_transfer_past_its_target() {
    rejects("fn main(){let r={let n:i64=1;&n};}", CoreRule::N4);
}
#[test]
fn autonomous_task_state_is_owned_by_execution_branch() {
    let s = semantic::resolve(
        parse_source("async fn work() i64{1} fn main(){let h=runtime::spawn(work());}".to_owned())
            .unwrap(),
    )
    .unwrap();
    assert!(
        s.logical
            .semantics
            .post_ast
            .objects
            .ownership
            .iter()
            .any(|l| matches!(l.owner, Owner::ExecutionBranch { .. }))
    );
    assert!(
        s.logical
            .finals
            .iter()
            .any(|f| matches!(f.cleanup_exit, LogicalCleanupSite::ExecutionBranchEnd(_)))
    );
    assert!(matches!(
        rule_check::verify(s.logical),
        RuleAnalysisResult::Established(_)
    ));
}
#[test]
fn source_pool_cannot_die_before_its_allocation() {
    rejects(
        "fn main(){let a={let mut p=Pool<i64>::new(2);p.new(1)};}",
        CoreRule::N4,
    );
}
#[test]
fn dropping_a_primitive_consumes_the_binding() {
    rejects("fn main(){let n:i64=1;drop(n);let other=n;}", CoreRule::N6);
}

#[test]
fn each_loop_iteration_can_destroy_its_own_value() {
    accepts(
        "struct Item{n:i64;} fn main(){let mut i:i64=0;while i<2{let value=Item{n:i};drop(value);i+=1;}}",
    );
}
#[test]
fn user_code_cannot_call_a_destructor_method() {
    rejects(
        "struct Resource{n:i64;fn drop(&mut self){self.n=0;}} fn main(){let mut r=Resource{n:1};r.drop();}",
        CoreRule::N7,
    );
}
#[test]
fn explicit_drop_is_not_scheduled_again_at_scope_exit() {
    let source = "struct Resource{n:i64;} fn main(){let r=Resource{n:1};drop(r);}";
    match verify(source) {
        RuleAnalysisResult::Established(p) => {
            let ids = p
                .semantics
                .semantics
                .post_ast
                .bodies
                .iter()
                .flat_map(|b| &b.operations)
                .filter_map(|o| {
                    if let Operation::DropValue(x) = o {
                        Some(x.value)
                    } else {
                        None
                    }
                })
                .collect::<Vec<_>>();
            let destroyed = p
                .semantics
                .semantics
                .post_ast
                .objects
                .value_entities
                .iter()
                .filter(|v| ids.contains(&v.value))
                .map(|v| v.entity.clone())
                .collect::<Vec<_>>();
            assert!(
                p.derived
                    .cleanup
                    .iter()
                    .flat_map(|e| &e.steps)
                    .all(|step| match step {
                        VerifiedDestructionStep::OwnedComponent { parent: entity, .. }
                        | VerifiedDestructionStep::Hook { entity, .. }
                        | VerifiedDestructionStep::EndLifetime { entity, .. } =>
                            !destroyed.contains(entity),
                    })
            );
        }
        RuleAnalysisResult::Rejected(r) => panic!("{:?}", r.diagnostics),
        RuleAnalysisResult::MissingSemanticInput(r) => panic!("{:?}", r.missing),
    }
}
#[test]
fn static_literal_borrow_can_be_returned() {
    accepts("fn name() &str{\"Corbo\"} fn main(){}");
}
#[test]
fn replacing_a_reference_field_preserves_the_new_dependency() {
    rejects(
        "struct View{value:&i64;} fn main(){let stable:i64=1;let mut view=View{value:&stable};{let temporary:i64=2;view.value=&temporary;}let value=*view.value;}",
        CoreRule::N4,
    );
}
#[test]
fn returned_reference_through_a_function_keeps_the_actual_target() {
    rejects(
        "fn borrow(x:&i64) &i64{x} fn main(){let view={let n:i64=1;borrow(&n)};let n=*view;}",
        CoreRule::N4,
    );
}
#[test]
fn copied_enums_have_independent_cleanup_owners() {
    accepts(
        "enum Resource{Handle(i64);fn drop(&mut self){}} fn main(){let first=Resource::Handle(10);let second=first;drop(first);let third=second;drop(second);drop(third);}",
    );
    rejects(
        "enum Resource{Handle(i64);fn drop(&mut self){}} fn main(){let first=Resource::Handle(10);let second=first;drop(first);let invalid=first;}",
        CoreRule::N6,
    );
}

#[test]
fn explicit_enum_copy_and_drop_have_the_same_ownership_rule() {
    accepts(
        "enum Resource{Handle(i64);fn drop(&mut self){}} fn main(){let first=Resource::Handle(10);let second=copy(first);drop(first);drop(second);}",
    );
}

#[test]
fn hook_does_not_replace_owned_component_destruction() {
    let result = verify(
        "struct Child{value:i64;fn drop(&mut self){self.value=0;}} struct Parent{child:Child;fn drop(&mut self){}} fn main(){let p=Parent{child:Child{value:1}};}",
    );
    let RuleAnalysisResult::Established(result) = result else {
        panic!("expected a checked destruction chain")
    };
    let steps = result
        .derived
        .cleanup
        .iter()
        .flat_map(|e| &e.steps)
        .collect::<Vec<_>>();
    assert!(
        steps
            .iter()
            .any(|s| matches!(s, VerifiedDestructionStep::Hook { .. }))
    );
    assert!(
        steps
            .iter()
            .any(|s| matches!(s, VerifiedDestructionStep::OwnedComponent { .. }))
    );
    assert!(
        steps
            .iter()
            .any(|s| matches!(s, VerifiedDestructionStep::EndLifetime { .. }))
    );
}
#[test]
fn destructor_hook_cannot_consume_its_borrowed_object() {
    rejects(
        "struct Item{value:i64;fn drop(&mut self){drop(*self);}} fn main(){let item=Item{value:1};}",
        CoreRule::N3,
    );
}

#[test]
fn recursive_result_dependencies_preserve_all_formal_origins() {
    rejects(
        "fn choose(a:&i64,b:&i64,n:i64) &i64 {if n==0 {a} else {choose(b,a,n-1)}} fn invalid(external:&i64,n:i64) &i64 {let local:i64=7;choose(external,&local,n)} fn main(){}",
        CoreRule::N4,
    );
}
#[test]
fn recursive_result_dependencies_allow_external_origins() {
    accepts(
        "fn choose(a:&i64,b:&i64,n:i64) &i64 {if n==0 {a} else {choose(b,a,n-1)}} fn valid(a:&i64,b:&i64,n:i64) &i64 {choose(a,b,n)} fn main(){}",
    );
}

#[test]
fn raw_address_confinement_survives_copy_and_aggregate_wrapping() {
    rejects(
        "struct Wrapped{address:usize;} fn invalid() Wrapped {let n:i64=1;@unchecked {let raw=addr(n);let copied=raw;Wrapped{address:copied}}} fn main(){}",
        CoreRule::N4,
    );
}
#[test]
fn raw_address_can_be_used_inside_its_unchecked_scope() {
    accepts(
        "fn main(){let n:i64=1;@unchecked {let raw=addr(n);let copied=raw;let observed=copied;}}",
    );
}
#[test]
fn unchecked_boundary_may_construct_an_interior_mutable_reference() {
    accepts(
        "struct Cell{value:i64;fn access(&self) &mut i64{@unchecked{return &mut (*self).value;}}}fn main(){}",
    );
}

#[test]
fn later_iteration_join_does_not_complete_an_earlier_task() {
    rejects(
        "async fn read(n:&i64) i64 {*n} fn work(mut first:bool){let n:i64=1;loop{let execution=runtime::spawn(read(&n));if first{first=false;continue;}let result=execution.join();break;}} fn main(){}",
        CoreRule::N4,
    );
}
#[test]
fn each_iteration_can_complete_its_own_task() {
    accepts(
        "async fn read(n:&i64) i64 {*n} fn work(flag:bool){let n:i64=1;while flag{let execution=runtime::spawn(read(&n));let result=execution.join();}} fn main(){}",
    );
}

#[test]
fn owned_formal_contents_retain_caller_lifetime_dependencies() {
    rejects(
        "struct Wrapped{target:&i64;} fn forward(value:Wrapped) Wrapped {value} fn invalid() Wrapped {let local:i64=1;forward(Wrapped{target:&local})} fn main(){}",
        CoreRule::N4,
    );
}
#[test]
fn owned_formal_contents_can_carry_external_dependencies() {
    accepts(
        "struct Wrapped{target:&i64;} fn forward(value:Wrapped) Wrapped {value} fn valid(external:&i64) Wrapped {forward(Wrapped{target:external})} fn main(){}",
    );
}

#[test]
fn projected_reference_return_keeps_selected_target() {
    rejects(
        "struct Pair{first:&i64;second:&i64;} fn second(value:Pair) &i64{&*value.second} fn invalid(external:&i64) &i64{let local:i64=1;second(Pair{first:external,second:&local})} fn main(){}",
        CoreRule::N4,
    );
}
#[test]
fn projected_reference_return_does_not_keep_unselected_target() {
    accepts(
        "struct Pair{first:&i64;second:&i64;} fn first(value:Pair) &i64{&*value.first} fn valid(external:&i64) &i64{let local:i64=1;first(Pair{first:external,second:&local})} fn main(){}",
    );
}

#[test]
fn independent_cleanup_uses_reverse_receipt_order_after_a_move() {
    let RuleAnalysisResult::Established(checked) = verify(
        "struct Item{n:i64;fn drop(&mut self){}} fn main(){let a=Item{n:1};let b=Item{n:2};let c=a;}",
    ) else {
        panic!("valid cleanup program rejected");
    };
    let p = &checked.semantics.semantics.post_ast;
    let entity = |name: &str| {
        let binding = p
            .scopes
            .bindings
            .iter()
            .find(|binding| p.symbols.entries[binding.symbol.0 as usize].spelling == name)
            .unwrap();
        p.objects.ownership.iter().find(|link| matches!(link.owner, Owner::Binding { binding: owner, .. } if owner == binding.id)).map(|link| link.entity.clone()).unwrap()
    };
    let a = entity("a");
    let b = entity("b");
    let sequence = checked
        .derived
        .cleanup
        .iter()
        .flat_map(|cleanup| cleanup.steps.iter())
        .filter_map(|step| match step {
            VerifiedDestructionStep::Hook { entity, .. } if *entity == a || *entity == b => {
                Some(entity.clone())
            }
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(
        sequence,
        vec![a, b],
        "the most recent receiver c is destroyed before b"
    );
}

#[test]
fn allocation_use_after_explicit_source_pool_destruction_is_rejected() {
    rejects(
        "fn main(){let mut pool=Pool<i64>::new(2);let item=pool.new(1);drop(pool);let observed=*item;}",
        CoreRule::N4,
    );
}
#[test]
fn moving_the_source_pool_does_not_destroy_its_allocations() {
    accepts(
        "fn main(){let mut pool=Pool<i64>::new(2);let item=pool.new(1);let moved_pool=pool;let observed=*item;}",
    );
}

#[test]
fn compound_assignment_write_conflicts_with_a_live_borrow() {
    rejects(
        "fn main(){let mut n:i64=1;let view=&n;n+=1;let observed=*view;}",
        CoreRule::N5,
    );
}
#[test]
fn compound_assignment_of_a_disjoint_field_is_valid() {
    accepts(
        "struct Pair{a:i64;b:i64;} fn main(){let mut pair=Pair{a:1,b:2};let view=&pair.a;pair.b+=1;let observed=*view;}",
    );
}

#[test]
fn next_iteration_borrow_is_not_a_use_of_the_previous_descriptor() {
    accepts(
        "fn work(flag:bool){let mut n:i64=1;while flag{let view=&n;let observed=*view;n+=1;}} fn main(){}",
    );
}
#[test]
fn borrow_created_outside_the_loop_remains_live_across_iterations() {
    rejects(
        "fn work(flag:bool){let mut n:i64=1;let view=&n;while flag{n+=1;let observed=*view;}} fn main(){}",
        CoreRule::N5,
    );
}

#[test]
fn shared_reference_field_is_copied_from_a_borrowed_record() {
    accepts("struct Header{field_name:&str;fn name(&self) &str{(*self).field_name}} fn main(){}");
}

#[test]
fn consuming_custom_destructor_payload_is_not_silently_established() {
    let result = verify(
        "struct Item{value:i64;} enum Packet{Stored(Item);fn drop(&mut self){match &*self{Packet::Stored(item)=>{let observed=item.value;}}}} fn extract(packet:Packet) Item{match packet{Packet::Stored(item)=>{item}}} fn main(){}",
    );
    let RuleAnalysisResult::Rejected(rejected) = result else {
        panic!("unresolved destruction contract must not establish verification");
    };
    assert!(
        std::iter::once(&rejected.diagnostics.first)
            .chain(&rejected.diagnostics.rest)
            .any(|diagnostic| diagnostic.rule == CoreRule::N7 && !diagnostic.established_violation)
    );
}
