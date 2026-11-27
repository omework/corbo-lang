//! Grammar-family coverage of the semantic handoff, not an N1–N8 checker.
use corbo_frontend::{ast::NodeKind, parse_source, semantic};
use std::collections::BTreeSet;

#[test]
fn every_ast_construct_has_a_resolved_semantic_context() {
    let sources = [
        (
            vec![],
            "main.crb",
            r#"
            use app::helper::{Number as Boxed, answer};
            #(datastack: size=4M)
            #(configurable) const SIZE:usize=2;
            #(if: target.family == "unix" || target.family == "windows") const ENABLED:bool=true; #(endif)
            enum Choice { Empty; Item(i64); Named { value:i64; }; }
            #(type: R)
            #(type: S<R:i64,u64> with {fn get(&self) R;})
            fn fetch(source:&S) R {source.get()}
            #(type: T with { fn get(&self) i64; } | { fn get(&self) i64; })
            fn read(value:&T) i64 {value.get()}
            async fn task(value:i64) i64 {yield;value}
            async fn consume() Result<i64,i64> {
                let pending=async move {task(1).await};
                let value=pending.await;
                let result:Result<i64,i64>=Ok(value);
                let extracted=result?;
                Ok(extracted)
            }
            fn main() {
                let number=answer();
                let box=Boxed {value:number};
                let value=read(&box);
                let fetched=fetch(&box);
                let mut pair=(number,1);
                pair.0=2;
                let (left,right)=pair;
                let mut data=[left,right];
                let view=&mut data[..SIZE];
                view[0]+=1;
                let widened=1 as u64;
                let chosen=if ENABLED {value+1} else {0};
                let variant=Choice::Item(chosen);
                if let Choice::Item(item)=variant {let n=item;}
                let selected=match variant {Choice::Empty=>{0},Choice::Item(item)=>{item},Choice::Named{value:item}=>{item}};
                let stop=loop {break selected;};
                let mut index=0;
                while index<2 {index+=1;if index==1 {continue;}}
                for element in data.ref() {let n=*element;}
                let closure=|v:i64| i64 {return v+1;};
                let call=(closure)(stop);
                let moved=move {number};
                {move number;let n=number;}
                let unwrapped:Option<i64>=Some(1);
                let n=unwrapped!;
                @unchecked {
                    let address=addr(index);
                    @c(includes={"stdint.h"}) { ${index} = 1; }
                    @c++ { ${index} = 2; }
                    @asm { nop }
                }
            }
        "#,
        ),
        (
            vec!["helper"],
            "helper.crb",
            r#"
            pub struct Number {
                pub value:i64;
                pub fn get(&self) i64 {self.value}
            }
            pub fn answer() i64 {42}
        "#,
        ),
    ];
    let modules = sources
        .into_iter()
        .map(|(path, file, source)| semantic::ParsedModule {
            package: "app".into(),
            path: path.into_iter().map(str::to_owned).collect(),
            file_path: file.into(),
            syntax: parse_source(source.into()).unwrap(),
        })
        .collect();
    let result = semantic::resolve_package(modules).unwrap_or_else(|e| panic!("{e:#?}"));
    semantic::validate_population(&result.logical).unwrap();
    let mut encountered = BTreeSet::new();
    for input in &result.modules {
        for node in &input.syntax.ast.nodes {
            semantic::grammar::context(&node.kind);
            encountered.insert(semantic::grammar::construct_name(&node.kind));
        }
    }
    let mapping = include_str!("../../docs/architecture/post_ast_mapping.csv");
    let expected: BTreeSet<_> = mapping
        .lines()
        .skip(1)
        .filter_map(|line| line.split(',').next())
        .collect();
    let missing: Vec<_> = expected.difference(&encountered).collect();
    assert!(
        missing.is_empty(),
        "AST constructs missing from successfully resolved corpus: {missing:?}"
    );
    assert_eq!(
        expected, encountered,
        "grammar map and AST semantic inventory differ"
    );
    assert!(
        result
            .modules
            .iter()
            .flat_map(|m| &m.syntax.ast.nodes)
            .any(|n| matches!(n.kind, NodeKind::Range { .. }))
    );
}

#[test]
fn operator_and_external_function_forms_have_concrete_operations() {
    use corbo_frontend::post_ast::*;
    let unit = parse_source(
        r#"
        extern "C" fn external(value:i64) i64;
        fn main(){
            let mut n:u64=1;
            n+=1;n-=1;n*=2;n/=2;n%=3;n&=7;n|=2;n^=1;n<<=1;n>>=1;
            let a=n+1;let b=n-1;let c=n*2;let d=n/2;let e=n%3;
            let f=n&7;let g=n|2;let h=n^1;let i=n<<1;let j=n>>1;
            let k=~n;let l= -1;let m= !(n==2);
            let less=n<3;let more=n>3;let le=n<=3;let ge=n>=3;let ne=n!=3;
            let boolean=(less&&more)||ne;
            @unchecked {let returned=external(1);}
        }
    "#
        .into(),
    )
    .unwrap();
    let resolved = semantic::resolve(unit).unwrap();
    let p = &resolved.logical.semantics.post_ast;
    assert!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .any(|o| matches!(o, Operation::ExternalCall(_)))
    );
    assert_eq!(
        p.bodies
            .iter()
            .flat_map(|b| &b.operations)
            .filter(|o| matches!(
                o,
                Operation::AddAssign(_)
                    | Operation::SubtractAssign(_)
                    | Operation::MultiplyAssign(_)
                    | Operation::DivideAssign(_)
                    | Operation::RemainderAssign(_)
                    | Operation::BitAndAssign(_)
                    | Operation::BitOrAssign(_)
                    | Operation::BitXorAssign(_)
                    | Operation::ShiftLeftAssign(_)
                    | Operation::ShiftRightAssign(_)
            ))
            .count(),
        10
    );
}
