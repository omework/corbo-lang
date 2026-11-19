"""Stored exclusive capabilities: fixed layout, returns, reuse and exhaustion."""
import validate_reference_field_c as runner
D='enum W{Bound{data:&mut Int}}'
MAKE='fn make(q:&mut Pool<W>,n:&mut Int)-><-W{let w=new(q)W.Bound{data:n};return<-w;}'
runner.PROGRAMS={
'mixed':'enum Mix{A{a:Int,x:&mut Int,b:Int,y:&Int,c:Int}}fn main(){let mut p=pool<Int>(2);let mut q=pool<Mix>(1);let mut n=new(p)Int(10);let y=new(p)Int(20);address(n);let w=new(q)Mix.A{a:1,x:&mut n,b:2,y:&y,c:3};print(w);match &w{Mix.A{a:_,x:r,b:_,y:s,c:_}=>{address(r);print(r);print(s);}}n=30;print(n);}',
'returned':D+MAKE+'fn main(){let mut p=pool<Int>(1);let mut q=pool<W>(1);let mut n=new(p)Int(10);address(n);let w=make(&mut q,&mut n);let a=&w;let b=&w;print(a);print(b);q.reset();n=30;let z=make(&mut q,&mut n);print(z);drop(->z);drop(->n);let next=new(p)Int(7);address(next);print(next);}',
'exhaustion':D+'fn main(){let mut p=pool<Int>(2);let mut q=pool<W>(1);let mut a=new(p)Int(10);let mut b=new(p)Int(20);let x=new(q)W.Bound{data:&mut a};let y=new(q)W.Bound{data:&mut b};print(x);print(y);}'
}
def validate(r,case):
    assert 'runtime error:' not in r.stderr,r.stderr
    if case=='exhaustion':
        assert r.returncode!=0 and 'pool capacity exceeded' in r.stderr,r.stderr
        assert not r.stdout and 'destroy ' not in r.stderr,r.stderr
        return
    assert r.returncode==0,r.stderr
    lines=r.stdout.splitlines()
    destroyed=[x.split('=',1)[1] for x in r.stderr.splitlines() if x.startswith('destroy ')]
    if case=='mixed':
        assert lines[0]==lines[2],lines
        assert [lines[1],*lines[3:]]==['Mix.A(1, 10, 2, 20, 3)','10','20','30'],lines
        assert destroyed==['Mix.A','20','30'],destroyed
    else:
        assert lines[0]==lines[4],lines
        assert [*lines[1:4],lines[5]]==['W.Bound(10)','W.Bound(10)','W.Bound(30)','7'],lines
        assert destroyed==['W.Bound','W.Bound','30','7'],destroyed
runner.validate=validate
if __name__=='__main__':runner.main()
