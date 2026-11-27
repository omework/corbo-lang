//! Emit C from the typed instructions produced by the verifier.

use crate::placement::{
    BindingStorage, Destination, Footprint, FootprintStep, FunctionPlacement, GrowthUnit,
    ValueDestination, ValueReservation,
};
use crate::verify::{
    Expr, Function, Growing, Instr, OwnedResource, Ownership, Referent, Structure, Ty, Value,
    VerifiedProgram, contains_handle, layout_dependencies,
};
use std::{
    collections::{BTreeMap, BTreeSet},
    fmt::Write,
};

const PRELUDE: &str = r#"#include <stdbool.h>
#include <stdint.h>
#include <limits.h>
#include <inttypes.h>
#include <math.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct { const void *data; uintptr_t len; } CrustSlice;

#define crust_arithmetic_error() do { \
    fputs("corbo: erreur arithmetique\n", stderr); \
    exit(EXIT_FAILURE); \
} while (0)

"#;

pub fn emit_c(program: &VerifiedProgram) -> String {
    let mut uses_storage = program.ownership.iter().any(Option::is_some)
        || program.functions.iter().any(|function| {
            owned_resource(function.result, program).is_some()
                || function
                    .parameters
                    .iter()
                    .any(|(_, ty)| owned_resource(*ty, program).is_some())
        })
        || program.placement.functions.iter().any(|placement| {
            !placement.before.is_empty()
                || !placement.parameters.is_empty()
                || placement
                    .values_before
                    .values()
                    .flatten()
                    .any(|reservation| reservation.storage(placement).is_some())
        });
    let uses_async = program
        .functions
        .iter()
        .any(|function| function.asynchronous);
    let uses_threads = uses_async
        || program
            .structures
            .iter()
            .enumerate()
            .any(|(index, _)| contains_handle(Ty::Struct(index), &program.structures))
        || program.functions.iter().any(|function| {
            function.native
                || matches!(function.result, Ty::Handle(..))
                || function
                    .parameters
                    .iter()
                    .any(|(_, ty)| matches!(ty, Ty::Handle(..)))
        });
    uses_storage |= uses_threads;
    let uses_regions = uses_threads
        || program.stack_sizes.reclaim_threshold.is_some()
        || program.stack_sizes.region_reclaim_threshold.is_some()
        || program
            .structures
            .iter()
            .any(|layout| layout.growing.is_some())
        || program
            .functions
            .iter()
            .any(|function| has_region_scope(&function.body));
    let mut output = if uses_storage || uses_regions {
        String::from(include_str!("datastack.c"))
    } else {
        String::from("#include <stddef.h>\nstatic size_t crust_cursor;\n")
    };
    if uses_threads {
        output.insert_str(
            0,
            "#define CRUST_LOCAL _Thread_local\n#define CRUST_HAS_THREADS 1\n",
        );
    }
    output.push_str(PRELUDE);
    if program.process_args {
        output.push_str(include_str!("process_args.c"));
    }
    if let Some(bits) = program.pointer_width {
        writeln!(output, "_Static_assert(sizeof(uintptr_t) * CHAR_BIT == {bits}, \"Crust target pointer width mismatch\");").unwrap();
    }
    let mut assembly_sites = BTreeSet::new();
    for function in &program.functions {
        emit_assembly_functions(&mut output, &function.body, &mut assembly_sites);
    }
    output.push_str("enum { CRUST_REHOME, CRUST_DETACH, CRUST_ATTACH, CRUST_DESTROY, CRUST_DROP, CRUST_ADOPT, CRUST_EXTRACT, CRUST_FINALIZE, CRUST_UNREGISTER };\n");
    if uses_threads {
        output.push_str("#define CRUST_DRAIN_THREADS() crust_thread_drain()\n");
    } else {
        output.push_str("#define CRUST_DRAIN_THREADS() ((void)0)\n");
    }
    if uses_storage {
        output.push_str("#define CRUST_HAS_DATASTACK 1\n");
    }
    let uses_maps = program
        .structures
        .iter()
        .any(|layout| matches!(layout.growing, Some(Growing::Map(..))));
    if uses_maps {
        output.push_str("#define CRUST_HAS_MAPS 1\n");
    }
    if uses_threads {
        output.push_str("#include <pthread.h>\n");
    }
    if uses_async {
        output.push_str("#define CRUST_HAS_ASYNC 1\n");
    }
    if uses_regions {
        output.push_str("#define CRUST_HAS_REGIONS 1\n");
        output.push_str(include_str!("region_storage.c"));
        if uses_threads {
            output.push_str(include_str!("native_thread.c"));
            if uses_async {
                output.push_str(include_str!("async_queue.c"));
                if let Some([create, watch, wait]) = program.socket_reactor {
                    writeln!(output, "extern void crust_fn_{create}(int64_t *);").unwrap();
                    writeln!(output, "extern void crust_fn_{watch}(int64_t *, int64_t, uint64_t, bool, uintptr_t);").unwrap();
                    writeln!(output, "extern void crust_fn_{wait}(uintptr_t *, int64_t);").unwrap();
                    writeln!(output, "#define CRUST_SOCKET_CREATE crust_fn_{create}\n#define CRUST_SOCKET_WATCH crust_fn_{watch}\n#define CRUST_SOCKET_WAIT crust_fn_{wait}").unwrap();
                    output.push_str(include_str!("socket_reactor.c"));
                }
                if let Some([create, attach, submit, next]) = program.socket_completion {
                    writeln!(output, "extern void crust_fn_{create}(uintptr_t *);").unwrap();
                    writeln!(
                        output,
                        "extern void crust_fn_{attach}(int64_t *, uintptr_t, uint64_t);"
                    )
                    .unwrap();
                    writeln!(
                        output,
                        "extern void crust_fn_{submit}(int64_t *, uintptr_t);"
                    )
                    .unwrap();
                    writeln!(
                        output,
                        "extern void crust_fn_{next}(uintptr_t *, uintptr_t);"
                    )
                    .unwrap();
                    writeln!(output, "#define CRUST_IOCP_CREATE crust_fn_{create}\n#define CRUST_IOCP_ATTACH crust_fn_{attach}\n#define CRUST_IOCP_SUBMIT crust_fn_{submit}\n#define CRUST_IOCP_NEXT crust_fn_{next}").unwrap();
                    output.push_str(include_str!("socket_iocp.c"));
                }
            }
        }
        if uses_maps {
            output.push_str(include_str!("region_map.c"));
        }
    } else {
        output.push_str("#define CRUST_REGION_MARK(name) CRUST_POOL_MARK(name)\n#define crust_scope_rewind(mark, region, fixed_threshold, regional_threshold, force) do { CRUST_POOL_REWIND(region); crust_rewind(mark); } while (0)\n");
    }
    if uses_threads
        || program
            .structures
            .iter()
            .enumerate()
            .any(|(index, layout)| layout.pool.is_some() || program.ownership[index].is_some())
        || program.functions.iter().any(|function| {
            matches!(function.result, Ty::Allocation(_))
                || function
                    .parameters
                    .iter()
                    .any(|(_, ty)| matches!(ty, Ty::Allocation(_)))
        })
    {
        output.push_str("#define CRUST_HAS_POOLS 1\n");
        if program
            .structures
            .iter()
            .any(|layout| layout.destructor.is_some())
        {
            output.push_str("#define CRUST_HAS_DESTRUCTORS 1\n");
            output.push_str(include_str!("destructors.c"));
        }
        let runtime = include_str!("pool_storage.c");
        output.push_str(runtime);
        if uses_maps {
            output.push_str("static inline __attribute__((unused)) void crust_map_destroy_allocation(void *entry) { crust_pool_resource(*(CrustAllocation **)entry, 0, CRUST_DESTROY); }\n");
        }
    } else {
        output.push_str("typedef struct CrustAllocation CrustAllocation;\n#define crust_rewind(mark) (crust_cursor = (mark))\n#define CRUST_POOL_MARK(name)\n#define CRUST_POOL_REWIND(name) ((void)0)\n");
    }
    if uses_async {
        output.push_str(include_str!("async_context.c"));
    }
    for index in 0..program.structures.len() {
        writeln!(
            output,
            "typedef struct CrustStruct{index} CrustStruct{index};"
        )
        .unwrap();
    }
    let mut defined = vec![false; program.structures.len()];
    for index in 0..defined.len() {
        define_layout(&mut output, &program.structures, &mut defined, index);
    }

    if uses_threads {
        for (index, function) in program
            .functions
            .iter()
            .enumerate()
            .filter(|(_, function)| function.native || function.asynchronous)
        {
            let result_type = if function.result == Ty::Void {
                "unsigned char".to_owned()
            } else {
                stored_type(function.result)
            };
            writeln!(output, "typedef struct {{").unwrap();
            output.push_str("    CrustHandle handle;\n");
            writeln!(output, "    {result_type} result;").unwrap();
            if function.asynchronous {
                output.push_str("    size_t pc;\n    CrustAsyncContext context;\n");
                let placement = &program.placement.functions[index];
                for &(binding, ty) in &function.parameters {
                    if matches!(ty, Ty::Struct(_)) {
                        writeln!(output, "    {} capture{};", stored_type(ty), binding.0).unwrap();
                    }
                }
                for (name, ty) in async_fields(placement, program) {
                    writeln!(output, "    {ty} {name};").unwrap();
                }
                for (&binding, &ty) in &placement.frame_values {
                    let pointer = if placement.frame_binding_aliases.contains(&binding) {
                        "*"
                    } else {
                        ""
                    };
                    writeln!(output, "    {} {pointer}b{binding};", c_type(ty)).unwrap();
                }
            } else {
                let width = program.placement.functions[index].caller_slots;
                if width != 0 {
                    writeln!(output, "    {result_type} output[{width}];").unwrap();
                }
                for (position, &(_, ty)) in function.parameters.iter().enumerate() {
                    writeln!(output, "    {} capture{position};", stored_type(ty)).unwrap();
                }
            }
            writeln!(output, "}} CrustThreadFrame{index};").unwrap();
        }
    }
    if program.stack_sizes.size.is_none() {
        let mut emitted = BTreeSet::new();
        if uses_storage && let Some(footprint) = &program.placement.footprint {
            emit_footprint(&mut output, footprint, &mut emitted);
        }
        for footprint in program.placement.worker_footprints.values() {
            emit_footprint(&mut output, footprint, &mut emitted);
        }
    }
    for (index, function) in program
        .functions
        .iter()
        .enumerate()
        .filter(|(_, function)| !function.asynchronous)
    {
        writeln!(
            output,
            "{};",
            signature(
                function,
                index,
                &program.placement.functions[index],
                program.process_args
            )
        )
        .unwrap();
    }
    emit_resource_walkers(&mut output, program);
    if uses_threads {
        emit_native_workers(&mut output, program);
    }
    if uses_async {
        emit_async_workers(&mut output, program);
    }
    for (index, function) in program
        .functions
        .iter()
        .enumerate()
        .filter(|(_, function)| !function.asynchronous)
    {
        let placement = &program.placement.functions[index];
        writeln!(
            output,
            "\n{} {{",
            signature(function, index, placement, program.process_args)
        )
        .unwrap();
        if placement.caller_slots > 0 || (!function.entry && scalar_result(function.result)) {
            output.push_str("    (void)crust_out;\n");
        }
        if function.entry && program.process_args {
            output.push_str("    crust_args_init(argc, argv);\n");
        }
        if function.entry && uses_storage {
            if let Some(size) = program.stack_sizes.size {
                writeln!(output, "    crust_set_capacity(UINT64_C({size}));").unwrap();
            } else if let Some(footprint) = &program.placement.footprint {
                writeln!(
                    output,
                    "    crust_set_capacity(crust_bound_{}(0));",
                    footprint.entry
                )
                .unwrap();
            }
        }
        if function.entry && uses_regions {
            let limit = emit_region_bound(
                &mut output,
                program.placement.footprint.as_ref(),
                program.stack_sizes.region_size.is_none(),
            );
            let slots = placement.regions.slots;
            let limit = program
                .stack_sizes
                .region_size
                .map_or(limit, |bytes| format!("UINT64_C({bytes})"));
            writeln!(
                output,
                "    crust_regions_configure(UINT64_C({}), {limit}, {slots});",
                program.stack_sizes.region_stack_size.unwrap_or(0)
            )
            .unwrap();
        }
        output.push_str(
            "    size_t crust_frame = crust_cursor;\n    CRUST_REGION_MARK(crust_region_frame);\n",
        );
        for (binding, ty) in &function.parameters {
            if function.borrowed_parameters.contains(binding) {
                writeln!(output, "    (void)sizeof(b{});", binding.0).unwrap();
                continue;
            }
            if let Some(resource @ OwnedResource::Inline(_)) = owned_resource(*ty, program) {
                writeln!(
                    output,
                    "    {}",
                    resource_call(
                        resource,
                        &format!("b{}", binding.0),
                        "crust_pool_current_owner()",
                        "CRUST_REHOME"
                    )
                )
                .unwrap();
            }
            if map_type(*ty, &program.structures) {
                writeln!(
                    output,
                    "    b{}->contents.owner = crust_map_depth;",
                    binding.0
                )
                .unwrap();
            }
            if !placement.parameters.iter().any(|(id, _)| id == binding) {
                writeln!(output, "    (void)sizeof(b{});", binding.0).unwrap();
            }
        }
        for &(binding, ty) in &placement.parameters {
            if function.borrowed_parameters.contains(&binding) {
                continue;
            }
            let id = binding.0;
            let handle = matches!(ty, Ty::Handle(..) | Ty::Future(_));
            let resource = owned_resource(ty, program);
            let ty = c_type(ty);
            writeln!(output, "    {ty} *b{id} = crust_reserve({ty}, 1);").unwrap();
            writeln!(output, "    *b{id} = p{id};").unwrap();
            if handle {
                writeln!(output, "    crust_thread_own(*b{id}, crust_thread_depth);").unwrap();
            }
            if matches!(resource, Some(OwnedResource::Slot)) {
                writeln!(
                    output,
                    "    crust_pool_resource(*b{id}, crust_pool_current_owner(), CRUST_REHOME);"
                )
                .unwrap();
            }
        }
        let mut instruction = 0;
        body(
            &mut output,
            &function.body,
            1,
            function.entry,
            placement,
            &mut instruction,
            None,
            0,
            program,
            false,
        );
        output.push_str("}\n");
    }
    output
}

