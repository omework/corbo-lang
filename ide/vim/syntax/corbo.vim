" SPDX-License-Identifier: MIT OR Apache-2.0
if exists('b:current_syntax')
  finish
endif

syntax keyword corboDeclaration fn impl let pub extern use
syntax keyword corboStructure struct enum
syntax keyword corboTypedef type
syntax keyword corboModifier mut move const
syntax keyword corboAsync async
syntax keyword corboAwait await
syntax keyword corboConditional if else match
syntax keyword corboRepeat loop while for in
syntax keyword corboControl break continue return yield
syntax keyword corboCast as
syntax keyword corboUnsafe unsafe
syntax keyword corboBoolean true false
syntax keyword corboReceiver self
syntax keyword corboType Self bool Void i32 i64 u8 u16 u32 u64 usize f32 f64 str char String
syntax keyword corboType A Pool PoolError Vector Option Result Mutex AsyncMutex HashMap
syntax match corboNamespace /\<\%(std\|runtime\)\>\ze::/
syntax match corboBuiltin /\<\%(addr\|copy\|drop\|print\)\>\ze\s*(/
syntax match corboFunction /\%(\<fn\s\+\)\@<=[A-Za-z_][A-Za-z_0-9]*/
syntax match corboAnnotation /#\s*(\s*\%(if\|endif\|branch\|datastack\|directive\|free_pages\|lock\|stack_region\|type\|configurable\|override\|thread\)\>/
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

" Embed the installed C++ syntax; Corbo itself still owns the outer boundary.
syntax include @corboCpp syntax/cpp.vim
unlet! b:current_syntax
syntax region corboCppOptions start=/(/ end=/)/ contained contains=corboString
syntax region corboCppBody matchgroup=corboAnnotation start=/{/ end=/}/ contained
      \ contains=@corboCpp,corboCppBody,corboAsmOperand
syntax region corboCpp matchgroup=corboAnnotation start=/@c++\ze\%([ \t]*(\|[ \t]*{\)/ end=/\%(}\)\@<=/
      \ contains=corboCppOptions,corboCppBody

syntax match corboAsmOperand /\${[A-Za-z_][A-Za-z_0-9]*}/ contained
syntax region corboAsm matchgroup=corboAnnotation start=/@asm\>\_s*{/ end=/}/
      \ contains=corboAsmOperand,corboComment,corboDocComment
syntax sync fromstart

" Reuse Rust-specific colorscheme groups without loading Rust syntax rules.
" Default links also work when no Rust buffer has been opened.
highlight default link rustKeyword Keyword
highlight default link rustStructure Keyword
highlight default link rustTypedef Keyword
highlight default link rustStorage StorageClass
highlight default link rustAsync rustKeyword
highlight default link rustAwait rustKeyword
highlight default link rustConditional Conditional
highlight default link rustRepeat Conditional
highlight default link rustUnsafeKeyword Exception
highlight default link rustBoolean Boolean
highlight default link rustSelf Constant
highlight default link rustType Type
highlight default link rustModPath Include
highlight default link rustFunction Function
highlight default link rustFuncName Function
highlight default link rustOperator Operator
highlight default link rustNumber Number
highlight default link rustFloat Float
highlight default link rustCommentLine Comment
highlight default link rustCommentLineDoc SpecialComment
highlight default link rustEscape Special
highlight default link rustString String

highlight default link corboDeclaration rustKeyword
highlight default link corboStructure rustStructure
highlight default link corboTypedef rustTypedef
highlight default link corboModifier rustStorage
highlight default link corboAsync rustAsync
highlight default link corboAwait rustAwait
highlight default link corboConditional rustConditional
highlight default link corboRepeat rustRepeat
highlight default link corboControl rustKeyword
highlight default link corboCast rustOperator
highlight default link corboUnsafe rustUnsafeKeyword
highlight default link corboBoolean rustBoolean
highlight default link corboReceiver rustSelf
highlight default link corboType rustType
highlight default link corboNamespace rustModPath
highlight default link corboBuiltin rustFunction
highlight default link corboFunction rustFuncName
highlight default link corboAnnotation PreProc
highlight default link corboUnchecked rustUnsafeKeyword
highlight default link corboOperator rustOperator
highlight default link corboNumber rustNumber
highlight default link corboFloat rustFloat
highlight default link corboTodo Todo
highlight default link corboComment rustCommentLine
highlight default link corboDocComment rustCommentLineDoc
highlight default link corboEscape rustEscape
highlight default link corboString rustString
highlight default link corboAsmOperand Special

let b:current_syntax = 'corbo'
