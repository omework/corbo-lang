"""Direct &Int results across optimized C, pool reuse and mutable parents."""
import validate_borrowed_return_c as runner

PREFIX='''
fn borrow(d:&Int)->&Int{return d;}
fn relay(d:&Int)->&Int{let mut r=borrow(d);return r;}
fn choose(n:Int,a:&Int,b:&Int)->&Int{if n==0{return a;}return b;}
'''
runner.PROGRAMS={
 'readonly':PREFIX+'''fn main(){
    let mut p=pool<Int>(2);let mut a=new(p)Int(42);let mut b=new(p)Int(7);
    address(a);let mut first=relay(&a);address(first);print(first);
    let mut r=choose(1,&a,&b);address(b);address(r);print(r);
    drop(->a);drop(->b);p.reset();let mut fresh=new(p)Int(9);print(fresh);
 }''',
 'mutable_parent':PREFIX+'''fn main(){
    let mut p=pool<Int>(1);let mut data=new(p)Int(42);let mut m=&mut data;
    let mut r=relay(m);print(r);m.set(7);print(m);
 }''',
 'exhaustion':PREFIX+'''fn main(){
    let mut p=pool<Int>(1);let mut data=new(p)Int(42);let mut r=relay(&data);print(r);
    let mut fresh=new(p)Int(9);print(fresh);
 }''',
}

def validate(result,case):
    assert 'runtime error:' not in result.stderr,result.stderr
    if case=='exhaustion':
        assert result.returncode!=0 and 'pool capacity exceeded' in result.stderr,result.stderr
        assert result.stdout=='42\n' and 'destroy ' not in result.stderr,(result.stdout,result.stderr)
        return
    assert result.returncode==0,result.stderr
    lines=result.stdout.splitlines()
    if case=='readonly':
        assert len(lines)==7 and lines[0]==lines[1] and lines[3]==lines[4],lines
        assert [lines[2],lines[5],lines[6]]==['42','7','9'],lines
        expected=['destroy a=42','destroy b=7','destroy fresh=9']
    else:
        assert lines==['42','7'],lines
        expected=['destroy data=7']
    assert [s for s in result.stderr.splitlines() if s.startswith('destroy ')]==expected,result.stderr

runner.validate=validate
if __name__=='__main__':runner.main()