fn emit_region_bound(
    output: &mut String,
    footprint: Option<&Footprint>,
    infer_limit: bool,
) -> String {
    let growth = footprint.and_then(crate::placement::region_growth);
    if infer_limit && let Some(growth) = growth {
        output.push_str("    size_t region_bytes = 0;\n");
        for (ty, count) in growth {
            let unit = match ty {
                GrowthUnit::Element(ty) => format!("sizeof({})", stored_type(ty)),
                GrowthUnit::ThreadFrame(worker) => format!("sizeof(CrustThreadFrame{worker})"),
                GrowthUnit::MapEntry(ty) => {
                    format!("crust_map_growth_bound(sizeof({}))", stored_type(ty))
                }
            };
            writeln!(
                output,
                "    region_bytes = crust_advance(region_bytes, {unit}, 1, {count});"
            )
            .unwrap();
        }
        output.push_str("    if (region_bytes == 0) region_bytes = 1;\n");
        "region_bytes".to_owned()
    } else {
        "0".to_owned()
    }
}

fn emit_native_workers(output: &mut String, program: &VerifiedProgram) {
    let fixed = program.stack_sizes.size.unwrap_or(0);
    let region_limit = program.stack_sizes.region_size.unwrap_or(0);
    let region_stack = program.stack_sizes.region_stack_size.unwrap_or(0);
    for (index, function) in program
        .functions
        .iter()
        .enumerate()
        .filter(|(_, function)| function.native)
    {
        let mut parameters = vec!["bool dedicated".to_owned()];
        let mut arguments = Vec::new();
        let mut initialize = String::new();
        let aggregate = matches!(function.result, Ty::Struct(_));
        if scalar_result(function.result) {
            arguments.push("&frame->result".to_owned());
        } else if program.placement.functions[index].caller_slots != 0 {
            arguments.push("frame->output".to_owned());
        }
        for (position, &(_, ty)) in function.parameters.iter().enumerate() {
            parameters.push(format!("{} capture{position}", c_type(ty)));
            let (address, deref) = if matches!(ty, Ty::Struct(_)) {
                ("&", "*")
            } else {
                ("", "")
            };
            arguments.push(format!("{address}frame->capture{position}"));
            writeln!(
                initialize,
                "    frame->capture{position} = {deref}capture{position};"
            )
            .unwrap();
        }
        let captures = function
            .parameters
            .iter()
            .enumerate()
            .filter_map(|(position, &(_, ty))| {
                let resource = result_resource(ty, program)?;
                let address = if matches!(ty, Ty::Struct(_)) { "&" } else { "" };
                let destination = format!("{address}frame->capture{position}");
                let source = if matches!(ty, Ty::Struct(_)) {
                    format!("capture{position}")
                } else {
                    destination.clone()
                };
                Some((resource, source, destination))
            })
            .collect::<Vec<_>>();
        let mut attach = String::new();
        for (resource, source, destination) in &captures {
            writeln!(
                initialize,
                "    {}",
                resource_call(*resource, source, "0", "CRUST_DETACH")
            )
            .unwrap();
            writeln!(
                attach,
                "    {}",
                resource_call(*resource, destination, "0", "CRUST_ATTACH")
            )
            .unwrap();
        }
        let capture_dispose = if captures.is_empty() {
            "NULL".to_owned()
        } else {
            let name = format!("crust_native_dispose_captures_{index}");
            writeln!(output, "static void {name}(CrustHandle *handle) {{ CrustThreadFrame{index} *frame = (void *)handle;").unwrap();
            for (resource, _, place) in captures.iter().rev() {
                writeln!(
                    output,
                    "    {}",
                    resource_call(*resource, place, "0", "CRUST_DESTROY")
                )
                .unwrap();
            }
            output.push_str("}\n");
            name
        };
        let result_cleanup = if let Some(resource) = result_resource(function.result, program) {
            let name = format!("crust_native_dispose_result_{index}");
            let place = if aggregate {
                "&frame->result"
            } else {
                "frame->result"
            };
            writeln!(output, "static void {name}(CrustHandle *handle) {{ CrustThreadFrame{index} *frame = (void *)handle;").unwrap();
            writeln!(
                output,
                "    {}\n}}",
                resource_call(resource, place, "0", "CRUST_DESTROY")
            )
            .unwrap();
            // A returned map is still registered at the address returned by the worker function.
            let source = if aggregate { "result" } else { place };
            format!(
                "    {}\n    handle->dispose = {name};\n",
                resource_call(resource, source, "0", "CRUST_DETACH")
            )
        } else {
            "    handle->dispose = NULL;\n".into()
        };
        let result_parameter = parameters.join(", ");
        let arguments = arguments.join(", ");
        let (result, save_result) = if aggregate {
            (
                format!("{} result = ", c_type(function.result)),
                "    frame->result = *result;\n",
            )
        } else {
            (String::new(), "")
        };
        let footprint = program.placement.worker_footprints.get(&index);
        writeln!(
            output,
            r#"
static void *crust_native_worker_{index}(void *argument) {{
    CrustThreadFrame{index} *frame = argument;
    CrustHandle *handle = &frame->handle;
"#
        )
        .unwrap();
        if fixed != 0 {
            writeln!(output, "    crust_set_capacity(UINT64_C({fixed}));").unwrap();
        } else if footprint.is_some() {
            writeln!(output, "    crust_set_capacity(crust_bound_{index}(0));").unwrap();
        }
        let limit = emit_region_bound(output, footprint, region_limit == 0);
        let slots = program.placement.functions[index].regions.slots;
        writeln!(output, r#"    crust_regions_configure(handle->region_stack_limit, handle->region_limit ? handle->region_limit : {limit}, {slots});
{attach}    {result}crust_fn_{index}({arguments});
{result_cleanup}{save_result}    crust_worker_close_regions();
    if (crust_stack != NULL)
        crust_guarded_unmap(crust_stack, crust_capacity);
    crust_thread_complete(handle);
    return NULL;
}}

static CrustHandle *crust_native_start_{index}({result_parameter}) {{
    CrustGrowing region = dedicated ? crust_region_take_dedicated() : crust_region_take();
    if (sizeof(CrustThreadFrame{index}) > region.band->limit)
        crust_region_error();
    CrustThreadFrame{index} *frame = (void *)crust_region_data(&region);
{initialize}    frame->handle.region = region;
    frame->handle.result = &frame->result;
    frame->handle.region_limit = crust_region_scope == NULL ? UINT64_C({region_limit}) : crust_region_scope->limit;
    frame->handle.region_stack_limit = crust_region_scope == NULL ? UINT64_C({region_stack}) : 0;
    return crust_thread_launch(&frame->handle, crust_native_worker_{index}, frame, {capture_dispose});
}}
"#).unwrap();
    }
}

// Any temporary or reservation that spans a poll lives in the Future.
// Keep the full set for now; no cross-suspension liveness optimization.
fn async_fields(
    placement: &FunctionPlacement,
    program: &VerifiedProgram,
) -> BTreeMap<String, String> {
    let layouts = &program.structures;
    let mut fields = BTreeMap::new();
    for (&temp, &(ty, read_only)) in &placement.frame_temps {
        fields.insert(format!("t{temp}"), evaluation_type(ty, read_only));
    }
    for value in &placement.frame_receivers {
        if owned_resource(value.ty, program).is_some() && !map_type(value.ty, layouts) {
            fields.insert(format!("resource_depth{}", value.temp), "size_t".into());
        }
        if matches!(value.ty, Ty::Struct(_)) {
            fields.insert(format!("t{}", value.temp), c_type(value.ty));
            if map_type(value.ty, layouts) {
                fields.insert(format!("map_depth{}", value.temp), "size_t".into());
            }
        } else if matches!(value.ty, Ty::Handle(..) | Ty::Future(_)) {
            fields.insert(format!("handle_depth{}", value.temp), "size_t".into());
        }
    }
    for slot in placement.before.values().flatten() {
        fields.insert(format!("s{}", slot.slot), c_type(slot.ty));
    }
    for reservation in placement.values_before.values().flatten() {
        let (prefix, value) = match reservation {
            ValueReservation::Receiver(value) => ("r", value),
            ValueReservation::CallResult(value) => ("o", value),
            ValueReservation::Binding(..) => continue,
        };
        if value.ty.scalar().is_some() && !placement.value_aliases.contains_key(&value.temp) {
            fields.insert(format!("scalar{}{}", prefix, value.temp), c_type(value.ty));
        }
        fields.insert(
            format!("{prefix}{}", value.temp),
            format!("{} *", c_type(value.ty)),
        );
    }
    for site in &placement.frame_scope_sites {
        fields.insert(format!("scope{site}"), "CrustAsyncMark".into());
    }
    fields
}

fn owned_resource(ty: Ty, program: &VerifiedProgram) -> Option<OwnedResource> {
    match ty {
        Ty::Allocation(_) => Some(OwnedResource::Slot),
        ty if map_type(ty, &program.structures) => Some(OwnedResource::Map),
        Ty::Struct(layout) if program.ownership[layout].is_some() => {
            Some(OwnedResource::Inline(layout))
        }
        _ => None,
    }
}

fn result_resource(ty: Ty, program: &VerifiedProgram) -> Option<OwnedResource> {
    if matches!(ty, Ty::Handle(..)) {
        Some(OwnedResource::Handle)
    } else {
        owned_resource(ty, program)
    }
}

fn resource_call(resource: OwnedResource, value: &str, owner: &str, action: &str) -> String {
    match resource {
        OwnedResource::Handle => format!("crust_pool_handle_resource({value}, {owner}, {action});"),
        OwnedResource::Map => {
            format!("crust_map_resource(&({value})->contents, {owner}, {action});")
        }
        OwnedResource::Slot => format!("crust_pool_resource({value}, {owner}, {action});"),
        OwnedResource::Inline(layout) => {
            format!("crust_resources_{layout}({value}, {owner}, {action});")
        }
    }
}

fn emit_resource_walkers(output: &mut String, program: &VerifiedProgram) {
    let ownership = &program.ownership;
    let walkers = || {
        ownership
            .iter()
            .enumerate()
            .filter_map(|(index, plan)| plan.as_ref().map(|plan| (index, plan)))
    };
    for (index, _) in walkers() {
        writeln!(output, "static inline __attribute__((unused)) void crust_resources_{index}(CrustStruct{index} *, uintptr_t, int);").unwrap();
    }
    for (layout, structure) in program.structures.iter().enumerate() {
        if let Some(function) = structure.destructor {
            writeln!(
                output,
                "static void crust_destruct_{layout}(void *value) {{ crust_fn_{function}(value); }}"
            )
            .unwrap();
        }
        if crate::verify::inline_destructor(Ty::Struct(layout), &program.structures) {
            writeln!(output, "static inline __attribute__((unused)) void crust_finalize_{layout}(void *value) {{ crust_resources_{layout}(value, 0, CRUST_FINALIZE); }}").unwrap();
        }
    }
    for (layout, structure) in program.structures.iter().enumerate() {
        if !structure.variants.is_empty()
            && crate::verify::inline_destructor(Ty::Struct(layout), &program.structures)
        {
            for tag in 0..structure.variants.len() {
                writeln!(output, "static inline __attribute__((unused)) void crust_finalize_{layout}_{tag}(void *payload) {{ CrustStruct{layout} value; value.tag = {tag}; value.data.v{tag} = *(CrustVariant{layout}_{tag} *)payload; crust_finalize_{layout}(&value); }}").unwrap();
            }
        }
    }
    for (index, plan) in walkers() {
        writeln!(output, "static inline __attribute__((unused)) void crust_resources_{index}(CrustStruct{index} *value, uintptr_t owner, int action) {{").unwrap();
        let destructor = |output: &mut String, condition: &str| {
            if program.structures[index].destructor.is_some() {
                writeln!(output, "    if ({condition}) crust_destructor_resource(&value->destructor, value, crust_destruct_{index}, action == CRUST_EXTRACT ? crust_pool_current_owner() : owner, action);").unwrap();
            }
        };
        let register =
            "action == CRUST_REHOME || action == CRUST_ATTACH || action == CRUST_EXTRACT";
        destructor(output, &format!("!({register})"));
        let field = |output: &mut String, resource, place: &str| {
            let argument = match resource {
                OwnedResource::Slot | OwnedResource::Handle => place.to_owned(),
                OwnedResource::Inline(_) | OwnedResource::Map => format!("&{place}"),
            };
            if !matches!(resource, OwnedResource::Inline(_)) {
                writeln!(
                    output,
                    "    if (action != CRUST_FINALIZE && action != CRUST_UNREGISTER) {}",
                    resource_call(resource, &argument, "owner", "action")
                )
                .unwrap();
            } else {
                writeln!(
                    output,
                    "    {}",
                    resource_call(resource, &argument, "owner", "action")
                )
                .unwrap();
            }
        };
        match plan {
            Ownership::Array { element, len } => {
                writeln!(output, "    for (size_t i = {len}; i != 0; --i) {{").unwrap();
                field(output, *element, "value->elements[i-1]");
                output.push_str("    }\n");
            }
            Ownership::Variants(variants) => {
                output.push_str("    switch (value->tag) {\n");
                for (tag, fields) in variants.iter().enumerate() {
                    writeln!(output, "    case {tag}:").unwrap();
                    for &(index, child) in fields {
                        field(output, child, &format!("value->data.v{tag}.f{index}"));
                    }
                    output.push_str("        break;\n");
                }
                output.push_str("    default: abort();\n    }\n");
            }
            Ownership::Fields(fields) => {
                for &(index, child) in fields {
                    field(output, child, &format!("value->f{index}"));
                }
            }
        }
        destructor(output, register);
        output.push_str("}\n");
    }
}

fn owned_action(
    output: &mut String,
    pad: &str,
    value: Value,
    action: &str,
    owner: Option<&str>,
    program: &VerifiedProgram,
) {
    let Some(resource) = owned_resource(value.ty, program) else {
        return;
    };
    let input = operand(value);
    let owner = owner.unwrap_or(if map_type(value.ty, &program.structures) {
        "crust_map_depth"
    } else {
        "crust_pool_current_owner()"
    });
    writeln!(
        output,
        "{pad}{}",
        resource_call(resource, &input, owner, action)
    )
    .unwrap();
}

fn detach_destructor_value(
    output: &mut String,
    pad: &str,
    value: Value,
    program: &VerifiedProgram,
) {
    if crate::verify::inline_destructor(value.ty, &program.structures) {
        owned_action(output, pad, value, "CRUST_UNREGISTER", Some("0"), program);
    }
}

fn adopt_owned(
    output: &mut String,
    pad: &str,
    parent: &str,
    value: Value,
    program: &VerifiedProgram,
) {
    adopt_owned_at(output, pad, parent, value.ty, &operand(value), program);
}

fn adopt_owned_at(
    output: &mut String,
    pad: &str,
    parent: &str,
    ty: Ty,
    place: &str,
    program: &VerifiedProgram,
) {
    let Some(resource) = result_resource(ty, program) else {
        return;
    };
    writeln!(output, "{pad}{{").unwrap();
    writeln!(
        output,
        "{pad}    CrustAllocation *previous = {parent}->children;"
    )
    .unwrap();
    writeln!(
        output,
        "{pad}    CrustAdoption adoption = {{ {parent}, &{parent}->children }};"
    )
    .unwrap();
    writeln!(
        output,
        "{pad}    {}",
        resource_call(resource, place, "(uintptr_t)&adoption", "CRUST_ADOPT")
    )
    .unwrap();
    writeln!(output, "{pad}    *adoption.tail = previous;").unwrap();
    writeln!(output, "{pad}}}").unwrap();
}

fn future_parameters(function: &Function) -> String {
    std::iter::once("bool dedicated".to_owned())
        .chain(
            function
                .parameters
                .iter()
                .map(|(binding, ty)| format!("{} capture{}", c_type(*ty), binding.0)),
        )
        .collect::<Vec<_>>()
        .join(", ")
}

fn emit_async_workers(output: &mut String, program: &VerifiedProgram) {
    for (index, function) in program.functions.iter().enumerate() {
        if function.asynchronous {
            writeln!(
                output,
                "static inline __attribute__((unused)) CrustHandle *crust_future_new_{index}({});",
                future_parameters(function)
            )
            .unwrap();
        }
    }
    for (index, function) in program
        .functions
        .iter()
        .enumerate()
        .filter(|(_, function)| function.asynchronous)
    {
        let placement = &program.placement.functions[index];
        let owned = |ty| result_resource(ty, program).is_some();
        let owned_captures = function
            .parameters
            .iter()
            .filter_map(|&(binding, ty)| {
                owned_resource(ty, program).map(|resource| (binding, resource))
            })
            .collect::<Vec<_>>();
        let handles = function
            .parameters
            .iter()
            .filter(|(_, ty)| matches!(ty, Ty::Handle(..)))
            .collect::<Vec<_>>();
        let captured_cleanup = !owned_captures.is_empty() || !handles.is_empty();
        if captured_cleanup {
            writeln!(output, "static void crust_dispose_captures_{index}(CrustHandle *handle) {{ CrustThreadFrame{index} *frame = (void *)handle;").unwrap();
            for &(binding, _) in handles.iter().rev().copied() {
                writeln!(
                    output,
                    "    if (frame->b{0} != NULL) crust_thread_detach(frame->b{0});",
                    binding.0
                )
                .unwrap();
            }
            for &(binding, resource) in owned_captures.iter().rev() {
                writeln!(
                    output,
                    "    {}",
                    resource_call(
                        resource,
                        &format!("frame->b{}", binding.0),
                        "0",
                        "CRUST_DESTROY"
                    )
                )
                .unwrap();
            }
            output.push_str("}\n");
        }
        if let Some(resource) = result_resource(function.result, program) {
            writeln!(output, "static void crust_dispose_result_{index}(CrustHandle *handle) {{ CrustThreadFrame{index} *frame = (void *)handle;").unwrap();
            let place = if matches!(function.result, Ty::Struct(_)) {
                "&frame->result"
            } else {
                "frame->result"
            };
            writeln!(
                output,
                "    {}\n}}",
                resource_call(resource, place, "0", "CRUST_DESTROY")
            )
            .unwrap();
        }
        let yields = &placement.suspension_sites;
        let fields = async_fields(placement, program);
        writeln!(
            output,
            "\nstatic bool crust_async_poll_{index}(CrustHandle *handle) {{"
        )
        .unwrap();
        writeln!(
            output,
            "    CrustThreadFrame{index} *frame = (void *)handle;"
        )
        .unwrap();
        output.push_str(
            r#"    crust_async_exchange(&frame->context);
    size_t crust_frame = 0;
    CrustRegionBand *crust_region_frame = NULL;
    size_t crust_region_frame_threads = 0;
#ifdef CRUST_HAS_POOLS
    size_t crust_region_frame_pools = 0;
#endif
#ifdef CRUST_HAS_MAPS
    size_t crust_region_frame_depth = 0;
#endif
"#,
        );
        for (&binding, &ty) in &program.placement.functions[index].frame_values {
            if matches!(ty, Ty::Struct(_)) {
                writeln!(
                    output,
                    "    {} b{binding} = frame->b{binding}; (void)b{binding};",
                    c_type(ty)
                )
                .unwrap();
            } else if placement.frame_binding_aliases.contains(&binding) {
                writeln!(
                    output,
                    "    {} *b{binding} = frame->b{binding}; (void)b{binding};",
                    c_type(ty)
                )
                .unwrap();
            } else {
                writeln!(
                    output,
                    "    {} *b{binding} = &frame->b{binding}; (void)b{binding};",
                    c_type(ty)
                )
                .unwrap();
            }
        }
        if captured_cleanup {
            output.push_str("    if (frame->pc == 0) {\n");
            for &(binding, _) in &handles {
                writeln!(
                    output,
                    "        if (frame->b{0} != NULL) crust_thread_register(frame->b{0});",
                    binding.0
                )
                .unwrap();
            }
            for &(binding, resource) in &owned_captures {
                writeln!(
                    output,
                    "        {}",
                    resource_call(
                        resource,
                        &format!("frame->b{}", binding.0),
                        "crust_thread_depth",
                        "CRUST_ATTACH"
                    )
                )
                .unwrap();
            }
            output.push_str("        handle->dispose = NULL;\n    }\n");
        }
        if owned(function.result) {
            writeln!(
                output,
                "#define CRUST_ASYNC_RESULT_DISPOSE crust_dispose_result_{index}"
            )
            .unwrap();
        }
        for name in fields.keys() {
            writeln!(output, "#define {name} (frame->{name})").unwrap();
        }
        if !yields.is_empty() {
            output.push_str("    switch (frame->pc) {\n    case 0: break;\n");
            for site in yields {
                writeln!(output, "    case {}: goto resume{site};", site + 1).unwrap();
            }
            output.push_str("    default: abort();\n    }\n");
        } else {
            output.push_str("    (void)frame;\n");
        }
        body(
            output,
            &function.body,
            1,
            false,
            &program.placement.functions[index],
            &mut 0,
            None,
            0,
            program,
            true,
        );
        output.push_str("}\n");
        if owned(function.result) {
            output.push_str("#undef CRUST_ASYNC_RESULT_DISPOSE\n");
        }
        for name in fields.keys() {
            writeln!(output, "#undef {name}").unwrap();
        }

        let parameters = future_parameters(function);
        writeln!(output, "static inline __attribute__((unused)) CrustHandle *crust_future_new_{index}({parameters}) {{").unwrap();
        writeln!(
            output,
            r#"    CrustGrowing region = dedicated ? crust_region_take_dedicated() : crust_region_take();
    if (sizeof(CrustThreadFrame{index}) > region.band->limit)
        crust_region_error();
    CrustThreadFrame{index} *frame = (void *)crust_region_data(&region);
    frame->handle.region = region;
    frame->handle.result = &frame->result;
    frame->handle.poll = crust_async_poll_{index};
    frame->handle.scheduled = false;
    frame->handle.waiter = NULL;
    frame->handle.waiting = false;
    frame->handle.parked = false;
    frame->handle.dispose = NULL;
    frame->pc = 0;
    frame->context = (CrustAsyncContext){{0}};"#
        )
        .unwrap();
        for (&binding, &ty) in &program.placement.functions[index].frame_values {
            if matches!(ty, Ty::Struct(_)) || placement.frame_binding_aliases.contains(&binding) {
                writeln!(output, "    frame->b{binding} = NULL;").unwrap();
            }
        }
        let footprint = program.placement.worker_footprints.get(&index);
        let global_limit = program.stack_sizes.region_size.unwrap_or(0);
        let global_stack = program.stack_sizes.region_stack_size.unwrap_or(0);
        let region_limit = emit_region_bound(output, footprint, global_limit == 0);
        let slots = placement.regions.slots;
        writeln!(output, "    uintmax_t limit = crust_region_scope == NULL ? (UINT64_C({global_limit}) ? UINT64_C({global_limit}) : {region_limit}) : crust_region_scope->limit;").unwrap();
        writeln!(
            output,
            "    uintmax_t stack = crust_region_scope == NULL ? UINT64_C({global_stack}) : 0;"
        )
        .unwrap();
        output.push_str("    frame->context.region_limit = 100 * 1024 * 1024;\n    crust_async_exchange(&frame->context);\n#ifdef CRUST_HAS_POOLS\n    crust_async_pool = true;\n#endif\n");
        if let Some(bytes) = program.stack_sizes.size {
            writeln!(output, "    crust_set_capacity(UINT64_C({bytes}));").unwrap();
        } else if footprint.is_some() {
            writeln!(output, "    crust_set_capacity(crust_bound_{index}(0));").unwrap();
        }
        writeln!(
            output,
            "    crust_regions_configure(stack, limit, {slots});"
        )
        .unwrap();
        output.push_str("    crust_thread_depth = 1;\n#ifdef CRUST_HAS_MAPS\n    crust_map_depth = 1;\n#endif\n    crust_async_exchange(&frame->context);\n");
        for (binding, ty) in &function.parameters {
            if matches!(ty, Ty::Struct(_)) {
                writeln!(
                    output,
                    "    frame->capture{0} = *capture{0}; frame->b{0} = &frame->capture{0};",
                    binding.0
                )
                .unwrap();
            } else {
                writeln!(output, "    frame->b{0} = capture{0};", binding.0).unwrap();
            }
        }
        if captured_cleanup {
            for &(binding, _) in &handles {
                writeln!(
                    output,
                    "    if (frame->b{0} != NULL) crust_thread_unlink(frame->b{0});",
                    binding.0
                )
                .unwrap();
            }
            for &(binding, resource) in &owned_captures {
                writeln!(
                    output,
                    "    {}",
                    resource_call(
                        resource,
                        &if !matches!(resource, OwnedResource::Slot) {
                            format!("capture{}", binding.0)
                        } else {
                            format!("frame->b{}", binding.0)
                        },
                        "0",
                        "CRUST_DETACH"
                    )
                )
                .unwrap();
            }
            writeln!(
                output,
                "    frame->handle.dispose = crust_dispose_captures_{index};"
            )
            .unwrap();
        }
        output.push_str("    return crust_thread_register(&frame->handle);\n}\n");
    }
}

fn has_region_scope(body: &[Instr]) -> bool {
    body.iter().any(|instruction| match instruction {
        Instr::RegionScope { .. } | Instr::FreePages => true,
        Instr::Block(nested) => has_region_scope(nested),
        Instr::If(_, yes, no) => has_region_scope(yes) || has_region_scope(no),
        Instr::Loop {
            condition, body, ..
        } => has_region_scope(condition) || has_region_scope(body),
        _ => false,
    })
}

fn emit_footprint(output: &mut String, footprint: &Footprint, emitted: &mut BTreeSet<usize>) {
    for &function in &footprint.order {
        if !emitted.insert(function) {
            continue;
        }
        writeln!(
            output,
            "\nstatic size_t crust_bound_{function}(size_t base) {{"
        )
        .unwrap();
        // All emitted storage types use fundamental C alignment. Cursor
        // behavior repeats at max_align_t boundaries, so memoize by residue.
        output.push_str(
            r#"    static CRUST_LOCAL size_t cache[_Alignof(max_align_t)];
    size_t residue = base % _Alignof(max_align_t);
    if (cache[residue] == 0) {
        size_t cursor = residue;
        size_t peak = cursor;
"#,
        );
        measure_steps(output, &footprint.steps[function], 2);
        output.push_str(
            r#"        cache[residue] = peak + 1;
    }
    return crust_advance(base - residue, 1, 1, cache[residue] - 1);
}
"#,
        );
    }
}

