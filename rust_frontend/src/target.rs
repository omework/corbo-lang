use crate::{
    Error,
    lexer::{Kind, Token, decoded_text},
};

#[derive(Clone, Debug)]
pub struct Target {
    os: String,
    family: String,
    arch: String,
    pointer_width: Option<u32>,
}

impl Target {
    pub fn host() -> Self {
        Self {
            os: std::env::consts::OS.into(),
            family: std::env::consts::FAMILY.into(),
            arch: std::env::consts::ARCH.into(),
            pointer_width: Some(usize::BITS),
        }
    }

    pub fn from_triple(triple: &str) -> Result<Self, String> {
        let mut parts = triple.split('-');
        let arch = parts.next().unwrap_or_default();
        let (os, family) = parts
            .find_map(|part| match part {
                "darwin" | "macos" => Some(("macos", "unix")),
                "linux" | "freebsd" | "netbsd" | "openbsd" | "dragonfly" | "android" | "ios"
                | "solaris" | "illumos" => Some((part, "unix")),
                "windows" => Some(("windows", "windows")),
                _ => None,
            })
            .ok_or_else(|| format!("unsupported target: {triple}"))?;
        if arch.is_empty() {
            return Err(format!("missing architecture in target: {triple}"));
        }
        let arch = match arch {
            "i386" | "i586" | "i686" => "x86",
            _ => arch,
        };
        Ok(Self {
            os: os.into(),
            family: family.into(),
            arch: arch.into(),
            pointer_width: match arch {
                "x86_64" if triple.ends_with("gnux32") => Some(32),
                "aarch64" if triple.ends_with("gnu_ilp32") => Some(32),
                "x86_64" | "aarch64" | "riscv64" | "powerpc64" | "powerpc64le" | "s390x"
                | "mips64" | "mips64el" | "loongarch64" | "sparc64" => Some(64),
                "x86" | "arm" | "armv7" | "armv7s" | "thumbv7neon" | "riscv32" | "powerpc"
                | "mips" | "mipsel" | "sparc" => Some(32),
                _ => None,
            },
        })
    }

    pub(crate) fn pointer_width(&self) -> Option<u32> {
        self.pointer_width
    }

    pub(crate) fn assembly_abi(&self) -> Option<crate::assembly::Abi> {
        use crate::assembly::Abi;
        if self.pointer_width != Some(64) {
            return None;
        }
        match (self.os.as_str(), self.arch.as_str()) {
            ("linux", "x86_64") => Some(Abi::Linux),
            ("linux", "aarch64") => Some(Abi::LinuxArm64),
            ("macos", "x86_64") => Some(Abi::DarwinX64),
            ("macos", "aarch64") => Some(Abi::DarwinArm64),
            ("windows", "x86_64") => Some(Abi::WindowsX64),
            ("windows", "aarch64") => Some(Abi::WindowsArm64),
            _ => None,
        }
    }

    fn property(&self, key: &str) -> Option<&str> {
        match key {
            "os" => Some(&self.os),
            "family" => Some(&self.family),
            "arch" => Some(&self.arch),
            "pointer_width" => match self.pointer_width {
                Some(32) => Some("32"),
                Some(64) => Some("64"),
                _ => Some("unknown"),
            },
            _ => None,
        }
    }
}

// Keep original spans for diagnostics. Filter before collecting type names
// or building any package symbol table.
pub(crate) fn select(
    source: &str,
    tokens: Vec<Token>,
    target: &Target,
) -> Result<Vec<Token>, Error> {
    let word = |index: usize| {
        tokens
            .get(index)
            .map_or("", |token| &source[token.span.start..token.span.end])
    };
    let error = |index: usize, message| {
        Error::new(
            tokens.get(index).map_or(source.len(), |t| t.span.start),
            message,
        )
    };
    let mut selected = Vec::new();
    let mut stack = Vec::new();
    let mut cursor = 0;
    while cursor < tokens.len() {
        if stack.is_empty()
            && word(cursor) == "#"
            && word(cursor + 1) == "("
            && word(cursor + 2) == "if"
        {
            if word(cursor + 3) != ":" {
                return Err(error(cursor + 3, "malformed target condition"));
            }
            let mut condition = cursor + 4;
            let mut include = false;
            let mut conjunction = true;
            loop {
                for (offset, expected) in [(0, "target"), (1, "."), (3, "==")] {
                    if word(condition + offset) != expected {
                        return Err(error(condition + offset, "malformed target condition"));
                    }
                }
                let actual = target
                    .property(word(condition + 2))
                    .ok_or_else(|| error(condition + 2, "unknown target property"))?;
                if tokens
                    .get(condition + 4)
                    .is_none_or(|token| token.kind != Kind::Text)
                {
                    return Err(error(condition + 4, "target condition expects a string"));
                }
                conjunction &= decoded_text(word(condition + 4)) == actual.as_bytes();
                condition += 5;
                match word(condition) {
                    "&&" => {}
                    "||" => {
                        include |= conjunction;
                        conjunction = true;
                    }
                    _ => break,
                }
                condition += 1;
            }
            if word(condition) != "{" {
                return Err(error(condition, "malformed target condition"));
            }
            let start = condition + 1;
            let mut end = start;
            let mut depth = 1;
            while end < tokens.len() - 1 {
                match word(end) {
                    "{" => depth += 1,
                    "}" => depth -= 1,
                    _ => {}
                }
                if depth == 0 {
                    break;
                }
                end += 1;
            }
            if word(end) != "}" || word(end + 1) != ")" {
                return Err(error(end, "target selection must end with })"));
            }
            if include || conjunction {
                selected.extend_from_slice(&tokens[start..end]);
            }
            cursor = end + 2;
            continue;
        }
        match word(cursor) {
            "{" => stack.push("}"),
            "(" => stack.push(")"),
            "[" => stack.push("]"),
            close if stack.last() == Some(&close) => {
                stack.pop();
            }
            _ => {}
        }
        selected.push(tokens[cursor].clone());
        cursor += 1;
    }
    Ok(selected)
}
