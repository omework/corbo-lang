//! Resolve Crust operands while leaving target instructions to the assembler.
use crate::{Error, tree::BindingId, verify::Ty};

#[derive(Debug)]
pub(crate) struct Operand {
    pub binding: BindingId,
    pub written: bool,
}

#[derive(Debug, Clone, Copy)]
pub(crate) enum Abi {
    Linux,
    LinuxArm64,
    DarwinX64,
    DarwinArm64,
    WindowsX64,
    WindowsArm64,
}

impl Abi {
    fn arm(self) -> bool {
        matches!(self, Self::LinuxArm64 | Self::DarwinArm64 | Self::WindowsArm64)
    }

    pub fn routine(self, name: &str, body: &str) -> String {
        match self {
            Self::Linux => format!(
                ".text\n.local {name}\n.type {name}, @function\n{name}:\n.intel_syntax noprefix\npush r12\nmov r12, rdi\n{body}pop r12\nret\n.att_syntax prefix\n.size {name}, .-{name}\n"
            ),
            Self::DarwinX64 | Self::WindowsX64 => {
                let (symbol, input) = if matches!(self, Self::DarwinX64) {
                    (format!("_{name}"), "rdi")
                } else {
                    (name.to_owned(), "rcx")
                };
                format!(
                    ".text\n{symbol}:\n.intel_syntax noprefix\npush r12\nmov r12, {input}\n{body}pop r12\nret\n.att_syntax prefix\n"
                )
            }
            Self::LinuxArm64 | Self::DarwinArm64 | Self::WindowsArm64 => {
                let prefix = if matches!(self, Self::DarwinArm64) {
                    "_"
                } else {
                    ""
                };
                format!(
                    ".text\n{prefix}{name}:\nstp x19, x30, [sp, #-16]!\nmov x19, x0\n{body}ldp x19, x30, [sp], #16\nret\n"
                )
            }
        }
    }
}

#[derive(Debug)]
pub(crate) struct Block {
    pub abi: Abi,
    pub offset: usize,
    pub code: String,
    pub operands: Vec<Operand>,
}

pub(crate) fn lower(
    abi: Abi,
    template: &str,
    offset: usize,
    mut resolve: impl FnMut(usize, bool) -> Result<(BindingId, Ty), Error>,
) -> Result<Block, Error> {
    let mut block = Block {
        abi,
        offset,
        code: String::new(),
        operands: Vec::new(),
    };
    let body = &template[template.find('{').unwrap() + 1..template.len() - 1];
    let mut occurrence = 0;
    for line in body.lines() {
        let code = line.split_once("//").map_or(line, |(code, _)| code).trim();
        if !code.contains("${") {
            block.code.push_str(code);
            block.code.push('\n');
            continue;
        }
        let (mnemonic, args) = code
            .split_once(char::is_whitespace)
            .ok_or_else(|| Error::new(offset, "instruction attendue pour l’opérande assembleur"))?;
        if !mnemonic.eq_ignore_ascii_case("mov") {
            return Err(Error::new(
                offset,
                "les opérandes Crust sont pris en charge dans mov",
            ));
        }
        let (destination, source) = args
            .split_once(',')
            .ok_or_else(|| Error::new(offset, "mov attend deux opérandes"))?;
        if destination.contains("${") && source.contains("${") {
            return Err(Error::new(
                offset,
                "mov entre deux opérandes Crust exige un registre intermédiaire",
            ));
        }
        let mut memory_instruction = "mov";
        let mut lower_operand = |text: &str, register: &str, written| -> Result<String, Error> {
            let text = text.trim();
            if !text.contains("${") {
                return Ok(text.into());
            }
            let valid = text
                .strip_prefix("${")
                .and_then(|text| text.strip_suffix('}'))
                .is_some_and(|name| {
                    name.bytes()
                        .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
                });
            if !valid {
                return Err(Error::new(offset, "${nom} doit occuper un opérande entier"));
            }
            let (binding, ty) = resolve(occurrence, written)?;
            occurrence += 1;
            let width = match ty {
                Ty::U8 => "BYTE",
                Ty::U16 => "WORD",
                Ty::I32 | Ty::U32 => "DWORD",
                Ty::I64 | Ty::U64 | Ty::Usize => "QWORD",
                _ => {
                    return Err(Error::new(
                        offset,
                        "mov avec un opérande Crust exige un entier",
                    ));
                }
            };
            let slot =
                if let Some(slot) = block.operands.iter().position(|op| op.binding == binding) {
                    block.operands[slot].written |= written;
                    slot
                } else {
                    let slot = block.operands.len();
                    block.operands.push(Operand { binding, written });
                    slot
                };
            if abi.arm() {
                let prefix = if width == "QWORD" { 'x' } else { 'w' };
                if !register.trim().to_ascii_lowercase().starts_with(prefix) {
                    return Err(Error::new(
                        offset,
                        "largeur du registre ARM64 incompatible avec l’opérande",
                    ));
                }
                memory_instruction = match (written, width) {
                    (true, "BYTE") => "strb",
                    (true, "WORD") => "strh",
                    (false, "BYTE") => "ldrb",
                    (false, "WORD") => "ldrh",
                    (true, _) => "str",
                    (false, _) => "ldr",
                };
                Ok(format!("[x19, #{}]", slot * 8))
            } else {
                Ok(format!("{width} PTR [r12 + {}]", slot * 8))
            }
        };
        let store = destination.contains("${");
        let target = lower_operand(destination, source, true)?;
        let input = lower_operand(source, destination, false)?;
        use std::fmt::Write;
        if abi.arm() && store {
            writeln!(block.code, "{memory_instruction} {input}, {target}").unwrap();
        } else {
            writeln!(block.code, "{memory_instruction} {target}, {input}").unwrap();
        }
    }
    Ok(block)
}