fn measure_steps(output: &mut String, steps: &[FootprintStep], depth: usize) {
    let pad = "    ".repeat(depth);
    for step in steps {
        match step {
            FootprintStep::Reserve(ty, count) => {
                let ty = stored_type(*ty);
                writeln!(
                    output,
                    "{pad}cursor = crust_advance(cursor, sizeof({ty}), _Alignof({ty}), {count});"
                )
                .unwrap();
                writeln!(output, "{pad}if (cursor > peak) peak = cursor;").unwrap();
            }
            FootprintStep::Call(callee) => {
                writeln!(output, "{pad}{{").unwrap();
                writeln!(
                    output,
                    "{pad}    size_t called = crust_bound_{callee}(cursor);"
                )
                .unwrap();
                writeln!(output, "{pad}    if (called > peak) peak = called;").unwrap();
                writeln!(output, "{pad}}}").unwrap();
            }
            FootprintStep::Scope(steps) | FootprintStep::Loop(steps) => {
                measure_scope(output, steps, depth);
            }
            FootprintStep::Branch(arms) => {
                for arm in arms {
                    measure_scope(output, arm, depth);
                }
            }
            FootprintStep::Grow(..) | FootprintStep::MapGrow(..) | FootprintStep::Thread(..) => {}
        }
    }
}

