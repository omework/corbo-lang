" SPDX-License-Identifier: MIT OR Apache-2.0
if exists('b:current_syntax')
  finish
endif

syntax keyword corboDeclaration fn struct enum impl const let pub extern use
syntax keyword corboModifier mut move async
syntax keyword corboControl if else match loop while for in break continue return yield await as unsafe
syntax keyword corboBoolean true false
syntax keyword corboReceiver self
syntax keyword corboType bool Void i32 i64 u8 u16 u32 u64 usize f32 f64 str char String
syntax keyword corboType A Pool PoolError Vector Option Result Mutex AsyncMutex HashMap
syntax match corboNamespace /\<\%(std\|runtime\)\>\ze::/
syntax match corboBuiltin /\<\%(addr\|copy\|drop\|print\)\>\ze\s*(/
syntax match corboFunction /\%(\<fn\s\+\)\@<=[A-Za-z_][A-Za-z_0-9]*/
syntax match corboAnnotation /#\s*(\s*\%(if\|endif\|branch\|datastack\|directive\|free_pages\|lock\|stack_region\|type\)\>/
syntax match corboUnchecked /@unchecked\>/

syntax match corboOperator /::\|->\|=>\|\.\.\|[+*\/%&|^!~?=<>-]/
syntax match corboNumber /\<0[xX][0-9A-Fa-f]\+\>/
syntax match corboNumber /\<[0-9]\+\%([KMG]\)\?\>/
syntax match corboFloat /\<[0-9]\+\.\%(\.\)\@![0-9]*/
syntax match corboFloat /\%([A-Za-z_0-9.]\)\@<!\.[0-9]\+/

syntax match corboTodo /\<\%(TODO\|FIXME\|XXX\)\>/ contained
syntax match corboComment /\/\/.*$/ contains=corboTodo,@Spell
syntax match corboDocComment /\/\/[\/!].*$/ contains=corboTodo,@Spell
syntax match corboEscape /\\\%(["\\/bfnrt]\|u[0-9A-Fa-f]\{4}\)/ contained
syntax region corboString start=/"/ skip=/\\./ end=/"/ end=/$/ contains=corboEscape,@Spell

syntax match corboAsmOperand /\${[A-Za-z_][A-Za-z_0-9]*}/ contained
syntax region corboAsm matchgroup=corboAnnotation start=/@asm\>\_s*{/ end=/}/
      \ contains=corboAsmOperand,corboComment,corboDocComment
syntax sync fromstart

highlight default link corboDeclaration Keyword
highlight default link corboModifier StorageClass
highlight default link corboControl Statement
highlight default link corboBoolean Boolean
highlight default link corboReceiver Identifier
highlight default link corboType Type
highlight default link corboNamespace Include
highlight default link corboBuiltin Function
highlight default link corboFunction Function
highlight default link corboAnnotation PreProc
highlight default link corboUnchecked PreProc
highlight default link corboOperator Operator
highlight default link corboNumber Number
highlight default link corboFloat Float
highlight default link corboTodo Todo
highlight default link corboComment Comment
highlight default link corboDocComment SpecialComment
highlight default link corboEscape SpecialChar
highlight default link corboString String
highlight default link corboAsmOperand Special

let b:current_syntax = 'corbo'
