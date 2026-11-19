"""Content writes, binding capabilities and reuse in optimized C."""
import validate_borrowed_return_c as runner
runner.PROGRAMS={
 'identity':'''fn borrow(d:&Int)->&Int{return d;}
 fn main(){let mut p=pool<Int>(1);let mut d=new(p)Int(10);address(d);
 d=20;d.set(30);address(d);let r=borrow(&d);print(r);drop(->d);p.reset();
 let fresh=new(p)Int(7);address(fresh);print(fresh);}''',
 'rhs':'''fn read(d:&Int)->Int{return *d;}
 fn edit(mut d:->Int)-><-Int{let r=&d;d=read(r);d.set(30);return<-d;}
 fn main(){let mut p=pool<Int>(1);let d=new(p)Int(10);address(d);
 let result=edit(->d);address(result);print(result);
 let mut n=0;if true{n=1;}while n==1{n=2;continue;}print(n);}''',
 'exhaustion':'''fn main(){let mut p=pool<Int>(1);let mut d=new(p)Int(10);
 d=20;print(d);d=new(p)Int(30);print(d);}''',
}
def validate(result,case):
    assert 'runtime error:' not in result.stderr,result.stderr
    if case=='exhaustion':
        assert result.returncode!=0 and 'pool capacity exceeded' in result.stderr,result.stderr
        assert result.stdout=='20\n' and 'destroy ' not in result.stderr,(result.stdout,result.stderr)
        return
    assert result.returncode==0,result.stderr
    rows=result.stdout.splitlines()
    if case=='identity':
        assert len(rows)==5 and rows[0]==rows[1]==rows[3] and [rows[2],rows[4]]==['30','7'],rows
        expected=['destroy d=30','destroy fresh=7']
    else:
        assert len(rows)==4 and rows[0]==rows[1] and rows[2:]==['30','2'],rows
        expected=['destroy d=30']
    assert [r for r in result.stderr.splitlines() if r.startswith('destroy ')]==expected,result.stderr
runner.validate=validate
if __name__=='__main__':runner.main()