fn measure_scope(output: &mut String, steps: &[FootprintStep], depth: usize) {
    if steps.is_empty() {
        return;
    }
    let pad = "    ".repeat(depth);
    writeln!(output, "{pad}{{").unwrap();
    writeln!(output, "{pad}    size_t mark = cursor;").unwrap();
    measure_steps(output, steps, depth + 1);
    writeln!(output, "{pad}    cursor = mark;").unwrap();
    writeln!(output, "{pad}}}").unwrap();
}

fn map_type(ty: Ty, layouts: &[Structure]) -> bool {
    matches!(ty, Ty::Struct(index) if matches!(layouts[index].growing, Some(Growing::Map(..))))
}

fn stored_type(ty: Ty) -> String {
    match ty {
        Ty::Struct(index) => format!("CrustStruct{index}"),
        _ => c_type(ty),
    }
}

fn define_layout(output: &mut String, layouts: &[Structure], defined: &mut [bool], index: usize) {
    if defined[index] {
        return;
    }
    let layout = &layouts[index];
    for dependency in layout_dependencies(layout) {
        define_layout(output, layouts, defined, dependency);
    }
    defined[index] = true;
    if layout.pool.is_some_and(|(_, count)| count == 0) {
        return;
    }
    for (tag, (_, fields)) in layout.variants.iter().enumerate() {
        output.push_str("typedef struct {\n");
        define_fields(output, fields, "    ");
        writeln!(output, "}} CrustVariant{index}_{tag};").unwrap();
    }
    writeln!(output, "struct CrustStruct{index} {{").unwrap();
    if matches!(layout.growing, Some(Growing::Map(..))) {
        output.push_str("    CrustMap contents;\n");
    } else if layout.growing.is_some() {
        output.push_str("    CrustGrowing contents;\n");
    } else if let Some((element, length)) = layout.array {
        writeln!(
            output,
            "    {} elements[{}];",
            stored_type(element),
            length.max(1)
        )
        .unwrap();
    } else if let Some((element, capacity)) = layout.pool {
        let variants = match element {
            Ty::Struct(index) => &layouts[index].variants[..],
            _ => &[],
        };
        let arms = variants.len().max(1);
        writeln!(output, "    CrustPool header;").unwrap();
        writeln!(output, "    CrustPoolArm arms[{arms}];").unwrap();
        writeln!(output, "    CrustAllocation records[{arms}][{capacity}];").unwrap();
        if variants.is_empty() {
            writeln!(output, "    {} slots_0[{capacity}];", stored_type(element)).unwrap();
        } else {
            let Ty::Struct(element) = element else {
                unreachable!()
            };
            for tag in 0..variants.len() {
                writeln!(
                    output,
                    "    CrustVariant{element}_{tag} slots_{tag}[{capacity}];"
                )
                .unwrap();
            }
        }
    } else if !layout.variants.is_empty() {
        output.push_str("    size_t tag;\n    union {\n");
        for tag in 0..layout.variants.len() {
            writeln!(output, "        CrustVariant{index}_{tag} v{tag};").unwrap();
        }
        output.push_str("    } data;\n");
    } else {
        define_fields(output, &layout.fields, "    ");
    }
    if layout.destructor.is_some() {
        output.push_str("    CrustDestructor destructor;\n");
    }
    writeln!(output, "}};").unwrap();
}

fn define_fields(output: &mut String, fields: &[(String, Ty)], pad: &str) {
    if fields.is_empty() {
        writeln!(output, "{pad}unsigned char empty;").unwrap();
    }
    for (field, (_, ty)) in fields.iter().enumerate() {
        writeln!(output, "{pad}{} f{field};", stored_type(*ty)).unwrap();
    }
}

fn c_type(ty: Ty) -> String {
    match ty {
        Ty::Struct(id) => return format!("CrustStruct{id} *"),
        Ty::Void => "void",
        Ty::Bool => "bool",
        Ty::I32 => "int32_t",
        Ty::I64 => "int64_t",
        Ty::U8 => "uint8_t",
        Ty::U16 => "uint16_t",
        Ty::U32 => "uint32_t",
        Ty::U64 => "uint64_t",
        Ty::Usize => "uintptr_t",
        Ty::Slice { .. } | Ty::Str => "CrustSlice",
        Ty::F32 => "float",
        Ty::F64 => "double",
        Ty::Allocation(_) => "CrustAllocation *",
        Ty::Pool(_) => "CrustPool",
        Ty::Handle(..) | Ty::Future(_) => "CrustHandle *",
        Ty::Ref {
            target: Referent::Pool(_),
            mutable,
        } => {
            return if mutable {
                "CrustPool *"
            } else {
                "const CrustPool *"
            }
            .to_owned();
        }
        Ty::Ref { target, mutable } => {
            let qualifier = if mutable { "" } else { " const" };
            return format!("{}{qualifier} *", stored_type(target.ty()));
        }
    }
    .to_owned()
}

fn emit_assembly_functions(
    output: &mut String,
    instructions: &[Instr],
    emitted: &mut BTreeSet<usize>,
) {
    for instruction in instructions {
        match instruction {
            Instr::Assembly(block) if emitted.insert(block.offset) => {
                let name = format!("crust_asm_{}", block.offset);
                let code = block.abi.routine(&name, &block.code);
                writeln!(output, "extern void {name}(uint64_t *);").unwrap();
                output.push_str("__asm__(\n");
                for line in code.split_inclusive('\n') {
                    output.push_str("    \"");
                    for byte in line.bytes() {
                        match byte {
                            b'\n' => output.push_str("\\n"),
                            b'\\' => output.push_str("\\\\"),
                            b'"' => output.push_str("\\\""),
                            b' '..=b'~' => output.push(char::from(byte)),
                            _ => write!(output, "\\{byte:03o}").unwrap(),
                        }
                    }
                    output.push_str("\"\n");
                }
                output.push_str(");\n");
            }
            Instr::Block(nested) => emit_assembly_functions(output, nested, emitted),
            Instr::If(_, yes, no) => {
                emit_assembly_functions(output, yes, emitted);
                emit_assembly_functions(output, no, emitted);
            }
            Instr::Loop {
                condition, body, ..
            } => {
                emit_assembly_functions(output, condition, emitted);
                emit_assembly_functions(output, body, emitted);
            }
            _ => {}
        }
    }
}

fn scalar_result(ty: Ty) -> bool {
    !matches!(ty, Ty::Void | Ty::Struct(_))
}

fn signature(
    function: &Function,
    index: usize,
    placement: &FunctionPlacement,
    process_args: bool,
) -> String {
    if function.entry {
        return if process_args {
            "int main(int argc, char **argv)"
        } else {
            "int main(void)"
        }
        .to_owned();
    }
    let mut parameters = function
        .parameters
        .iter()
        .map(|(binding, ty)| {
            if function.borrowed_parameters.contains(binding) {
                return format!("{} *b{}", stored_type(*ty), binding.0);
            }
            let prefix = if matches!(ty, Ty::Struct(_)) {
                'b'
            } else {
                'p'
            };
            format!("{} {prefix}{}", c_type(*ty), binding.0)
        })
        .collect::<Vec<_>>();
    if placement.caller_slots > 0 {
        parameters.insert(0, format!("{} crust_out", c_type(function.result)));
    }
    if scalar_result(function.result) {
        parameters.insert(0, format!("{} *crust_out", c_type(function.result)));
    }
    let parameters = parameters.join(", ");
    let parameters = if parameters.is_empty() {
        "void"
    } else {
        &parameters
    };
    let result = if scalar_result(function.result) {
        Ty::Void
    } else {
        function.result
    };
    format!("{} crust_fn_{index}({parameters})", c_type(result))
}

fn operand(value: Value) -> String {
    if value.receiver && scalar_result(value.ty) {
        format!("(*r{})", value.temp)
    } else {
        format!("t{}", value.temp)
    }
}

fn stored_operand(value: Value) -> String {
    let expression = operand(value);
    if matches!(value.ty, Ty::Struct(_)) {
        format!("*{expression}")
    } else {
        expression
    }
}

fn arguments(values: &[Value]) -> String {
    values
        .iter()
        .map(|&value| operand(value))
        .collect::<Vec<_>>()
        .join(", ")
}

