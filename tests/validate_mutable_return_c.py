"""Exclusive returns across optimized C: identity, choice, children, exhaustion."""
import validate_borrowed_return_c as runner
PREFIX='''
fn borrow_mut(d:&mut Int)->&mut Int{return d;}
fn relay(d:&mut Int)->&mut Int{let mut vue=borrow_mut(d);return vue;}
fn borrow(d:&Int)->&Int{return d;}
fn choose(n:Int,a:&mut Int,b:&mut Int)->&mut Int{if n==0{return a;}return b;}
'''
runner.PROGRAMS={
 'identity':PREFIX+'''fn main(){
 let mut p=pool<Int>(1);let mut nombre=new(p)Int(10);address(nombre);
 let mut vue=relay(&mut nombre);address(vue);vue.set(30);print(vue);
 nombre=40;print(nombre);drop(->nombre);p.reset();
 let fresh=new(p)Int(7);address(fresh);print(fresh);}''',
 'conditional':PREFIX+'''fn main(){
 let mut p=pool<Int>(1);let mut q=pool<Int>(1);
 let mut a=new(p)Int(10);let mut b=new(q)Int(7);address(b);
 let mut vue=choose(1,&mut a,&mut b);address(vue);vue.set(30);
 let child=borrow(vue);print(child);vue.set(40);print(vue);print(a);print(b);
 p.reset();q.reset();}''',
 'exhaustion':PREFIX+'''fn main(){let mut p=pool<Int>(1);
 let mut nombre=new(p)Int(10);let mut vue=borrow_mut(&mut nombre);vue.set(20);print(vue);
 let other=new(p)Int(7);print(other);}''',
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
        assert len(rows)==6 and rows[0]==rows[1]==rows[4],rows
        assert [rows[2],rows[3],rows[5]]==['30','40','7'],rows
        expected=['destroy nombre=40','destroy fresh=7']
    else:
        assert len(rows)==6 and rows[0]==rows[1] and rows[2:]==['30','40','10','40'],rows
        expected=['destroy a=10','destroy b=40']
    assert [r for r in result.stderr.splitlines() if r.startswith('destroy ')]==expected,result.stderr
runner.validate=validate
if __name__=='__main__':runner.main()