fn body(
    output: &mut String,
    instructions: &[Instr],
    depth: usize,
    entry: bool,
    placement: &FunctionPlacement,
    cursor: &mut usize,
    loop_mark: Option<(usize, usize)>,
    enclosing_free_pages: usize,
    program: &VerifiedProgram,
    async_body: bool,
) {
    let layouts = &program.structures;
    let pad = "    ".repeat(depth);
    let free_pages = |body: &[Instr]| {
        body.iter()
            .any(|instruction| matches!(instruction, Instr::FreePages))
    };
    let forced_scopes = enclosing_free_pages + usize::from(free_pages(instructions));
    let fixed_threshold = program.stack_sizes.reclaim_threshold.unwrap_or(0);
    let regional_threshold = program.stack_sizes.region_reclaim_threshold.unwrap_or(0);
    let reclaim = |force| {
        format!(
            "UINT64_C({fixed_threshold}), UINT64_C({regional_threshold}), {}",
            u8::from(force)
        )
    };
    let return_reclaim = reclaim(forced_scopes != 0);
    for instruction in instructions {
        let index = *cursor;
        *cursor += 1;
        let enter = if async_body {
            format!("scope{index} = crust_async_mark();")
        } else {
            format!("size_t m{index} = crust_cursor; CRUST_REGION_MARK(rmark{index});")
        };
        let rewind = |site, force| {
            let reclaim = reclaim(force);
            if async_body {
                format!("crust_async_rewind(scope{site}, {reclaim});")
            } else {
                format!("crust_scope_rewind(m{site}, rmark{site}, {reclaim});")
            }
        };

        for reservation in placement.before.get(&index).into_iter().flatten() {
            let Ty::Struct(ty) = reservation.ty else {
                unreachable!()
            };
            let declaration = if async_body {
                String::new()
            } else {
                format!("CrustStruct{ty} *")
            };
            writeln!(
                output,
                "{pad}{declaration}s{} = crust_reserve(CrustStruct{ty}, {});",
                reservation.slot, reservation.width
            )
            .unwrap();
        }
        for reservation in placement.values_before.get(&index).into_iter().flatten() {
            let (name, ty, alias) = match reservation {
                ValueReservation::Binding(binding, ty, Some(storage)) => {
                    let location = match storage {
                        BindingStorage::Caller if async_body => "&frame->result".to_owned(),
                        BindingStorage::Caller => "crust_out".to_owned(),
                        BindingStorage::Binding(source) => format!("b{}", source.0),
                        BindingStorage::Receiver(temp) => format!("r{temp}"),
                        BindingStorage::CallResult(temp) => format!("o{temp}"),
                    };
                    if async_body {
                        writeln!(output, "{pad}frame->b{0} = b{0} = {location};", binding.0)
                            .unwrap();
                    } else {
                        writeln!(output, "{pad}{} *b{} = {location};", c_type(*ty), binding.0)
                            .unwrap();
                    }
                    continue;
                }
                ValueReservation::Binding(binding, ty, None) => {
                    (format!("b{}", binding.0), *ty, None)
                }
                ValueReservation::Receiver(value) => (
                    format!("r{}", value.temp),
                    value.ty,
                    placement.value_aliases.get(&value.temp),
                ),
                ValueReservation::CallResult(value) => (
                    format!("o{}", value.temp),
                    value.ty,
                    placement.value_aliases.get(&value.temp),
                ),
            };
            let frame_scalar = async_body && ty.scalar().is_some();
            let ty = c_type(ty);
            let location = match alias {
                Some(ValueDestination::Caller) if async_body => "&frame->result".to_owned(),
                Some(ValueDestination::Caller) => "crust_out".to_owned(),
                Some(ValueDestination::Receiver(temp)) => format!("r{temp}"),
                None if frame_scalar => format!("&scalar{name}"),
                None => format!("crust_reserve({ty}, 1)"),
            };
            let declaration = if async_body {
                String::new()
            } else {
                format!("{ty} *")
            };
            writeln!(output, "{pad}{declaration}{name} = {location};").unwrap();
        }
        if let Instr::Reserve(value) = instruction
            && owned_resource(value.ty, program).is_some()
            && !map_type(value.ty, layouts)
        {
            writeln!(
                output,
                "{pad}{}resource_depth{} = crust_pool_current_owner();",
                if async_body { "" } else { "size_t " },
                value.temp
            )
            .unwrap();
        }
        match instruction {
            Instr::Evaluate(
                value,
                expression @ (Expr::SocketWait(socket, argument)
                | Expr::SocketCompletion(socket, argument)),
            ) => {
                let park = match expression {
                    Expr::SocketWait(..) => "crust_socket_park",
                    _ => "crust_iocp_park",
                };
                writeln!(
                    output,
                    "{pad}t{} = {park}({}, {});",
                    value.temp,
                    operand(*socket),
                    operand(*argument)
                )
                .unwrap();
                writeln!(output, "{pad}if (t{} == 0) {{", value.temp).unwrap();
                writeln!(output, "{pad}    frame->pc = {};", index + 1).unwrap();
                writeln!(
                    output,
                    "{pad}    crust_async_exchange(&frame->context); return false;\n{pad}}}"
                )
                .unwrap();
                writeln!(output, "resume{index}: ;").unwrap();
            }
            Instr::Evaluate(value, Expr::AwaitHandle(handle)) => {
                let target = format!("t{}", value.temp);
                let destination = aggregate_destination(placement, *value).unwrap();
                writeln!(output, "{pad}{target} = {destination};").unwrap();
                writeln!(output, "resume{index}: ;").unwrap();
                let Ty::Struct(layout) = value.ty else {
                    unreachable!()
                };
                let args = completion_arguments(&target, &layouts[layout]);
                writeln!(
                    output,
                    "{pad}int completion{index} = crust_async_handle_take({}, {args});",
                    operand(*handle)
                )
                .unwrap();
                writeln!(output, "{pad}if (completion{index} < 0) {{").unwrap();
                writeln!(output, "{pad}    frame->pc = {};", index + 1).unwrap();
                writeln!(
                    output,
                    "{pad}    crust_async_exchange(&frame->context); return false;"
                )
                .unwrap();
                writeln!(output, "{pad}}}").unwrap();
                writeln!(output, "{pad}{target}->tag = (size_t)completion{index};").unwrap();
                emit_launch_failed(output, &pad, &target);
                owned_action(output, &pad, *value, "CRUST_ATTACH", None, program);
            }
            Instr::Evaluate(value, Expr::Await(future)) => {
                let child = operand(*future);
                writeln!(output, "resume{index}: ;").unwrap();
                writeln!(output, "{pad}if (!{child}->poll({child})) {{").unwrap();
                writeln!(output, "{pad}    frame->pc = {};", index + 1).unwrap();
                writeln!(
                    output,
                    "{pad}    crust_async_exchange(&frame->context); return false;"
                )
                .unwrap();
                writeln!(output, "{pad}}}").unwrap();
                let result = match value.ty {
                    Ty::Void => "NULL, 0".to_owned(),
                    Ty::Struct(_) => {
                        let target = aggregate_destination(placement, *value).unwrap();
                        writeln!(output, "{pad}t{} = {target};", value.temp).unwrap();
                        format!("t{0}, sizeof(*t{0})", value.temp)
                    }
                    ty if ty.scalar().is_some() => format!("o{0}, sizeof(*o{0})", value.temp),
                    _ => format!("&t{0}, sizeof(t{0})", value.temp),
                };
                writeln!(output, "{pad}crust_future_take({child}, {result});").unwrap();
                if value.ty.scalar().is_some() {
                    writeln!(output, "{pad}t{0} = *o{0};", value.temp).unwrap();
                }
                if matches!(value.ty, Ty::Handle(..)) {
                    writeln!(
                        output,
                        "{pad}crust_handle_resource(t{}, crust_thread_depth, CRUST_ATTACH);",
                        value.temp
                    )
                    .unwrap();
                } else {
                    owned_action(output, &pad, *value, "CRUST_ATTACH", None, program);
                }
            }
            Instr::Evaluate(value, expression) => evaluate(
                output, &pad, *value, expression, placement, program, async_body,
            ),
            Instr::Bind(binding, value) => {
                let id = binding.0;
                let value_text = operand(*value);
                if matches!(value.ty, Ty::Struct(_)) && async_body {
                    writeln!(output, "{pad}frame->b{id} = b{id} = {value_text};").unwrap();
                    owned_action(output, &pad, *value, "CRUST_REHOME", None, program);
                } else if matches!(value.ty, Ty::Struct(_)) {
                    writeln!(output, "{pad}{} b{id} = {value_text};", c_type(value.ty)).unwrap();
                    owned_action(output, &pad, *value, "CRUST_REHOME", None, program);
                } else {
                    writeln!(output, "{pad}*b{id} = {value_text};").unwrap();
                    if matches!(owned_resource(value.ty, program), Some(OwnedResource::Slot)) {
                        writeln!(output, "{pad}crust_pool_resource(*b{id}, crust_pool_current_owner(), CRUST_REHOME);").unwrap();
                    } else if matches!(value.ty, Ty::Handle(..) | Ty::Future(_)) {
                        writeln!(output, "{pad}crust_thread_own(*b{id}, crust_thread_depth);")
                            .unwrap();
                    }
                }
                if map_type(value.ty, layouts) {
                    writeln!(output, "{pad}b{id}->contents.owner = crust_map_depth;").unwrap();
                }
                writeln!(output, "{pad}(void)sizeof(b{});", binding.0).unwrap();
            }
            Instr::Write(binding, value) => {
                writeln!(output, "{pad}*b{} = {};", binding.0, operand(*value)).unwrap()
            }
            Instr::FreePages => {}
            Instr::RegionScope { max_size, count } => {
                writeln!(
                    output,
                    "{pad}crust_region_enter(UINT64_C({max_size}), UINT64_C({count}), {});",
                    placement
                        .regions
                        .scope_slots
                        .get(&index)
                        .copied()
                        .unwrap_or(0)
                )
                .unwrap();
            }
            Instr::GrowingPush(handle, value) => {
                let ty = stored_type(value.ty);
                let source = if matches!(value.ty, Ty::Struct(_)) {
                    operand(*value)
                } else {
                    format!("&({ty}){{ {} }}", operand(*value))
                };
                let owner = operand(*handle);
                let descriptor = if matches!(handle.ty, Ty::Ref { .. }) {
                    format!("&{owner}->contents")
                } else {
                    format!("(CrustGrowing *){owner}->data")
                };
                writeln!(
                    output,
                    "{pad}crust_region_append({descriptor}, {source}, sizeof({ty}));"
                )
                .unwrap();
                if matches!(handle.ty, Ty::Allocation(_)) {
                    adopt_owned(output, &pad, &owner, *value, program);
                }
            }
            Instr::GrowingText(handle, bytes) => {
                if bytes.is_empty() {
                    writeln!(output, "{pad}(void){};", operand(*handle)).unwrap();
                } else {
                    let literal = bytes
                        .iter()
                        .map(|byte| format!("\\x{byte:02x}"))
                        .collect::<String>();
                    writeln!(
                        output,
                        "{pad}crust_region_append((CrustGrowing *){}->data, \"{literal}\", {});",
                        operand(*handle),
                        bytes.len()
                    )
                    .unwrap();
                }
            }
            Instr::CheckIndex(index, length) => {
                let index_text = operand(*index);
                let negative = if index.ty.signed() {
                    format!("{index_text} < 0 || ")
                } else {
                    String::new()
                };
                if *length == 0 {
                    writeln!(output, "{pad}if ((void){index_text}, true) {{ fputs(\"corbo: indice hors du tableau\\n\", stderr); exit(EXIT_FAILURE); }}").unwrap();
                } else {
                    writeln!(output, "{pad}if ({negative}(uint64_t){index_text} >= UINT64_C({length})) {{ fputs(\"corbo: indice hors du tableau\\n\", stderr); exit(EXIT_FAILURE); }}").unwrap();
                }
            }
            Instr::WriteIndex(owner, index, value) => writeln!(
                output,
                "{pad}{}->elements[(size_t){}] = {};",
                operand(*owner),
                operand(*index),
                stored_operand(*value)
            )
            .unwrap(),
            Instr::WriteSliceElement(address, value) => writeln!(
                output,
                "{pad}*({} *)(uintptr_t){} = {};",
                stored_type(value.ty),
                operand(*address),
                stored_operand(*value)
            )
            .unwrap(),
            Instr::WriteNested(binding, value) => {
                writeln!(output, "{pad}***b{} = {};", binding.0, operand(*value)).unwrap();
            }
            Instr::WriteThrough(binding, value) => {
                writeln!(output, "{pad}**b{} = {};", binding.0, operand(*value)).unwrap()
            }
            Instr::Assembly(block) => {
                let len = block.operands.len().max(1);
                writeln!(output, "{pad}{{").unwrap();
                writeln!(output, "{pad}    uint64_t crust_operands[{len}] = {{0}};").unwrap();
                for (slot, op) in block.operands.iter().enumerate() {
                    let id = op.binding.0;
                    // Copy the object representation so narrow/signed slots
                    // preserve their low bytes without integer conversions.
                    writeln!(
                        output,
                        "{pad}    memcpy(&crust_operands[{slot}], b{id}, sizeof(*b{id}));"
                    )
                    .unwrap();
                }
                writeln!(
                    output,
                    "{pad}    crust_asm_{}(crust_operands);",
                    block.offset
                )
                .unwrap();
                for (slot, op) in block
                    .operands
                    .iter()
                    .enumerate()
                    .filter(|(_, op)| op.written)
                {
                    let id = op.binding.0;
                    writeln!(
                        output,
                        "{pad}    memcpy(b{id}, &crust_operands[{slot}], sizeof(*b{id}));"
                    )
                    .unwrap();
                }
                writeln!(output, "{pad}}}").unwrap();
            }
            Instr::Block(nested) => {
                let exit = rewind(index, free_pages(nested));
                writeln!(output, "{pad}{{").unwrap();
                writeln!(output, "{pad}    {enter}").unwrap();
                body(
                    output,
                    nested,
                    depth + 1,
                    entry,
                    placement,
                    cursor,
                    loop_mark,
                    forced_scopes,
                    program,
                    async_body,
                );
                writeln!(output, "{pad}    {exit}").unwrap();
                writeln!(output, "{pad}}}").unwrap();
            }
            Instr::If(condition, yes, no) => {
                let exit = rewind(index, free_pages(yes));
                writeln!(output, "{pad}if ({}) {{", operand(*condition)).unwrap();
                writeln!(output, "{pad}    {enter}").unwrap();
                body(
                    output,
                    yes,
                    depth + 1,
                    entry,
                    placement,
                    cursor,
                    loop_mark,
                    forced_scopes,
                    program,
                    async_body,
                );
                writeln!(output, "{pad}    {exit}").unwrap();
                if no.is_empty() {
                    writeln!(output, "{pad}}}").unwrap();
                } else {
                    let exit = rewind(index, free_pages(no));
                    writeln!(output, "{pad}}} else {{").unwrap();
                    writeln!(output, "{pad}    {enter}").unwrap();
                    body(
                        output,
                        no,
                        depth + 1,
                        entry,
                        placement,
                        cursor,
                        loop_mark,
                        forced_scopes,
                        program,
                        async_body,
                    );
                    writeln!(output, "{pad}    {exit}").unwrap();
                    writeln!(output, "{pad}}}").unwrap();
                }
            }
            Instr::Loop {
                condition,
                test,
                body: nested,
            } => {
                let exit = rewind(index, free_pages(nested));
                writeln!(output, "{pad}for (;;) {{").unwrap();
                writeln!(output, "{pad}    {enter}").unwrap();
                body(
                    output,
                    condition,
                    depth + 1,
                    entry,
                    placement,
                    cursor,
                    Some((index, forced_scopes)),
                    forced_scopes,
                    program,
                    async_body,
                );
                if let Some(test) = test {
                    writeln!(
                        output,
                        "{pad}    if (!{}) {{ {exit} break; }}",
                        operand(*test)
                    )
                    .unwrap();
                }
                body(
                    output,
                    nested,
                    depth + 1,
                    entry,
                    placement,
                    cursor,
                    Some((index, forced_scopes)),
                    forced_scopes,
                    program,
                    async_body,
                );
                writeln!(output, "{pad}    {exit}").unwrap();
                writeln!(output, "{pad}}}").unwrap();
            }
            Instr::Reserve(value) if matches!(value.ty, Ty::Struct(_)) => {
                if !async_body {
                    writeln!(output, "{pad}{} t{};", c_type(value.ty), value.temp).unwrap();
                }
                if map_type(value.ty, layouts) {
                    writeln!(
                        output,
                        "{pad}{}map_depth{} = crust_map_depth;",
                        if async_body { "" } else { "size_t " },
                        value.temp
                    )
                    .unwrap();
                }
            }
            Instr::Reserve(value) if matches!(value.ty, Ty::Handle(..) | Ty::Future(_)) => {
                writeln!(
                    output,
                    "{pad}{}handle_depth{} = crust_thread_depth;",
                    if async_body { "" } else { "size_t " },
                    value.temp
                )
                .unwrap();
            }
            Instr::Reserve(_) => {}
            Instr::Receive(receiver, value) => receive(output, &pad, *receiver, *value, program),
            Instr::Break(assignment) => {
                if let Some((receiver, value)) = assignment {
                    receive(output, &pad, *receiver, *value, program);
                }
                writeln!(
                    output,
                    "{pad}{} break;",
                    rewind(loop_mark.unwrap().0, forced_scopes > loop_mark.unwrap().1)
                )
                .unwrap();
            }
            Instr::Continue => {
                writeln!(
                    output,
                    "{pad}{} continue;",
                    rewind(loop_mark.unwrap().0, forced_scopes > loop_mark.unwrap().1)
                )
                .unwrap();
            }
            Instr::Yield => {
                writeln!(output, "{pad}frame->pc = {};", index + 1).unwrap();
                writeln!(output, "{pad}crust_async_exchange(&frame->context);").unwrap();
                writeln!(output, "{pad}return false;\nresume{index}: ;").unwrap();
            }
            Instr::Print(value) => match value.ty {
                Ty::Bool => writeln!(
                    output,
                    "{pad}puts({} ? \"true\" : \"false\");",
                    operand(*value)
                )
                .unwrap(),
                ty if ty.unsigned() => writeln!(
                    output,
                    "{pad}printf(\"%\" PRIu64 \"\\n\", (uint64_t){});",
                    operand(*value)
                )
                .unwrap(),
                ty if ty.float() => writeln!(
                    output,
                    "{pad}printf(\"%.17g\\n\", (double){});",
                    operand(*value)
                )
                .unwrap(),
                Ty::I32 | Ty::I64 => writeln!(
                    output,
                    "{pad}printf(\"%\" PRId64 \"\\n\", (int64_t){});",
                    operand(*value)
                )
                .unwrap(),
                _ => unreachable!(),
            },
            Instr::Call(index, values) => {
                writeln!(output, "{pad}crust_fn_{index}({});", arguments(values)).unwrap()
            }
            Instr::DropMap(value) => {
                writeln!(
                    output,
                    "{pad}crust_map_drop(&{}->contents);",
                    operand(*value)
                )
                .unwrap();
            }
            Instr::DropHandle(value) => {
                writeln!(output, "{pad}crust_thread_drop({});", operand(*value)).unwrap();
            }
            Instr::DropOwned(value) => {
                owned_action(output, &pad, *value, "CRUST_DROP", Some("0"), program);
            }
            Instr::DropAllocation(value) => {
                writeln!(output, "{pad}crust_pool_drop({});", operand(*value)).unwrap()
            }
            Instr::Discard(value) => writeln!(output, "{pad}(void){};", operand(*value)).unwrap(),
            Instr::Return(result) => {
                if async_body {
                    if let Some(value) = result {
                        if let Some(resource) = result_resource(value.ty, program) {
                            writeln!(
                                output,
                                "{pad}{}",
                                resource_call(resource, &operand(*value), "0", "CRUST_DETACH")
                            )
                            .unwrap();
                            writeln!(output, "{pad}handle->dispose = CRUST_ASYNC_RESULT_DISPOSE;")
                                .unwrap();
                        }
                        writeln!(output, "{pad}frame->result = {};", stored_operand(*value))
                            .unwrap();
                    }
                    writeln!(
                        output,
                        "{pad}crust_scope_rewind(crust_frame, crust_region_frame, {return_reclaim});"
                    )
                    .unwrap();
                    writeln!(output, "{pad}crust_async_close_context();").unwrap();
                    writeln!(output, "{pad}crust_async_exchange(&frame->context);").unwrap();
                    writeln!(output, "{pad}return true;").unwrap();
                    continue;
                }
                if let Some(value) = result.filter(|value| !entry && scalar_result(value.ty)) {
                    writeln!(output, "{pad}*crust_out = {};", operand(value)).unwrap();
                    if matches!(owned_resource(value.ty, program), Some(OwnedResource::Slot)) {
                        writeln!(output, "{pad}crust_pool_resource(*crust_out, crust_region_frame_pools, CRUST_REHOME);").unwrap();
                    } else if matches!(value.ty, Ty::Handle(..) | Ty::Future(_)) {
                        writeln!(
                            output,
                            "{pad}crust_thread_own(*crust_out, crust_region_frame_threads);"
                        )
                        .unwrap();
                    }
                }
                if let Some(value) = result.filter(|value| {
                    matches!(value.ty, Ty::Struct(_)) && !map_type(value.ty, layouts)
                }) {
                    owned_action(
                        output,
                        &pad,
                        value,
                        "CRUST_REHOME",
                        Some("crust_region_frame_pools"),
                        program,
                    );
                }
                if let Some(value) = result.filter(|value| map_type(value.ty, layouts)) {
                    writeln!(
                        output,
                        "{pad}{}->contents.owner = crust_region_frame_depth;",
                        operand(value)
                    )
                    .unwrap();
                }
                if let Some(value) = result.filter(|_| entry) {
                    writeln!(output, "{pad}int crust_status = {};", operand(value)).unwrap();
                }
                writeln!(
                    output,
                    "{pad}crust_scope_rewind(crust_frame, crust_region_frame, {return_reclaim});"
                )
                .unwrap();
                if entry {
                    output.push_str(&format!("{pad}CRUST_DRAIN_THREADS();\n"));
                }
                match result {
                    Some(_) if entry => writeln!(output, "{pad}return crust_status;").unwrap(),
                    Some(value) if !scalar_result(value.ty) => {
                        writeln!(output, "{pad}return {};", operand(*value)).unwrap()
                    }
                    None if entry => writeln!(output, "{pad}return 0;").unwrap(),
                    _ => writeln!(output, "{pad}return;").unwrap(),
                }
            }
        }
    }
}

fn receive(
    output: &mut String,
    pad: &str,
    receiver: Value,
    value: Value,
    program: &VerifiedProgram,
) {
    let layouts = &program.structures;
    let destination = if matches!(receiver.ty, Ty::Struct(_)) {
        "t"
    } else {
        "*r"
    };
    writeln!(
        output,
        "{pad}{destination}{} = {};",
        receiver.temp,
        operand(value)
    )
    .unwrap();
    if owned_resource(receiver.ty, program).is_some() && !map_type(receiver.ty, layouts) {
        owned_action(
            output,
            pad,
            receiver,
            "CRUST_REHOME",
            Some(&format!("resource_depth{}", receiver.temp)),
            program,
        );
    }
    if matches!(receiver.ty, Ty::Handle(..) | Ty::Future(_)) {
        writeln!(
            output,
            "{pad}crust_thread_own(*r{0}, handle_depth{0});",
            receiver.temp
        )
        .unwrap();
    }
    if map_type(receiver.ty, layouts) {
        writeln!(
            output,
            "{pad}t{0}->contents.owner = map_depth{0};",
            receiver.temp
        )
        .unwrap();
    }
}

fn completion_arguments(target: &str, layout: &Structure) -> String {
    if layout.variants[1].1.is_empty() {
        "NULL, 0".to_owned()
    } else {
        format!("&{target}->data.v1.f0, sizeof({target}->data.v1.f0)")
    }
}

fn emit_launch_failed(output: &mut String, pad: &str, target: &str) {
    writeln!(output, "{pad}if ({target}->tag == 0) {{ {target}->data.v0.f0.tag = 0; {target}->data.v0.f0.data.v0.empty = 0; }}").unwrap();
}

fn evaluation_type(ty: Ty, read_only: bool) -> String {
    if matches!(ty, Ty::Struct(_)) && read_only {
        format!("const {}", c_type(ty))
    } else {
        c_type(ty)
    }
}

fn aggregate_destination(placement: &FunctionPlacement, value: Value) -> Option<String> {
    placement
        .construction_destination(value)
        .map(|destination| match destination {
            Destination::FrameResult => "&frame->result".to_owned(),
            Destination::Caller(0) => "crust_out".to_owned(),
            Destination::Caller(offset) => format!("crust_out + {offset}"),
            Destination::Slot { slot, .. } => format!("s{slot}"),
        })
}

fn evaluate(
    output: &mut String,
    pad: &str,
    value: Value,
    expression: &Expr,
    placement: &FunctionPlacement,
    program: &VerifiedProgram,
    async_body: bool,
) {
    if placement.pool_initializers.contains_key(&value.temp) {
        return;
    }
    let layouts = &program.structures;
    let ty = evaluation_type(value.ty, expression.reads_aggregate_place());
    let declaration = if async_body {
        String::new()
    } else {
        format!("{ty} ")
    };
    let target = format!("t{}", value.temp);
    let destination = aggregate_destination(placement, value);
    let dedicated = placement.regions.dedicated.contains(&value.temp);
    let captures_with_region = |captures: &[Value]| {
        std::iter::once(dedicated.to_string())
            .chain(captures.iter().map(|&capture| operand(capture)))
            .collect::<Vec<_>>()
            .join(", ")
    };
    let initial = match expression {
        Expr::Await(_)
        | Expr::AwaitHandle(_)
        | Expr::SocketWait(..)
        | Expr::SocketCompletion(..) => unreachable!(),
        Expr::SocketAttach(socket) => format!("crust_iocp_attach({})", operand(*socket)),
        Expr::Construct(fields) | Expr::Variant(_, fields) => {
            let destination = destination.expect("construction sans réservation");
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            let prefix = if let Expr::Variant(tag, _) = expression {
                writeln!(output, "{pad}{target}->tag = {tag};").unwrap();
                if fields.is_empty() {
                    writeln!(output, "{pad}{target}->data.v{tag}.empty = 0;").unwrap();
                }
                format!("{target}->data.v{tag}.")
            } else {
                format!("{target}->")
            };
            for (field, value) in fields {
                detach_destructor_value(output, pad, *value, program);
                writeln!(
                    output,
                    "{pad}{prefix}f{field} = {};",
                    stored_operand(*value)
                )
                .unwrap();
            }
            owned_action(output, pad, value, "CRUST_REHOME", None, program);
            return;
        }
        Expr::IsVariant(value, tag) => format!("{}->tag == {tag}", operand(*value)),
        Expr::TakeTupleField(subject, field) => {
            let place = format!("{}->f{field}", operand(*subject));
            if let Ty::Struct(_) = value.ty {
                let destination = destination.expect("tuple element without storage");
                writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
                if let Some(resource) = owned_resource(value.ty, program) {
                    writeln!(
                        output,
                        "{pad}{}",
                        resource_call(resource, &format!("&{place}"), "0", "CRUST_UNREGISTER")
                    )
                    .unwrap();
                }
                writeln!(output, "{pad}*{target} = {place};").unwrap();
                owned_action(output, pad, value, "CRUST_REHOME", None, program);
                return;
            }
            place
        }
        Expr::TakeVariantField(subject, tag, field) => {
            let place = format!("{}->data.v{tag}.f{field}", operand(*subject));
            if matches!(value.ty, Ty::Allocation(_) | Ty::Handle(..)) {
                // Clear the original owner before the enclosing variant can be cleaned.
                writeln!(output, "{pad}{declaration}{target} = {place};").unwrap();
                writeln!(output, "{pad}{place} = NULL;").unwrap();
                if let Some(resource) = result_resource(value.ty, program) {
                    writeln!(
                        output,
                        "{pad}{}",
                        resource_call(
                            resource,
                            &target,
                            "crust_pool_current_owner()",
                            "CRUST_REHOME"
                        )
                    )
                    .unwrap();
                }
                return;
            }
            let destination = destination.expect("champ déplacé sans réservation");
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            writeln!(output, "{pad}*{target} = {place};").unwrap();
            if let Some(resource) = owned_resource(value.ty, program) {
                let source = format!("&{place}");
                writeln!(
                    output,
                    "{pad}{}",
                    resource_call(resource, &source, "0", "CRUST_DETACH")
                )
                .unwrap();
                owned_action(output, pad, value, "CRUST_ATTACH", None, program);
            }
            return;
        }
        Expr::VariantField(subject, tag, field) => {
            let prefix = if matches!(value.ty, Ty::Struct(_)) {
                "&"
            } else {
                ""
            };
            format!("{prefix}{}->data.v{tag}.f{field}", operand(*subject))
        }
        Expr::BorrowVariantField(value, tag, field) => {
            format!("&{}->data.v{tag}.f{field}", operand(*value))
        }
        Expr::BorrowPoolVariantField(owner, layout, tag, field) => {
            let qualifier = if matches!(value.ty, Ty::Ref { mutable: true, .. }) {
                ""
            } else {
                "const "
            };
            format!(
                "&(({qualifier}CrustVariant{layout}_{tag} *){}->data)->f{field}",
                operand(*owner)
            )
        }
        Expr::PoolVariantField(value, layout, tag, field) => {
            format!(
                "((const CrustVariant{layout}_{tag} *){}->data)->f{field}",
                operand(*value)
            )
        }
        Expr::FutureNew(function, captures) => {
            format!(
                "crust_future_new_{function}({})",
                captures_with_region(captures)
            )
        }
        Expr::FutureSpawn(future, blocking) => {
            let suffix = if *blocking { "_blocking" } else { "" };
            format!("crust_future_spawn{suffix}({})", operand(*future))
        }
        Expr::NativeStart(worker, captures, _) => {
            format!(
                "crust_native_start_{worker}({})",
                captures_with_region(captures)
            )
        }
        Expr::NativeJoin(handle) => {
            let destination = destination.expect("résultat de thread sans réservation");
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            let Ty::Struct(layout) = value.ty else {
                unreachable!()
            };
            let args = completion_arguments(&target, &layouts[layout]);
            writeln!(
                output,
                "{pad}{target}->tag = crust_thread_join({}, {args});",
                operand(*handle)
            )
            .unwrap();
            emit_launch_failed(output, pad, &target);
            owned_action(output, pad, value, "CRUST_ATTACH", None, program);
            return;
        }
        Expr::MapNew => {
            let destination = destination.expect("HashMap sans réservation");
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            writeln!(
                output,
                "{pad}crust_map_new(&{target}->contents, {dedicated});"
            )
            .unwrap();
            return;
        }
        Expr::MapInsert(map, key, input) => {
            let destination = destination.expect("Option sans réservation");
            let value_ty = c_type(input.ty);
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            writeln!(output, "{pad}{target}->tag = crust_map_insert(&{}->contents, (uint64_t){}, &({value_ty}){{ {} }}, sizeof({value_ty}), &{target}->data.v1.f0);",
                operand(*map), operand(*key), operand(*input)).unwrap();
            if matches!(input.ty, Ty::Allocation(_)) {
                owned_action(output, pad, *input, "CRUST_DETACH", Some("0"), program);
                writeln!(
                    output,
                    "{pad}{}->contents.destroy_entry = crust_map_destroy_allocation;",
                    operand(*map)
                )
                .unwrap();
                owned_action(output, pad, value, "CRUST_ATTACH", None, program);
            }
            return;
        }
        Expr::MapGet(map, key) => {
            let destination = destination.expect("Option sans réservation");
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            writeln!(
                output,
                "{pad}{target}->data.v1.f0 = crust_map_get(&{}->contents, (uint64_t)*{});",
                operand(*map),
                operand(*key)
            )
            .unwrap();
            writeln!(output, "{pad}{target}->tag = {target}->data.v1.f0 != NULL;").unwrap();
            return;
        }
        Expr::MapRemove(map, key, element) => {
            let destination = destination.expect("Option sans réservation");
            let value_ty = c_type(*element);
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            writeln!(output, "{pad}{target}->tag = crust_map_remove(&{}->contents, (uint64_t)*{}, sizeof({value_ty}), &{target}->data.v1.f0);", operand(*map), operand(*key)).unwrap();
            if matches!(element, Ty::Allocation(_)) {
                owned_action(output, pad, value, "CRUST_ATTACH", None, program);
            }
            return;
        }
        Expr::PoolGrowing(pool) => {
            writeln!(
                output,
                "{pad}{declaration}{target} = crust_pool_take({}, 0);",
                operand(*pool)
            )
            .unwrap();
            writeln!(output, "{pad}{target}->growing = true;").unwrap();
            let take = if dedicated {
                "crust_region_take_dedicated"
            } else {
                "crust_region_take"
            };
            writeln!(output, "{pad}*(CrustGrowing *){target}->data = {take}();").unwrap();
            return;
        }
        Expr::GrowingLen(handle, element) => {
            format!(
                "((const CrustGrowing *){}->data)->used / sizeof({})",
                operand(*handle),
                stored_type(*element)
            )
        }
        Expr::VectorExtract(handle, index, element) => {
            let handle = operand(*handle);
            let stored = stored_type(*element);
            let pop = index.is_none();
            let index = index.map_or("0".to_owned(), operand);
            let place = if pop {
                format!("{target}->data.v1.f0")
            } else if matches!(element, Ty::Struct(_)) {
                format!("*{target}")
            } else {
                target.clone()
            };
            if let Some(destination) = destination {
                writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            } else if !async_body {
                writeln!(output, "{pad}{declaration}{target};").unwrap();
            }
            let call = format!(
                "crust_vector_extract((CrustGrowing *){handle}->data, (uint64_t){index}, sizeof({stored}), {}, &({place}))",
                u8::from(pop)
            );
            if pop {
                writeln!(output, "{pad}{target}->tag = {call};").unwrap();
                writeln!(
                    output,
                    "{pad}if (!{target}->tag) {target}->data.v0.empty = 0;"
                )
                .unwrap();
            } else {
                writeln!(output, "{pad}(void){call};").unwrap();
            }
            if let Some(resource) = result_resource(*element, program) {
                let guard = if pop {
                    format!("if ({target}->tag) ")
                } else {
                    String::new()
                };
                let place = if matches!(element, Ty::Struct(_)) {
                    format!("&({place})")
                } else {
                    place
                };
                writeln!(
                    output,
                    "{pad}{guard}{}",
                    resource_call(
                        resource,
                        &place,
                        &format!("(uintptr_t){handle}"),
                        "CRUST_EXTRACT"
                    )
                )
                .unwrap();
            }
            return;
        }
        Expr::GrowingIndex(handle, index) => {
            let stored = stored_type(value.ty);
            let address = format!(
                "crust_region_element((const CrustGrowing *){}->data, (uint64_t){}, sizeof({stored}))",
                operand(*handle),
                operand(*index)
            );
            if matches!(value.ty, Ty::Struct(_)) {
                format!("(const {stored} *){address}")
            } else {
                format!("*({stored} const *){address}")
            }
        }
        Expr::PoolNew(pool, init, variants) => {
            let pool = operand(*pool);
            let init_value = operand(*init);
            if let Some(fields) = placement.pool_initializers.get(&init.temp) {
                writeln!(
                    output,
                    "{pad}{declaration}{target} = crust_pool_take({pool}, 0);"
                )
                .unwrap();
                let stored = stored_type(init.ty);
                let place = format!("(({stored} *){target}->data)");
                for (field, input) in fields {
                    writeln!(
                        output,
                        "{pad}{place}->f{field} = {};",
                        stored_operand(*input)
                    )
                    .unwrap();
                }
                if let Ty::Struct(layout) = init.ty
                    && crate::verify::inline_destructor(init.ty, layouts)
                {
                    for (_, input) in fields {
                        detach_destructor_value(output, pad, *input, program);
                    }
                    writeln!(output, "{pad}{target}->finalize = crust_finalize_{layout};").unwrap();
                }
                adopt_owned_at(output, pad, &target, init.ty, &place, program);
                return;
            }
            if *variants == 0 {
                writeln!(
                    output,
                    "{pad}{declaration}{target} = crust_pool_take({pool}, 0);"
                )
                .unwrap();
                writeln!(
                    output,
                    "{pad}*({} *){target}->data = {};",
                    stored_type(init.ty),
                    stored_operand(*init)
                )
                .unwrap();
            } else {
                let Ty::Struct(layout) = init.ty else {
                    unreachable!()
                };
                writeln!(
                    output,
                    "{pad}{declaration}{target} = crust_pool_take({pool}, {init_value}->tag);"
                )
                .unwrap();
                writeln!(output, "{pad}switch ({init_value}->tag) {{").unwrap();
                for tag in 0..*variants {
                    writeln!(output, "{pad}case {tag}:").unwrap();
                    writeln!(output, "{pad}    *(CrustVariant{layout}_{tag} *){target}->data = {init_value}->data.v{tag};").unwrap();
                    writeln!(output, "{pad}    break;").unwrap();
                }
                writeln!(output, "{pad}default: abort();").unwrap();
                writeln!(output, "{pad}}}").unwrap();
            }
            if let Ty::Struct(layout) = init.ty
                && crate::verify::inline_destructor(init.ty, layouts)
            {
                if *variants == 0 {
                    writeln!(output, "{pad}{target}->finalize = crust_finalize_{layout};").unwrap();
                } else {
                    writeln!(output, "{pad}switch ({target}->tag) {{").unwrap();
                    for tag in 0..*variants {
                        writeln!(output, "{pad}case {tag}: {target}->finalize = crust_finalize_{layout}_{tag}; break;").unwrap();
                    }
                    writeln!(output, "{pad}default: abort(); }}").unwrap();
                }
            }
            adopt_owned(output, pad, &target, *init, program);
            return;
        }
        Expr::PoolBorrow(binding) => format!("&b{}->header", binding.0),
        Expr::PoolTake(input) => {
            let allocation = operand(*input);
            let stored = stored_type(value.ty);
            if let Ty::Struct(layout) = value.ty {
                let destination = destination.expect("contenu de pool sans réservation");
                writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
                if layouts[layout].variants.is_empty() {
                    writeln!(output, "{pad}*{target} = *({stored} *){allocation}->data;").unwrap();
                } else {
                    writeln!(
                        output,
                        "{pad}{target}->tag = {allocation}->tag; switch ({allocation}->tag) {{"
                    )
                    .unwrap();
                    for tag in 0..layouts[layout].variants.len() {
                        writeln!(output, "{pad}case {tag}: {target}->data.v{tag} = *(CrustVariant{layout}_{tag} *){allocation}->data; break;").unwrap();
                    }
                    writeln!(output, "{pad}default: abort(); }}").unwrap();
                }
            } else {
                writeln!(
                    output,
                    "{pad}{declaration}{target} = *({stored} *){allocation}->data;"
                )
                .unwrap();
            }
            let resource = result_resource(value.ty, program).unwrap();
            writeln!(
                output,
                "{pad}{}",
                resource_call(
                    resource,
                    &target,
                    &format!("(uintptr_t){allocation}"),
                    "CRUST_EXTRACT"
                )
            )
            .unwrap();
            if crate::verify::inline_destructor(value.ty, layouts) {
                writeln!(output, "{pad}{allocation}->finalize = NULL;").unwrap();
            }
            writeln!(output, "{pad}crust_pool_drop({allocation});").unwrap();
            return;
        }
        Expr::PoolRead(handle) => {
            let handle = operand(*handle);
            if matches!(value.ty, Ty::Struct(_)) {
                format!("({ty}){handle}->data")
            } else {
                format!("*({ty} *){handle}->data")
            }
        }
        Expr::Pool => {
            let destination = destination.expect("pool sans réservation");
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            let Ty::Struct(index) = value.ty else {
                unreachable!()
            };
            let (element, capacity) = layouts[index].pool.unwrap();
            let arms = if let Ty::Struct(index) = element {
                layouts[index].variants.len().max(1)
            } else {
                1
            };
            writeln!(output, "{pad}memset({target}, 0, sizeof(*{target}));").unwrap();
            writeln!(
                output,
                "{pad}{target}->header = (CrustPool){{ {capacity}, {target}->arms }};"
            )
            .unwrap();
            for tag in 0..arms {
                writeln!(output, "{pad}{target}->arms[{tag}] = (CrustPoolArm){{ .stride = sizeof(*{target}->slots_{tag}), .data = (unsigned char *){target}->slots_{tag}, .records = {target}->records[{tag}] }};").unwrap();
            }
            return;
        }
        Expr::Array(values, repeat) => {
            let destination = destination.expect("tableau sans réservation");
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            if *repeat && let Some(&element) = values.first() {
                writeln!(output, "{pad}for (size_t i = 0; i < sizeof({target}->elements) / sizeof(*{target}->elements); ++i) {{").unwrap();
                writeln!(
                    output,
                    "{pad}    {target}->elements[i] = {};",
                    stored_operand(element)
                )
                .unwrap();
                writeln!(output, "{pad}}}").unwrap();
            } else {
                for (index, &element) in values.iter().enumerate() {
                    detach_destructor_value(output, pad, element, program);
                    writeln!(
                        output,
                        "{pad}{target}->elements[{index}] = {};",
                        stored_operand(element)
                    )
                    .unwrap();
                }
            }
            owned_action(output, pad, value, "CRUST_REHOME", None, program);
            return;
        }
        Expr::Index(owner, index) => {
            let index_text = operand(*index);
            let address = if matches!(value.ty, Ty::Struct(_)) {
                "&"
            } else {
                ""
            };
            format!(
                "{address}{}->elements[(size_t){index_text}]",
                operand(*owner)
            )
        }
        Expr::Field(owner, field) => {
            let address = if matches!(value.ty, Ty::Struct(_)) {
                "&"
            } else {
                ""
            };
            format!("{address}{}->f{field}", operand(*owner))
        }
        Expr::Integer(number) => {
            if value.ty.unsigned() {
                format!("UINT64_C({number})")
            } else if *number == i64::MIN as i128 {
                "INT64_MIN".to_owned()
            } else if *number < 0 {
                format!("-INT64_C({})", number.unsigned_abs())
            } else {
                format!("INT64_C({number})")
            }
        }
        Expr::Float(literal) => literal.clone(),
        Expr::Boolean(value) => value.to_string(),
        Expr::Local(binding) if matches!(value.ty, Ty::Struct(_)) => format!("b{}", binding.0),
        Expr::Local(binding) => format!("*b{}", binding.0),
        Expr::Slice(array, length, end) => {
            let size = if let Some(end) = end {
                let bound = operand(*end);
                let negative = if end.ty.signed() {
                    format!("{bound} < 0 || ")
                } else {
                    String::new()
                };
                writeln!(output, "{pad}if ({negative}(uint64_t){bound} > UINT64_C({length})) {{ fputs(\"corbo: borne de tranche hors du tableau\\n\", stderr); exit(EXIT_FAILURE); }}").unwrap();
                format!("(uintptr_t){bound}")
            } else {
                length.to_string()
            };
            format!("(CrustSlice){{{}->elements, {size}}}", operand(*array))
        }
        Expr::GrowingSlice(handle, element) => {
            let name = format!("{target}_growing");
            let element = stored_type(*element);
            writeln!(
                output,
                "{pad}CrustGrowing *{name} = (CrustGrowing *){}->data;",
                operand(*handle)
            )
            .unwrap();
            format!("(CrustSlice){{crust_region_data({name}), {name}->used / sizeof({element})}}")
        }
        Expr::Subslice(slice, start, end) => {
            let Ty::Slice { element, .. } = slice.ty else {
                unreachable!()
            };
            let element = stored_type(element.ty());
            let source = operand(*slice);
            let lo = operand(*start);
            let hi = operand(*end);
            let mut checks = String::new();
            if start.ty.signed() {
                write!(checks, "{lo} < 0 || ").unwrap();
            }
            if end.ty.signed() {
                write!(checks, "{hi} < 0 || ").unwrap();
            }
            writeln!(output, "{pad}if ({checks}(uint64_t){lo} > (uint64_t){hi} || (uint64_t){hi} > {source}.len) {{ fputs(\"corbo: bornes de sous-tranche invalides\\n\", stderr); exit(EXIT_FAILURE); }}").unwrap();
            format!(
                "(CrustSlice){{{lo} == 0 ? {source}.data : ({element} const *){source}.data + (size_t){lo}, (uintptr_t){hi} - (uintptr_t){lo}}}"
            )
        }
        Expr::ProcessArgs => {
            let destination = destination.expect("arguments sans réservation");
            writeln!(output, "{pad}{declaration}{target} = {destination};").unwrap();
            writeln!(output, "{pad}{target}->tag = crust_args_status == 0;").unwrap();
            writeln!(
                output,
                "{pad}if ({target}->tag) {target}->data.v1.f0 = crust_args;"
            )
            .unwrap();
            writeln!(
                output,
                "{pad}else {{ {target}->data.v0.f0.tag = crust_args_status - 1; }}"
            )
            .unwrap();
            // Unit enum payload fields are initialized like ordinary variant constructors.
            writeln!(output, "{pad}if (!{target}->tag) {{ if (crust_args_status == 1) {target}->data.v0.f0.data.v0.empty = 0; else {target}->data.v0.f0.data.v1.empty = 0; }}").unwrap();
            return;
        }
        Expr::StrLiteral(bytes) => {
            let mut text = String::new();
            for byte in bytes {
                write!(text, "\\{byte:03o}").unwrap();
            }
            format!("(CrustSlice){{\"{text}\", {}}}", bytes.len())
        }
        Expr::StrBytes(text) => operand(*text),
        Expr::SliceLen(slice) => format!("{}.len", operand(*slice)),
        Expr::SliceElementAddress(slice, index) => {
            let Ty::Slice { element, .. } = slice.ty else {
                unreachable!()
            };
            let element = stored_type(element.ty());
            let slice = operand(*slice);
            let position = operand(*index);
            let negative = if index.ty.signed() {
                format!("{position} < 0 || ")
            } else {
                String::new()
            };
            writeln!(output, "{pad}if ({negative}(uint64_t){position} >= {slice}.len) {{ fputs(\"corbo: indice hors de la tranche\\n\", stderr); exit(EXIT_FAILURE); }}").unwrap();
            format!("(uintptr_t)(({element} const *){slice}.data + (size_t){position})")
        }
        Expr::SliceElementBorrow(address) => format!("({ty}){}", operand(*address)),
        Expr::SliceElement(address) if matches!(value.ty, Ty::Struct(_)) => {
            format!("({ty}){}", operand(*address))
        }
        Expr::SliceElement(address) => {
            format!("*({} const *){}", stored_type(value.ty), operand(*address))
        }
        Expr::Address(reference) => format!("(uintptr_t){}", operand(*reference)),
        Expr::Borrow(binding) => format!("b{}", binding.0),
        Expr::BorrowField(owner, field) => format!("({ty})&{}->f{field}", operand(*owner)),
        Expr::BorrowIndex(owner, index) => format!(
            "({ty})&{}->elements[(size_t){}]",
            operand(*owner),
            operand(*index)
        ),
        Expr::Reborrow(binding) => format!("*b{}", binding.0),
        Expr::Temporary(source) => operand(*source),
        Expr::BorrowThrough(reference) => operand(*reference),
        Expr::DereferenceValue(reference) if matches!(value.ty, Ty::Struct(_)) => {
            operand(*reference)
        }
        Expr::DereferenceValue(reference) => format!("*({})", operand(*reference)),
        Expr::Dereference(binding) if matches!(value.ty, Ty::Struct(_)) => {
            format!("*b{}", binding.0)
        }
        Expr::Dereference(binding) => format!("**b{}", binding.0),
        Expr::Shift(left, right, bits, leftward) => {
            let count = operand(*right);
            let negative = if right.ty.signed() {
                format!("{count} < 0 || ")
            } else {
                String::new()
            };
            writeln!(
                output,
                "{pad}if ({negative}(uint64_t){count} >= {bits}) crust_arithmetic_error();"
            )
            .unwrap();
            let input = operand(*left);
            if !leftward {
                // C leaves right shift of a negative signed integer implementation-defined.
                let shifted = if left.ty.signed() {
                    format!(
                        "{input} < 0 ? -1 - ({ty})((uint64_t)(-1 - {input}) >> {count}) : ({ty})((uint64_t){input} >> {count})"
                    )
                } else {
                    format!("({ty})((uint64_t){input} >> {count})")
                };
                writeln!(output, "{pad}{declaration}{target} = {shifted};").unwrap();
                return;
            }
            if !async_body {
                writeln!(output, "{pad}{ty} {target};").unwrap();
            }
            // Only shift the unsigned factor. Checked multiplication preserves
            // the mathematical result, including for a negative left operand.
            writeln!(output, "{pad}if (__builtin_mul_overflow({input}, UINT64_C(1) << {count}, &{target})) crust_arithmetic_error();").unwrap();
            return;
        }
        Expr::Cast(input) => format!("({ty})({})", operand(*input)),
        Expr::Unary(operator, operand) if operator == "-" && value.ty.signed() => {
            if !async_body {
                writeln!(output, "{pad}{ty} {target};").unwrap();
            }
            writeln!(output, "{pad}if (__builtin_sub_overflow(({ty})0, {}, &{target})) crust_arithmetic_error();", self::operand(*operand)).unwrap();
            return;
        }
        Expr::Unary(operator, operand) => format!("{operator}{}", self::operand(*operand)),
        Expr::Call(index, values, _) if scalar_result(value.ty) => {
            let mut args = vec![format!("o{}", value.temp)];
            args.extend(values.iter().map(|&argument| operand(argument)));
            writeln!(output, "{pad}crust_fn_{index}({});", args.join(", ")).unwrap();
            format!("*o{}", value.temp)
        }
        Expr::Call(index, values, _) => {
            let mut arguments = arguments(values);
            if let Some(destination) = destination {
                if arguments.is_empty() {
                    arguments = destination;
                } else {
                    arguments = format!("{destination}, {arguments}");
                }
            }
            format!("crust_fn_{index}({arguments})")
        }
        Expr::Binary(operator, left, right) => {
            let lhs = operand(*left);
            let rhs = operand(*right);
            if matches!(left.ty, Ty::Slice { .. }) {
                let comparison = format!("({lhs}.data == {rhs}.data && {lhs}.len == {rhs}.len)");
                let negate = if operator == "!=" { "!" } else { "" };
                writeln!(output, "{pad}{declaration}{target} = {negate}{comparison};").unwrap();
                return;
            }
            match operator.as_str() {
                "+" | "-" | "*" | "/" | "%" if left.ty.float() => {
                    if matches!(operator.as_str(), "/" | "%") {
                        writeln!(output, "{pad}if ({rhs} == 0) crust_arithmetic_error();").unwrap();
                    }
                    if operator == "%" {
                        let function = if left.ty == Ty::F32 { "fmodf" } else { "fmod" };
                        format!("{function}({lhs}, {rhs})")
                    } else {
                        format!("{lhs} {operator} {rhs}")
                    }
                }
                "+" | "-" | "*" => {
                    let builtin = match operator.as_str() {
                        "+" => "add",
                        "-" => "sub",
                        _ => "mul",
                    };
                    if !async_body {
                        writeln!(output, "{pad}{ty} {target};").unwrap();
                    }
                    writeln!(output, "{pad}if (__builtin_{builtin}_overflow({lhs}, {rhs}, &{target})) crust_arithmetic_error();").unwrap();
                    return;
                }
                "/" | "%" => {
                    writeln!(output, "{pad}if ({rhs} == 0) crust_arithmetic_error();").unwrap();
                    if left.ty.unsigned() {
                        return writeln!(
                            output,
                            "{pad}{declaration}{target} = {lhs} {operator} {rhs};"
                        )
                        .unwrap();
                    }
                    let min = if left.ty == Ty::I32 {
                        "INT32_MIN"
                    } else {
                        "INT64_MIN"
                    };
                    let overflow = format!("{lhs} == {min} && {rhs} == -1");
                    if operator == "/" {
                        writeln!(output, "{pad}if ({overflow}) crust_arithmetic_error();").unwrap();
                        format!("{lhs} / {rhs}")
                    } else {
                        format!("({overflow}) ? 0 : {lhs} % {rhs}")
                    }
                }
                _ => format!("{lhs} {operator} {rhs}"),
            }
        }
    };
    writeln!(output, "{pad}{declaration}{target} = {initial};").unwrap();
}
